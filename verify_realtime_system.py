
import requests
import time
from datetime import datetime

API_URL = "http://localhost:8000"

def test_live_feed():
    print("--- Testing Live Feed Order ---")
    # 1. Search with live=true
    response = requests.get(f"{API_URL}/leads/search", params={
        "live": "true",
        "verified_only": "false",
        "limit": 5
    })
    if response.status_code == 200:
        leads = response.json()
        print(f"Found {len(leads)} leads in live feed.")
        if len(leads) > 1:
            # Check if sorted by created_at desc
            times = [datetime.fromisoformat(l['created_at'].replace('Z', '+00:00')) for l in leads]
            is_sorted = all(times[i] >= times[i+1] for i in range(len(times)-1))
            print(f"Sorted by created_at desc: {is_sorted}")
    else:
        print(f"Failed to fetch live feed: {response.status_code}")

def test_verified_filter():
    print("\n--- Testing Strict Verification Filter ---")
    # 1. Search with verified_only=true
    response_v = requests.get(f"{API_URL}/leads/search", params={
        "verified_only": "true",
        "limit": 10
    })
    leads_v = response_v.json() if response_v.status_code == 200 else []
    print(f"Verified Only: {len(leads_v)} leads")
    
    # Check if all leads are actually verified
    all_verified = all(l.get('is_contact_verified') == 1 and l.get('contact_reliability_score', 0) >= 40 for l in leads_v)
    print(f"All leads meet verification criteria: {all_verified}")

    # 2. Search with verified_only=false
    response_all = requests.get(f"{API_URL}/leads/search", params={
        "verified_only": "false",
        "limit": 10
    })
    leads_all = response_all.json() if response_all.status_code == 200 else []
    print(f"All Leads: {len(leads_all)} leads")

def test_response_windows():
    print("\n--- Testing Competitive Advantage & Response Windows ---")
    response = requests.get(f"{API_URL}/leads/search", params={"limit": 5, "verified_only": "false"})
    if response.status_code == 200:
        leads = response.json()
        for l in leads:
            print(f"Lead ID: {l['id'][:8]} | Platform: {l['source_platform']:10} | Comp: {l['competition_count']} | Window: {l['optimal_response_window']}")

if __name__ == "__main__":
    # Ensure backend is running before testing
    try:
        test_live_feed()
        test_verified_filter()
        test_response_windows()
    except Exception as e:
        print(f"Test failed: {e}")
