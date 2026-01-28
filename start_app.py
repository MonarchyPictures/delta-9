import subprocess
import os
import time
import threading
import sys

def run_backend():
    # Start FastAPI backend
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    # Ensure dependencies are available for the subprocess
    subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"], cwd="/app/github_code_repository_1222/delta-9")

def run_frontend():
    # Start Vite frontend
    frontend_dir = "/app/github_code_repository_1222/delta-9/frontend"
    os.environ["VITE_API_URL"] = "https://delta7.onrender.com"
    subprocess.run(["npm", "install"], cwd=frontend_dir)
    subprocess.run(["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"], cwd=frontend_dir)

def shutdown():
    time.sleep(300) # Auto-shutdown after 5 mins
    os._exit(0)

# Pre-execution setup: Run seeders (fixed ones)
try:
    print("Running seeders...")
    subprocess.run([sys.executable, "/app/github_code_repository_1222/delta-9/seed_db.py"], check=True)
    subprocess.run([sys.executable, "/app/github_code_repository_1222/delta-9/seed_live_leads.py"], check=True)
    print("Seeding complete.")
except subprocess.CalledProcessError as e:
    print(f"Seeding failed: {e}")

threading.Thread(target=shutdown, daemon=True).start()
threading.Thread(target=run_backend, daemon=True).start()
run_frontend()