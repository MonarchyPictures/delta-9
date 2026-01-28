import requests
import time
import json

API_URL = "http://localhost:8000"

def test_search(query="water tank 5000l"):
    print(f"\n--- Testing search for: {query} ---")
    
    # 1. Trigger search
    try:
        resp = requests.post(f"{API_URL}/search", params={"query": query, "location": "Kenya"})
        print(f"Trigger Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        
        task_id = resp.json().get("task_id")
        if not task_id:
            print("❌ No task ID returned!")
            return
            
        # 2. Poll for leads
        for i in range(1, 16): # Poll for 15 times
            time.sleep(5)
            try:
                # Use live=true to get latest signals
                resp = requests.get(f"{API_URL}/leads/search", params={
                    "query": query, 
                    "live": "true",
                    "verified_only": "false" # Relaxed for live test
                })
                leads = resp.json().get("results", [])
                print(f"Polling {i}/15... Found {len(leads)} leads")
                if leads:
                     for lead in leads[:2]:
                         print(f"  - [{lead.get('source_platform')}] {lead.get('buyer_request_snippet')[:50]}... (Score: {lead.get('intent_score')})")
                         print(f"    URL: {lead.get('post_link')}")
                         print(f"    Location: {lead.get('location_raw')} | Readiness: {lead.get('readiness_level')}")
            except Exception as e:
                print(f"Error polling: {e}")
                
    except Exception as e:
        print(f"Error triggering search: {e}")

if __name__ == "__main__":
    # Test with a common Kenyan search query
    test_search("water tank 5000l")
    # Also test with a more specific intent query
    test_search("looking for solar panels Nairobi")
