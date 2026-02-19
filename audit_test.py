
import requests
import json
import time

BASE_URL = "http://localhost:8000"
SEARCH_ENDPOINT = f"{BASE_URL}/api/search"

QUERIES = [
    {"query": "laptops Nairobi", "desc": "Scraper Verification"},
    {"query": "truck tires Nairobi", "desc": "Final Test 1"},
    {"query": "bulk cooking oil supplier Kenya", "desc": "Final Test 2"},
    {"query": "used macbook pro Nairobi", "desc": "Final Test 3"}
]

REQUIRED_FIELDS = [
    "title", "url", "source", "market_side", "intent_score", 
    "urgency_score", "persona", "phone", "email", "confidence", "badge"
]

def run_test():
    print("STARTING FULL SYSTEM AUDIT\n")
    
    # Check API Status
    try:
        resp = requests.get(f"{BASE_URL}/docs")
        if resp.status_code == 200:
            print("API STATUS: PASS (Docs accessible)")
        else:
            print(f"API STATUS: FAIL (Status {resp.status_code})")
    except Exception as e:
        print(f"API STATUS: FAIL (Connection error: {e})")
        return

    # Run Queries
    for q in QUERIES:
        print(f"\nTESTING: {q['desc']} - Query: '{q['query']}'")
        payload = {"query": q["query"], "location": "Kenya"} # Location is implicit or explicit
        
        try:
            start_time = time.time()
            resp = requests.post(SEARCH_ENDPOINT, json=payload, timeout=60) # 60s timeout
            duration = time.time() - start_time
            
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                count = data.get("count", 0)
                metrics = data.get("metrics", {})
                
                print(f"   Duration: {duration:.2f}s")
                print(f"   Results: {count}")
                print(f"   Scrapers Run: {metrics.get('scrapers_run')}")
                
                if count > 0:
                    print("   SCRAPER STATUS: PASS")
                    
                    # Verify Fields
                    first_result = results[0]
                    missing = [f for f in REQUIRED_FIELDS if f not in first_result]
                    
                    if not missing:
                        print("   LEAD OBJECT INTEGRITY: PASS")
                    else:
                        print(f"   LEAD OBJECT INTEGRITY: FAIL (Missing: {missing})")
                        print(f"   Example keys: {list(first_result.keys())}")

                    # Verify AI Fields
                    print(f"   AI Analysis (Example):")
                    print(f"      - Persona: {first_result.get('persona')}")
                    print(f"      - Urgency: {first_result.get('urgency_score')}")
                    print(f"      - Confidence: {first_result.get('confidence')}")
                    print(f"      - Badge: {first_result.get('badge')}")
                    
                    # Verify Demand Only
                    supply_leads = [r for r in results if r.get("market_side") == "supply"]
                    if not supply_leads:
                         print("   MARKET CLASSIFIER: PASS (No supply leads)")
                    else:
                         print(f"   MARKET CLASSIFIER: WARNING ({len(supply_leads)} supply leads found)")
                else:
                    print("   SCRAPER STATUS: WARNING (0 results - might be valid if no leads)")
                    
            else:
                print(f"   QUERY FAILED: Status {resp.status_code}")
                print(f"   Response: {resp.text[:200]}")
                
        except Exception as e:
            print(f"   QUERY FAILED: {e}")

if __name__ == "__main__":
    run_test()
