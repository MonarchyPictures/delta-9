import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_search_mock():
    print("🧪 Testing Search Pipeline (Expecting Mock Results)...")
    
    # Use a query that might trigger fallback or just general search
    import random
    unique_id = random.randint(1000, 9999)
    payload = {
        "query": f"test buyer need laptops {unique_id}",
        "location": "Nairobi",
        "stream": False,
        "debug": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/search", json=payload)
        duration = time.time() - start_time
        
        print(f"⏱️ Request took {duration:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            # Handle different response structures (debug vs normal)
            if isinstance(data, dict):
                leads = data.get("results", []) or data.get("leads", [])
                debug_info = data.get("metrics", {})
                rejected = data.get("rejected", [])
                
                print("🔍 Response Keys:", data.keys())

            else:
                leads = data
                debug_info = {}
                rejected = []
                
            print(f"✅ Status: 200 OK")
            print(f"📦 Leads Found: {len(leads)}")
            if leads:
                print("First lead:", leads[0])
                print("All sources:", [l.get('source') for l in leads])
            
            print(f"🗑️ Rejected: {len(rejected)}")
            if rejected:
                print("First rejected:", rejected[0])
            
            # Check for Mock Scraper leads
            mock_leads = [
                l for l in leads 
                if l.get("source") == "mock_scraper" 
                or l.get("_scraper_name") == "MockScraper"
                or "Test Buyer" in str(l)
                or "mock_scraper" in str(l)
            ]
            
            if mock_leads:
                print(f"✅ Mock Scraper Active: Found {len(mock_leads)} mock leads.")
                for l in mock_leads[:2]:
                    print(f"   - ID: {l.get('id')}")
                    print(f"   - Source: {l.get('source')}")
                    print(f"   - Buyer: {l.get('buyer_name')}")
                    print(f"   - Snippet: {l.get('buyer_request_snippet')}")
            else:
                print("⚠️ No Mock Scraper leads found in 'leads' list.")
                
                # Check rejected
                mock_rejected = [l for l in rejected if "mock_scraper" in str(l) or "MockScraper" in str(l)]
                if mock_rejected:
                    print(f"⚠️ Mock leads were REJECTED. Count: {len(mock_rejected)}")
                    print(f"   - Reason: {mock_rejected[0].get('rejection_reason')}")
                else:
                    print("❌ Mock Scraper apparently did not run or return results.")
                    
            if debug_info:
                print("🔍 Debug Info Keys:", debug_info.keys())
                
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_search_mock()
