import subprocess
import os
import time
import threading
import sys

BASE_DIR = "/app/github_code_repository_1222/delta-9"
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

def run_backend():
    print("Starting FastAPI Backend...")
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"], cwd=BASE_DIR)

def run_frontend()

if __name__ == "__main__":
    # Ensure dependencies are installed before starting
    print("Checking Node.js dependencies...")
    try:
        subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)
        print("Frontend dependencies installed.")
    except Exception as e:
        print(f"npm install failed: {e}")
    main():
    print("Starting Vite Frontend...")
    os.environ["VITE_API_URL"] = "https://delta7.onrender.com"
    # Port 3000 as requested for preview
    subprocess.run(["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"], cwd=FRONTEND_DIR)

def shutdown():
    # 5 minute auto-shutdown for safety
    time.sleep(300)
    print("Auto-shutdown reaching time limit.")
    os._exit(0)

def main():
    print("Step 1: Running Seeders...")
    try:
        subprocess.run([sys.executable, "seed_db.py"], cwd=BASE_DIR, check=True)
        subprocess.run([sys.executable, "seed_live_leads.py"], cwd=BASE_DIR, check=True)
        print("Seeding successful.")
    except Exception as e:
        print(f"Seeding encountered an error: {e}")

    # Launch backend first and wait
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Give backend time to bind to port
    time.sleep(10)
    
    # Start auto-shutdown timer
    threading.Thread(target=shutdown, daemon=True).start()
    
    # Run frontend in main thread
    run_frontend()

if __name__ == "__main__":
    main()