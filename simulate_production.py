import asyncio
import logging
import uuid
import sys
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.db.models import Agent, Lead, ActivityLog, Base
from app.services.agent_scheduler import scheduler_loop, execute_agent, reset_stale_agents

# Create tables for simulation if they don't exist
print("🛠️ ensuring database tables exist...")
Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("ProductionSimulation")

TEST_AGENT_NAME = "Production Audit Agent"
TEST_QUERY = "looking for laptop"
TEST_LOCATION = "Nairobi"

def setup_test_agent(db: Session):
    # Clean up existing
    existing = db.query(Agent).filter(Agent.name == TEST_AGENT_NAME).first()
    if existing:
        print(f"Removing existing test agent: {existing.id}")
        db.delete(existing)
        db.commit()

    # Clean up all leads to ensure a clean test (PASS 2 Requirement: Remove Mock Data)
    # This ensures we only see what we just scraped
    print("🧹 Cleaning up old leads from DB...")
    db.query(Lead).delete()
    db.commit()

    # Create new agent
    agent = Agent(
        id=uuid.uuid4(), # Keep as UUID object for DB
        name=TEST_AGENT_NAME,
        query=TEST_QUERY,
        location=TEST_LOCATION,
        interval_hours=24,
        active=True,
        next_run_at=datetime.now(timezone.utc),
        is_running=False
    )
    db.add(agent)
    db.commit()
    print(f"Created test agent: {agent.id}")
    return str(agent.id)

def verify_results(db: Session, agent_id: str, run_count=1):
    print(f"--- Verifying Results (Run {run_count}) ---")
    
    # 1. Check Agent State
    # Handle UUID conversion if necessary
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        agent_uuid = agent_id

    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        print("❌ Agent not found!")
        return
    
    print(f"Agent Next Run: {agent.next_run_at}")
    # Ensure timezone awareness for comparison
    next_run = agent.next_run_at
    if next_run.tzinfo is None:
        next_run = next_run.replace(tzinfo=timezone.utc)
        
    if next_run > datetime.now(timezone.utc):
        print("✅ Agent next_run_at updated correctly.")
    else:
        print("❌ Agent next_run_at was NOT updated (remains in past).")

    # 2. Check Leads
    recent_leads = db.query(Lead).order_by(Lead.request_timestamp.desc()).all()
    print(f"Found {len(recent_leads)} total leads.")
    
    if len(recent_leads) > 0:
        print("✅ Leads inserted successfully.")
        for lead in recent_leads[:5]:
            print(f" - Lead ID: {lead.id}")
            snippet = lead.buyer_request_snippet or "No snippet"
            print(f"   - Snippet: {snippet[:100]}...")
            print(f"   - Intent Score: {lead.intent_score}")
            print(f"   - Source: {lead.source_platform} | URL: {lead.source_url}")
    else:
        print("⚠️ No leads found. This might be due to scraper failure or empty results.")

    return len(recent_leads)

async def run_simulation():
    print("🚀 Starting Autonomous Runtime Simulation (PASS 3)...")
    
    db = SessionLocal()
    try:
        # Reset stale agents before starting
        print("🧹 Resetting stale agents...")
        await asyncio.to_thread(reset_stale_agents, db)

        agent_id = setup_test_agent(db)
        
        # --- PASS 3, Step 1: Force Run Scheduler ---
        print("\n🔄 [STEP 1] Force-running agent...")
        await execute_agent(str(agent_id))
        
        initial_leads = verify_results(db, agent_id, run_count=1)
        
        # --- PASS 3, Step 2: Simulate Second Run (Idempotency) ---
        print("\n🔄 [STEP 2] Simulating Second Run (Check Duplicates)...")
        
        # Reset agent to be due now
        agent_uuid = uuid.UUID(agent_id)
        agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
        agent.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
        
        await execute_agent(str(agent_id))
        
        final_leads = verify_results(db, agent_id, run_count=2)
        
        if final_leads == initial_leads:
            print("✅ IDEMPOTENCY PASSED: No duplicate leads inserted.")
        else:
            print(f"⚠️ IDEMPOTENCY WARNING: Leads count changed from {initial_leads} to {final_leads}. (Could be new leads or duplicates)")
        
        # --- PASS 3, Step 3: Simulate Expired/Inactive Agent ---
        print("\n🔄 [STEP 3] Simulating Inactive Agent...")
        agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
        agent.active = False
        agent.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
        
        # Try to run - should return early
        await execute_agent(str(agent_id))
        
        # Verify it didn't update next_run_at (since it shouldn't run)
        db.refresh(agent)
        
        next_run = agent.next_run_at
        if next_run.tzinfo is None:
            next_run = next_run.replace(tzinfo=timezone.utc)
        
        if next_run < datetime.now(timezone.utc):
            print("✅ INACTIVE AGENT PASSED: Agent did not run (next_run_at is still in past).")
        else:
            print(f"❌ INACTIVE AGENT FAILED: Agent ran! (next_run_at: {agent.next_run_at})")

    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_simulation())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
