import requests
import json

url = "http://localhost:8001/search"
payload = {
    "query": "toyota",
    "location": "Nairobi, Kenya"
}
headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
