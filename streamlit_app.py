import streamlit as st
import pandas as pd
import pydeck as pdk
import h3
from shapely.geometry import Point
import snowflake.connector
import requests
import json

# Snowflake Connection
@st.cache_resource
def get_snowflake_connection():
    return snowflake.connector.connect(
        user=st.secrets["SNOWFLAKE_USER"],
        password=st.secrets["SNOWFLAKE_PASSWORD"],
        account=st.secrets["SNOWFLAKE_ACCOUNT"],
        warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
        database=st.secrets["SNOWFLAKE_DATABASE"],
        schema=st.secrets["SNOWFLAKE_SCHEMA"]
    )

conn = get_snowflake_connection()
cursor = conn.cursor()

# API URL
API_URL = "http://overpass-api.de/api/interpreter?data=[out:json][timeout:25];area['name'='Daerah Khusus ibukota Jakarta']->.a;(node['amenity'='pharmacy'](area.a);way['amenity'='pharmacy'](area.a);relation['amenity'='pharmacy'](area.a););out center tags;"

def fetch_pharmacy_data():
    """Fetch data from the Overpass API."""
    response = requests.get(API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"❌ API Request Failed: {response.status_code}")
        return None

def insert_into_snowflake(api_data):
    """Insert raw JSON into Snowflake TB_APT_RAW table."""
    try:
        sql_insert_raw = """
            INSERT INTO TB_APT_RAW (RAW_JSON) 
            SELECT PARSE_JSON(%s)
        """
        cursor.execute(sql_insert_raw, (json.dumps(api_data),))
        conn.commit()
        st.success("✅ Data refreshed successfully!")
    except Exception as e:
        st.error(f"❌ Error: {e}")

# Refresh Data Button
if st.button("🔄 Refresh Data"):
    data = fetch_pharmacy_data()
    if data:
        insert_into_snowflake(data)

# Query pharmacy data
query = """SELECT name, latitude, longitude, "tags" FROM public.tb_apt WHERE latitude IS NOT NULL AND longitude IS NOT NULL"""
cursor.execute(query)
df = pd.DataFrame(cursor.fetchall(), columns=["NAME", "LATITUDE", "LONGITUDE", "TAGS"])

# Title and Introduction
st.title("📍 Geospatial Data Visualization: Pharmacy Coverage & Density Analysis")
st.markdown("""
This interactive map helps analyze **pharmacy locations** with different visualization techniques:  
- **Buffer Zones** (Coverage area)  
- **H3 Hexagonal Aggregation** (Spatial insights)  
- **Heatmap** (Density distribution)  

🔍 **Use the controls on the left to customize the view!**
""")

# Sidebar settings
st.sidebar.header("🛠️ Map Controls")

# Total Record Count
st.sidebar.markdown(f"**📊 Total Records: {len(df)}**")

# Select visualization mode
mode = st.sidebar.radio("Select Visualization Mode:", ["Buffer", "H3 Hexagons", "Heatmap"])

# Select base map style
map_style = st.sidebar.selectbox(
    "🗺️ Choose Basemap",
    [
        "mapbox://styles/mapbox/streets-v11",
        "mapbox://styles/mapbox/satellite-v9",
        "mapbox://styles/mapbox/dark-v10",
        "mapbox://styles/mapbox/light-v9",
    ],
)

# Search for a pharmacy by name
search_query = st.sidebar.text_input("🔍 Search Pharmacy by Name")
if search_query:
    df = df[df["NAME"].str.contains(search_query, case=False, na=False)]

# Buffer Distance Control
buffer_distance = st.sidebar.slider(
    "Buffer Distance (meters)", min_value=100, max_value=1000, step=50, value=500
) / 111_000  # Convert meters to degrees

# H3 Resolution Control
h3_resolution = st.sidebar.selectbox("H3 Resolution", [6, 7, 8, 9], index=1)

# Heatmap Controls
if mode == "Heatmap":
    heatmap_radius = st.sidebar.slider("Heatmap Radius", min_value=10, max_value=100, value=50, step=5)
    heatmap_intensity = st.sidebar.slider("Heatmap Intensity", min_value=1, max_value=10, value=5)
    heatmap_opacity = st.sidebar.slider("Heatmap Opacity", min_value=0.1, max_value=1.0, value=0.5, step=0.1)

# Scatterplot for pharmacy locations
scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    df,
    get_position=["LONGITUDE", "LATITUDE"],
    get_radius=50,
    get_fill_color=[0, 0, 255, 200],
    pickable=True,
)

# Generate GeoJSON Data for Buffer and H3
buffered_features = []
h3_features = []

for _, row in df.iterrows():
    lat, lon, name, tags = row["LATITUDE"], row["LONGITUDE"], row["NAME"], row["TAGS"]

    # Buffer (Circle) Geometry
    if mode == "Buffer":
        point = Point(lon, lat)
        buffered_polygon = point.buffer(buffer_distance)
        buffered_geojson = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [list(map(list, buffered_polygon.exterior.coords))]},
            "properties": {"name": name, "tags": tags},
        }
        buffered_features.append(buffered_geojson)

    # H3 Hexagon Geometry
    elif mode == "H3 Hexagons":
        h3_index = h3.geo_to_h3(lat, lon, h3_resolution)
        hex_boundary = h3.h3_to_geo_boundary(h3_index, geo_json=True)
        h3_geojson = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [hex_boundary]},
            "properties": {"name": name, "tags": tags},
        }
        h3_features.append(h3_geojson)

# Create GeoJSON FeatureCollection
geojson_data = {
    "type": "FeatureCollection",
    "features": buffered_features if mode == "Buffer" else h3_features,
}

# Buffer Layer
buffer_layer = pdk.Layer(
    "GeoJsonLayer",
    geojson_data,
    pickable=True,
    stroked=True,
    filled=True,
    opacity=0.4,
    get_fill_color=[255, 0, 0, 100],
    get_line_color=[255, 0, 0],
)

# Final Map Layers
layers = [scatter_layer]
if mode == "Buffer":
    layers.append(buffer_layer)

# Render Map
st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=pdk.ViewState(latitude=df["LATITUDE"].mean(), longitude=df["LONGITUDE"].mean(), zoom=12),
    map_style=map_style,
    tooltip={"html": "<b>Pharmacy Name:</b> {name}<b><br>Tags:</b> {tags}", "style": {"backgroundColor": "steelblue", "color": "white"}},
))
