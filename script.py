import os

import requests
import json
import snowflake.connector

# Load Snowflake credentials from environment variables (GitHub Secrets)
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")

# API URL
API_URL = "http://overpass-api.de/api/interpreter?data=[out:json][timeout:25];area['name'='Daerah Khusus ibukota Jakarta']->.a;(node['amenity'='pharmacy'](area.a);way['amenity'='pharmacy'](area.a);relation['amenity'='pharmacy'](area.a););out center tags;"

def fetch_pharmacy_data():
    """Fetch data from the Overpass API."""
    response = requests.get(API_URL)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ API Request Failed: {response.status_code}")
        return None

def transform_data(api_data):
    """Transform API JSON to match Snowflake table structure."""
    records = []
    
    for element in api_data.get("elements", []):
        id_value = element.get("id")
        lat = element.get("lat")
        lon = element.get("lon")
        name = element.get("tags", {}).get("name", "Unknown Pharmacy")

        if id_value and lat and lon:
            geo = f"POINT({lon} {lat})"  # WKT format for GEOGRAPHY
            buffer = f"ST_BUFFER(TO_GEOGRAPHY('{geo}'), 50)"  # 50-meter buffer
            buffer_wkt = f"ST_ASWKT({buffer})"

            records.append((id_value, lat, lon, name, geo, buffer, buffer_wkt))

    return records

def insert_into_snowflake(records):
    """Insert data into Snowflake TB_APT table."""
    conn = None
    cursor = None  # ✅ Ensure cursor is always initialized

    try:
        
        # Connect to Snowflake
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            table=SNOWFLAKE_TABLE,
            schema=SNOWFLAKE_SCHEMA
        )
        cursor = conn.cursor()
        
        # ✅ Step 1: Insert Raw JSON into TB_APT_RAW (Fixed)
        raw_json_str = json.dumps(records).replace("'", "''")  # Escape single quotes
        sql_insert_raw = f"""
            INSERT INTO '{SNOWFLAKE_DATABASE}'.'{SNOWFLAKE_SCHEMA}'.'{SNOWFLAKE_TABLE}' (RAW_JSON) 
            SELECT TO_VARIANT('{raw_json_str}')
        """
        cursor.execute(sql_insert_raw)
        print("✅ Raw data inserted into TB_APT_RAW!")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        # Close Connection
        cursor.close()
        conn.close()


if __name__ == "__main__":
    data = fetch_pharmacy_data()
    
    if data:
        transformed_records = transform_data(data)
        if transformed_records:
            insert_into_snowflake(transformed_records)
        else:
            print("⚠️ No valid records to insert.")

