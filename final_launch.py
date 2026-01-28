import subprocess
import os
import time
import threading
import sys

BASE_DIR = "/app/github_code_repository_1222/delta-9"
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

def run_backend():
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"], cwd=BASE_DIR)

def run_frontend():
    os.environ["VITE_API_URL"] = "https://delta7.onrender.com"
    subprocess.run(["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"], cwd=FRONTEND_DIR)

def shutdown():
    time.sleep(300)
    os._exit(0)

print("Starting Delta9 Autonomous Market Intelligence Preview...")
threading.Thread(target=shutdown, daemon=True).start()
threading.Thread(target=run_backend, daemon=True).start()
time.sleep(5)
print("Preview accessible at http://localhost:3000")
run_frontend()