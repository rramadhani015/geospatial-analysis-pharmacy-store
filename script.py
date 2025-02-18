import requests

def hit_api():
    url = "http://overpass-api.de/api/interpreter?data=[out:json][timeout:25];area['name'='Daerah Khusus Ibukota Jakarta']->.a;(node['amenity'='pharmacy'](area.a);way['amenity'='pharmacy'](area.a);relation['amenity'='pharmacy'](area.a););out center tags;"
    
    response = requests.get(url)

    if response.status_code == 200:
        print("API Response:", response.json())  # Adjust this if you need specific data
    else:
        print("Error:", response.status_code, response.text)

if __name__ == "__main__":
    hit_api()
