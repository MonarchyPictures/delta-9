import requests
import time
import json

def verify_pipeline():
    base_url = "http://127.0.0.1:8000"
    query = "tires"
    location = "Kenya"
    
    print(f"🚀 Starting Strict Pipeline Verification for query: '{query}'")
    
    # 1. Trigger Search
    print(f"--- Step 1: Triggering Search ---")
    try:
        res = requests.post(f"{base_url}/search?query={query}&location={location}")
        print(f"Search trigger status: {res.status_code}")
        if res.status_code != 200:
            print(f"Error: {res.text}")
            return
    except Exception as e:
        print(f"Connection error: {e}")
        return

    # 2. Wait for results (since it's background/sync fallback)
    print(f"--- Step 2: Waiting for leads to populate ---")
    time.sleep(20) # Increased wait

    # 3. Check Leads
    print(f"--- Step 3: Inspecting Leads ---")
    try:
        res = requests.get(f"{base_url}/leads?location={location}")
        data = res.json()
        
        # Check if data is a list (leads) or a dict (with leads key)
        leads = data if isinstance(data, list) else data.get('leads', [])
        
        print(f"Found {len(leads)} leads.")
        
        seller_found = False
        buyer_count = 0
        
        # Take up to 10
        limit = min(10, len(leads))
        for i in range(limit):
            lead = leads[i]
            snippet = lead.get('buyer_request_snippet', '').lower()
            intent = lead.get('intent_type', 'UNKNOWN')
            
            # Strict Intent Check
            is_seller_text = any(s in snippet for s in ["for sale", "selling", "available", "price", "mzigo mpya"])
            
            print(f"{i+1}. [{intent}] {lead.get('source_platform')} | {lead.get('post_link')[:30]}...")
            print(f"   Text: {snippet[:100]}...")
            
            if intent == "SELLER" or (is_seller_text and "who" not in snippet and "anyone" not in snippet):
                print(f"   ❌ ERROR: Seller lead found in buyer pipeline!")
                seller_found = True
            elif intent == "BUYER":
                buyer_count += 1
                
        print(f"\nSummary:")
        print(f" - Buyer Leads: {buyer_count}")
        print(f" - Seller Leads: {'❌ FAIL' if seller_found else '✅ PASS (Zero)'}")
        
    except Exception as e:
        print(f"Inspection error: {e}")

if __name__ == "__main__":
    verify_pipeline()
