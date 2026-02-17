import requests
import sys

BASE_URL = "http://localhost:8000"

def test_soft_flagging():
    print("Testing Soft Flagging for Invalid API Key...")
    
    # 1. Test with Valid API Key
    headers_valid = {"x-api-key": "d9_prod_secret_key_2024"}
    try:
        # Note: Route is /settings based on app/routes/admin.py having no prefix
        response = requests.get(f"{BASE_URL}/settings", headers=headers_valid)
        if response.status_code == 200:
            print("✅ Valid API Key: Success (200 OK)")
        else:
            print(f"❌ Valid API Key: Failed ({response.status_code})")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        sys.exit(1)

    # 2. Test with Invalid API Key
    headers_invalid = {"x-api-key": "invalid_key_123"}
    try:
        response = requests.get(f"{BASE_URL}/settings", headers=headers_invalid)
        
        # In Soft Flagging mode, we expect 200 OK (but internally flagged)
        # OR 401 if we decided to keep it strict. 
        # Based on my code change, it should be 200 OK because HTTPException is commented out.
        
        if response.status_code == 200:
            print("✅ Invalid API Key: Soft Flagged (200 OK) - SUCCESS")
        elif response.status_code == 401:
            print("❌ Invalid API Key: Hard Blocked (401 Unauthorized) - FAIL (Soft Flagging not active)")
        else:
            print(f"⚠️ Invalid API Key: Unexpected Status ({response.status_code})")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_soft_flagging()
