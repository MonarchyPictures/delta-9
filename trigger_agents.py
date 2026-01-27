
from app.core.celery_worker import run_all_agents
import time

def trigger():
    print("Triggering all agents...")
    result = run_all_agents()
    print(f"Result: {result}")

if __name__ == "__main__":
    trigger()
