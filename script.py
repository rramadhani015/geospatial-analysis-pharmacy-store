import requests

def hit_api():
    url = "https://api.example.com/data"  # Change to your API
    #headers = {"Authorization": "Bearer YOUR_API_KEY"}  # Add if needed
    response = requests.get(url)

    if response.status_code == 200:
        print("API Response:", response.json())
    else:
        print("Error:", response.status_code, response.text)

if __name__ == "__main__":
    hit_api()
