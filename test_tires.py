import sys
import os
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.specialops import SpecialOpsAgent
from app.db.database import SessionLocal
from app.db import models

def test_tires_search():
    print("--- Testing 'tires' search with multi-source expansion ---")
    agent = SpecialOpsAgent()
    query = "tires"
    location = "Kenya"
    
    # 1. Execute mission
    leads = agent.execute_mission(query, location)
    
    print(f"\nFound {len(leads)} leads for '{query}'")
    
    for i, lead in enumerate(leads):
        print(f"\nLead {i+1}:")
        print(f"  Title: {lead.get('title')}")
        print(f"  Confidence: {lead.get('confidence')}%")
        print(f"  Is Hot: {lead.get('is_hot_lead')}")
        print(f"  Snippet: {lead.get('buyer_request_snippet')[:100]}...")

if __name__ == "__main__":
    test_tires_search()
