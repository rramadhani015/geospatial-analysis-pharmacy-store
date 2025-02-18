import requests
import json

def hit_api():
    url = "http://overpass-api.de/api/interpreter?data=[out:json][timeout:25];area['name'='Daerah Khusus Ibukota Jakarta']->.a;(node['amenity'='pharmacy'](area.a);way['amenity'='pharmacy'](area.a);relation['amenity'='pharmacy'](area.a););out center tags;"
    
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        
        # Print the result in a readable format
        print("Pharmacies in Jakarta:")
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name", "Unknown Pharmacy")
            address = tags.get("addr:street", "No Address Available")
            print(f"- {name} ({address})")

        # Optional: Save to a JSON file
        with open("pharmacies.json", "w") as file:
            json.dump(data, file, indent=4)
        
    else:
        print("Error:", response.status_code, response.text)

if __name__ == "__main__":
    hit_api()
