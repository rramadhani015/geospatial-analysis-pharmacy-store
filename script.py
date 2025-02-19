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
SNOWFLAKE_TABLE = os.getenv("SNOWFLAKE_TABLE")

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

def insert_into_snowflake(api_data):
    """Insert raw JSON into Snowflake TB_APT_RAW table."""
    conn = None
    cursor = None

    try:
        # Connect to Snowflake
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA
        )
        cursor = conn.cursor()

        # Insert JSON into Snowflake (using VARIANT)
        sql_insert_raw = f"""
            INSERT INTO SP_DB.PUBLIC.TB_APT_RAW (RAW_JSON) 
            SELECT PARSE_JSON(%s)
        """
        cursor.execute(sql_insert_raw, (json.dumps(api_data),))

        print("✅ Raw data inserted into TB_APT_RAW!")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    data = fetch_pharmacy_data()
    
    if data:
        insert_into_snowflake(data)
    else:
        print("⚠️ No data fetched.")
