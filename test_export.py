import requests
import json
import time

BASE_URL = "http://localhost:8000"
API_KEY = "d9_prod_secret_key_2024" # Assuming this is the key from previous context

def test_export():
    print("🧪 Testing Lead Export...")
    headers = {"x-api-key": API_KEY}
    
    # 1. Get leads to find an ID
    try:
        print("Fetching leads to get an ID...")
        resp = requests.get(f"{BASE_URL}/leads?limit=5", headers=headers)
        if resp.status_code != 200:
            print(f"❌ Failed to get leads: {resp.status_code}")
            print(resp.text)
            return

        data = resp.json()
        leads = data.get("leads", [])
        if not leads:
            print("⚠️ No leads found. Cannot test export.")
            return
            
        lead_id = leads[0]["id"]
        print(f"Found lead ID: {lead_id}")
        
        # 2. Test Export POST
        print(f"Testing POST /leads/export with ID {lead_id}...")
        payload = {"ids": [lead_id]}
        
        # Use stream=True for file download
        export_resp = requests.post(f"{BASE_URL}/leads/export", json=payload, headers=headers, stream=True)
        
        if export_resp.status_code == 200:
            print("✅ Export Success (200 OK)")
            content_disp = export_resp.headers.get("Content-Disposition", "")
            print(f"Content-Disposition: {content_disp}")
            
            # Read first few bytes
            content_preview = list(export_resp.iter_content(chunk_size=1024))[0].decode('utf-8')
            print("--- File Content Preview ---")
            print(content_preview[:200])
            print("----------------------------")
        else:
            print(f"❌ Export Failed: {export_resp.status_code}")
            print(export_resp.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_export()
