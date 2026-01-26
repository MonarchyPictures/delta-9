
import sys
import os
from datetime import datetime, timedelta
import uuid

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal, engine
from app.db import models

def seed_demo_data():
    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # 1. Seed an Agent
    agent = models.Agent(
        name="Water Tank Scout",
        query="water tank",
        location="Kenya",
        is_active=1,
        enable_alerts=1
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    print(f"Seeded agent: {agent.name}")

    # 2. Seed a Notification for this agent
    # Find one of the leads we seeded earlier
    lead = db.query(models.Lead).filter(models.Lead.product_category == "Water Tanks").first()
    
    if lead:
        notif = models.Notification(
            lead_id=lead.id,
            agent_id=agent.id,
            message=f"URGENT: New buyer interested in {lead.product_category} in {lead.location_raw}",
            is_read=0,
            created_at=datetime.now()
        )
        db.add(notif)
        db.commit()
        print(f"Seeded notification for agent: {agent.name}")
    else:
        print("No 'Water Tanks' lead found. Run seed_live_leads.py first.")

    db.close()

if __name__ == "__main__":
    seed_demo_data()
