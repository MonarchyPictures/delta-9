
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def check_endpoint(name, path, method="GET", data=None):
    url = f"{BASE_URL}{path}"
    print(f"Checking {name} ({method} {url})...")
    try:
        start_time = time.time()
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        duration = time.time() - start_time
        print(f"  Status: {response.status_code}")
        print(f"  Time: {duration:.2f}s")
        
        if response.status_code == 200:
            try:
                res_json = response.json()
                print(f"  Valid JSON: Yes")
                return True, res_json
            except:
                print(f"  Valid JSON: No")
                return False, response.text
        else:
            print(f"  Error: {response.text}")
            return False, response.text
    except Exception as e:
        print(f"  Exception: {e}")
        return False, str(e)

def validate_system():
    results = {}
    
    # 1. Health
    success, health_data = check_endpoint("Health", "/health")
    results["health"] = (success, health_data)
    if success:
        print(f"  System Health: {health_data}")
    
    # 2. Stats
    results["stats"] = check_endpoint("Stats", "/stats")
    
    # 3. Agents
    results["agents"] = check_endpoint("Agents", "/agents")
    
    # 4. Leads Search
    results["leads_search"] = check_endpoint("Leads Search", "/leads/search?limit=1")
    
    # 5. Settings
    results["settings"] = check_endpoint("Settings", "/settings")
    
    # 6. Notifications
    results["notifications"] = check_endpoint("Notifications", "/notifications")

    print("\n" + "="*50)
    print("VERIFICATION CHECKLIST")
    print("="*50)
    for name, (success, _) in results.items():
        status = "PASS" if success else "FAIL"
        print(f"{name.replace('_', ' ').title():<20}: {status}")
    print("="*50)

if __name__ == "__main__":
    validate_system()
