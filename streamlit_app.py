import streamlit as st
import pandas as pd
import pydeck as pdk
import h3
from shapely.geometry import Point
import snowflake.connector
import requests
import json

# List of provinces in Indonesia
PROVINCES = [
    "Aceh", "Bali", "Banten", "Bengkulu", "Daerah Khusus ibukota Jakarta", "Gorontalo", "Jambi", "Jawa Barat",
    "Jawa Tengah", "Jawa Timur", "Kalimantan Barat", "Kalimantan Selatan", "Kalimantan Tengah", "Kalimantan Timur", "Kalimantan Utara",
    "Kepulauan Bangka Belitung", "Kepulauan Riau", "Lampung", "Maluku", "Maluku Utara", "Nusa Tenggara Barat", "Nusa Tenggara Timur",
    "Papua", "Papua Barat", "Riau", "Sulawesi Barat", "Sulawesi Selatan", "Sulawesi Tengah", "Sulawesi Tenggara", "Sulawesi Utara",
    "Sumatera Barat", "Sumatera Selatan", "Sumatera Utara", "Yogyakarta"
]

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

# Sidebar settings
st.sidebar.header("🛠️ Map Controls")

# Province Selection
selected_province = st.sidebar.selectbox("🌍 Select Province", PROVINCES, index=4)

# API URL Function
def get_api_url(province):
    return f"http://overpass-api.de/api/interpreter?data=[out:json][timeout:25];area['name'='{province}']->.a;(node['amenity'='pharmacy'](area.a);way['amenity'='pharmacy'](area.a);relation['amenity'='pharmacy'](area.a););out center tags;"

def fetch_pharmacy_data(province):
    """Fetch data from the Overpass API."""
    response = requests.get(get_api_url(province))
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

# Refresh Data Button in Sidebar
if st.sidebar.button("🔍 Find and Refresh"):
    data = fetch_pharmacy_data(selected_province)
    if data:
        insert_into_snowflake(data)

# Query pharmacy data
query = """SELECT name, latitude, longitude, "tags" FROM public.tb_apt WHERE latitude IS NOT NULL AND longitude IS NOT NULL"""
cursor.execute(query)
df = pd.DataFrame(cursor.fetchall(), columns=["NAME", "LATITUDE", "LONGITUDE", "TAGS"])

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

# Render map visualization as before...
