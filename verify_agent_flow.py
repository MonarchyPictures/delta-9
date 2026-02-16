import sys
import os
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.database import SessionLocal, engine
from app.db import models

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_flow():
    """
    Verifies the Agent Run Flow:
    1. Create Agent
    2. Simulate Scrape (with high score result)
    3. Check AgentRawLead (Save ALL)
    4. Check Lead (Score/Rank)
    5. Check Notification (Notify)
    6. Check notified flag
    """
    db = SessionLocal()
    try:
        # 1. Create Test Agent
        agent_id = "test-agent-flow-verify"
        # Cleanup previous run
        db.query(models.Notification).filter(models.Notification.agent_id == agent_id).delete()
        db.query(models.AgentRawLead).filter(models.AgentRawLead.agent_id == agent_id).delete()
        db.query(models.AgentLead).filter(models.AgentLead.agent_id == agent_id).delete()
        db.query(models.Agent).filter(models.Agent.id == agent_id).delete()
        # NEW: Cleanup the test lead itself to avoid duplicate detection skipping it
        db.query(models.Lead).filter(models.Lead.contact_phone == "0712345678").delete()
        db.commit()

        agent = models.Agent(
            id=agent_id,
            name="Flow Test Agent",
            query="test product",
            location="Nairobi",
            interval_hours=2,
            duration_days=7,
            active=1,
            start_time=datetime.now(),
            next_run_at=datetime.now()
        )
        db.add(agent)
        db.commit()
        logger.info(f"✅ Step 1: Created Agent {agent_id}")

        # 2. Simulate Scrape Platform Task
        # We will mock the internal components of scrape_platform_task
        # Let's try importing the task and mocking the scraper.
        # Since LeadScraper is imported inside the function from 'scraper', we patch 'scraper.LeadScraper'
        with patch('scraper.LeadScraper') as MockScraper:
            # Setup Mock Scraper to return a high-value lead
            mock_instance = MockScraper.return_value
            mock_instance.scrape_platform.return_value = [{
                "source": "TestPlatform",
                "text": "I urgently need to buy a test product in Nairobi. Call me at 0712345678. Budget 50k.",
                "url": "http://test.com/post/1",
                "phone": "0712345678",
                "timestamp": datetime.now().isoformat()
            }]
            
            # Import the task (it will use the mocked scraper)
            from app.core.celery_worker import scrape_platform_task
            
            # MOCK RANKING to force HIGH SCORE (0.9)
            with patch("app.intelligence.ranking.RankingEngine.calculate_score", return_value=0.9):
                logger.info("⏳ Step 2: Running scrape_platform_task (with mocked High Score)...")
                # Simulate the task call with correct parameters
                result = scrape_platform_task(
                    platform="TestPlatform",
                    query="test product",
                    location="Nairobi",
                    agent_id=agent_id,
                    tier=2,
                    timeout=15
                )
                logger.info(f"Task Result: {result}")

        # 3. Verify AgentRawLead (Save ALL)
        raw_lead = db.query(models.AgentRawLead).filter(models.AgentRawLead.agent_id == agent_id).first()
        if raw_lead:
            logger.info(f"✅ Step 3: AgentRawLead saved. ID: {raw_lead.id}, Text: {raw_lead.raw_text[:30]}...")
        else:
            logger.error("❌ Step 3: AgentRawLead NOT found!")
            return

        # 4. Verify Lead Scoring/Ranking
        # The lead should be created
        lead = db.query(models.Lead).filter(models.Lead.contact_phone == "0712345678").first()
        if lead:
            logger.info(f"✅ Step 4: Lead created. ID: {lead.id}, Intent: {lead.intent_score}, Ranked: {lead.ranked_score}")
            if lead.ranked_score >= 0.75:
                logger.info("   -> Ranked Score is HIGH (>= 0.75) as expected for urgent request.")
            else:
                logger.warning(f"   -> Ranked Score {lead.ranked_score} is lower than expected for 'urgent'. Check ranking weights.")
        else:
            logger.error("❌ Step 4: Lead NOT found!")
            return

        # 5. Check Notification (Notify)
        # Should be ONE summary notification
        notifications = db.query(models.Notification).filter(models.Notification.agent_id == agent_id).all()
        if len(notifications) == 1:
            n = notifications[0]
            logger.info(f"✅ Step 5: Notification created. Message: '{n.message}'")
            if "New High-Intent Leads" in n.message:
                 logger.info("   -> Message format correct (Summary style).")
            else:
                 logger.warning(f"   -> Message format unexpected: {n.message}")
        elif len(notifications) == 0:
            if lead and lead.ranked_score < 0.5:
                 logger.info(f"ℹ️ Step 5: No notification created (Score {lead.ranked_score} too low).")
            else:
                 logger.error(f"❌ Step 5: No notification created despite high score!")
        else:
            logger.warning(f"⚠️ Step 5: Multiple notifications found ({len(notifications)}). Expected 1 summary.")
            for n in notifications:
                logger.info(f"   - {n.message}")

        # 6. Check notified flag
        if raw_lead:
            # Refresh from DB
            db.refresh(raw_lead)
            logger.info(f"ℹ️ Step 6: AgentRawLead.notified is {raw_lead.notified} (Correct if > 0).")
            
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_flow()
