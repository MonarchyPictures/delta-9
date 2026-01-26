import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_flow():
    print("--- Testing Search-Driven Kenya-Only Lead System ---")
    
    # 1. Test Search Trigger
    print("\n1. Triggering background search for 'construction tank' in Nairobi...")
    try:
        res = requests.post(f"{BASE_URL}/search", params={"query": "construction tank", "location": "Nairobi"})
        print(f"Response: {res.json()}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Test Agent Creation
    print("\n2. Creating a search agent for 'Toyota Camry' in Mombasa...")
    agent_data = {
        "name": "Camry Sniper",
        "query": "Toyota Camry",
        "location": "Mombasa",
        "is_active": 1
    }
    try:
        res = requests.post(f"{BASE_URL}/agents", json=agent_data)
        agent = res.json()
        print(f"Agent Created: {agent}")
        agent_id = agent["id"]
    except Exception as e:
        print(f"Error: {e}")
        return

    # 3. List Agents
    print("\n3. Listing all agents...")
    try:
        res = requests.get(f"{BASE_URL}/agents")
        print(f"Agents: {res.json()}")
    except Exception as e:
        print(f"Error: {e}")

    # 4. Search Leads (with pagination and time filter)
    print("\n4. Searching for leads in Kenya (last 2 hours)...")
    try:
        res = requests.get(f"{BASE_URL}/leads/search", params={"location": "Kenya", "hours": 2, "page": 1, "limit": 10})
        leads = res.json()
        print(f"Found {len(leads)} leads in last 2 hours.")
        if leads:
            print(f"Sample Lead: {leads[0]['buyer_request_snippet']} at {leads[0]['location_raw']}")
    except Exception as e:
        print(f"Error: {e}")

    # 5. Delete Agent
    print(f"\n5. Terminating agent {agent_id}...")
    try:
        res = requests.delete(f"{BASE_URL}/agents/{agent_id}")
        print(f"Response: {res.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_flow()
