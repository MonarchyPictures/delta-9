import requests
import json

url = "http://localhost:8000/search"
payload = {
    "query": "laptop",
    "location": "remote",
    "debug": True
}
headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Results Count: {data.get('count')}")
        print(f"Total Signals Captured: {data.get('total_signals_captured')}")
        print(f"Rejected Count: {len(data.get('rejected', []))}")
        if data.get('rejected'):
            print("Sample Rejected Lead:", data['rejected'][0])
        else:
            print("No rejected leads found.")
            
        print("Metrics:", json.dumps(data.get('metrics', {}), indent=2))
    else:
        print("Error Response:", response.text)
except Exception as e:
    print(f"Request failed: {e}")
