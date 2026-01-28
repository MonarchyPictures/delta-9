import requests
try:
    resp = requests.get("http://localhost:8080/search?q=test&format=json")
    print(f"SearXNG Status: {resp.status_code}")
    print(f"Results found: {len(resp.json().get('results', []))}")
except Exception as e:
    print(f"SearXNG Error: {e}")
