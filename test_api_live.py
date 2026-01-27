
import requests
import json

def test_api():
    url = "http://localhost:8000/leads/search?live=true&limit=15&verified_only=false"
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Count: {data.get('count')}")
        results = data.get('results', [])
        print(f"Results returned: {len(results)}")
        for i, lead in enumerate(results[:3]):
            print(f"Lead {i+1}: {lead.get('source_platform')} - {lead.get('buyer_request_snippet')[:50]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
