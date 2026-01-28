
import os
import sys
import logging
from app.core.specialops import SpecialOpsAgent
from app.db.database import SessionLocal
from app.db import models

# Setup logging to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_search():
    agent = SpecialOpsAgent()
    query = "tires"
    location = "Kenya"
    
    print(f"🚀 Starting mission for '{query}' in {location}")
    results = agent.execute_mission(query, location)
    
    print(f"✅ Mission returned {len(results)} leads")
    for i, lead in enumerate(results[:5]):
        print(f"Lead {i+1}: {lead.get('title')}")
        print(f"Confidence: {lead.get('confidence')}")
        print(f"URL: {lead.get('url')}")
        print("-" * 20)

if __name__ == "__main__":
    test_search()
