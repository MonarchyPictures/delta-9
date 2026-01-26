
import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(method, path, data=None):
    url = f"{BASE_URL}{path}"
    print(f"Testing {method} {url}...")
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PATCH":
            response = requests.patch(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)[:200]}...")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    print("-" * 20)

if __name__ == "__main__":
    # Test Root
    test_endpoint("GET", "/")
    
    # Test Stats
    test_endpoint("GET", "/stats")
    
    # Test Leads Search
    test_endpoint("GET", "/leads/search?limit=1")
    
    # Test Agents
    test_endpoint("GET", "/agents")
    
    # Test Notifications
    test_endpoint("GET", "/notifications")
    
    # Test Intelligence
    test_endpoint("GET", "/intelligence/demand/trends")
    test_endpoint("GET", "/intelligence/demand/emerging")
    
    # Test Outreach
    # We need a lead ID for this. Let's try to get one first.
    res = requests.get(f"{BASE_URL}/leads/search?limit=1")
    if res.status_code == 200 and res.json():
        lead_id = res.json()[0]['id']
        test_endpoint("POST", f"/outreach/contact/{lead_id}")
        test_endpoint("POST", "/outreach/track", {"lead_id": lead_id, "response_text": "I am interested in buying this!"})
