
import urllib.request
import sys

try:
    with urllib.request.urlopen('http://localhost:8001/docs') as response:
        print(f"Backend Status: {response.getcode()}")
except Exception as e:
    print(f"Backend Check Failed: {e}")
    sys.exit(1)
