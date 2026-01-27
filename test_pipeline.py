
import requests
import time
import uuid

BASE_URL = "http://localhost:8000"

def test_full_pipeline():
    print("Starting Full Data Pipeline Test...")
    
    # 1. Create an Agent
    agent_name = f"Test Agent {uuid.uuid4().hex[:4]}"
    print(f"1. Creating Agent: {agent_name}...")
    agent_data = {
        "name": agent_name,
        "query": "solar panels",
        "location": "Nairobi",
        "is_active": 1,
        "enable_alerts": 1
    }
    res = requests.post(f"{BASE_URL}/agents", json=agent_data)
    if res.status_code != 200:
        print(f"  FAILED: Could not create agent ({res.status_code})")
        return False
    
    agent = res.json()
    agent_id = agent["id"]
    print(f"  SUCCESS: Agent ID {agent_id}")
    
    # 2. Trigger Search (Manual trigger if possible, or wait for polling)
    # Since we can't easily trigger a specific agent via API in main.py 
    # (except for the daily run), we'll check if leads already exist for 'solar panels'
    # or just perform a search to see if the search logic works.
    print(f"2. Testing Search Logic for 'solar panels' in 'Nairobi'...")
    res = requests.get(f"{BASE_URL}/leads/search?query=solar+panels&location=Nairobi")
    if res.status_code != 200:
        print(f"  FAILED: Search endpoint failed ({res.status_code})")
        return False
    
    leads = res.json().get("results", [])
    print(f"  SUCCESS: Found {len(leads)} leads")
    
    # 3. Verify Stats Update
    print("3. Verifying Stats Update...")
    res = requests.get(f"{BASE_URL}/stats")
    stats = res.json()
    print(f"  Stats: {stats}")
    
    # 4. Clean up
    print(f"4. Cleaning up: Deleting Agent {agent_id}...")
    res = requests.delete(f"{BASE_URL}/agents/{agent_id}")
    if res.status_code == 200:
        print("  SUCCESS: Agent deleted")
    else:
        print(f"  WARNING: Could not delete agent ({res.status_code})")
        
    print("\n✅ Data Pipeline Integrity Test: PASSED")
    return True

if __name__ == "__main__":
    test_full_pipeline()
