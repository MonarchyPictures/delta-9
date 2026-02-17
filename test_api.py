
import requests
try:
    r = requests.get('http://localhost:8000/leads/search?live=true&limit=15&verified_only=false')
    print(f'Status: {r.status_code}')
    data = r.json()
    print(f'Count: {len(data.get("results", []))}')
    for lead in data.get("results", [])[:3]:
        print(f"- {lead.get('source_platform')}: {lead.get('buyer_request_snippet')[:50]}")
except Exception as e:
    print(f'Error: {e}')
