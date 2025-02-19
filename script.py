import requests
import json

def hit_api():
    url = "http://overpass-api.de/api/interpreter?data=[out:json][timeout:25];area['name'='Daerah Khusus ibukota Jakarta']->.a;(node['amenity'='pharmacy'](area.a);way['amenity'='pharmacy'](area.a);relation['amenity'='pharmacy'](area.a););out center tags;"
    
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        
        # Print the raw JSON response to ensure it's visible in logs
        print("=== RAW API RESPONSE ===")
        print(json.dumps(data, indent=4))  # Pretty-print JSON for GitHub logs

        # Extract pharmacy details
        print("=== Extracted Pharmacy List ===")
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name", "Unknown Pharmacy")
            address = tags.get("addr:street", "No Address Available")
            print(f"- {name} ({address})")

    else:
        print("Error:", response.status_code, response.text)

if __name__ == "__main__":
    hit_api()
