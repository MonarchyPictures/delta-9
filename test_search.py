
import requests
import time

def test_search():
    url = "http://127.0.0.1:8001/search"
    payload = {"query": "test query", "location": "Nairobi"}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...") # Print first 200 chars
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
