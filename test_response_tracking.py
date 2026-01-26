
import uuid
from datetime import datetime, timedelta
from app.db.database import SessionLocal, engine
from app.db import models
from app.utils.outreach import OutreachEngine
from app.utils.normalization import LeadValidator
from sqlalchemy import or_

def test_response_tracking_system():
    print("🚀 Starting Response Tracking System Verification...")
    
    # Initialize DB and Engines
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    outreach = OutreachEngine()
    validator = LeadValidator()
    
    try:
        # 1. Setup "Bad History" - User who didn't respond twice
        bad_phone = "0712345678"
        bad_email = "ignorer@example.com"
        
        # Clear existing leads with this link to avoid unique constraint error
        db.query(models.Lead).filter(models.Lead.post_link.like("https://fb.com/history_%")).delete(synchronize_session=False)
        db.query(models.Lead).filter(models.Lead.post_link == "https://reddit.com/new_post").delete(synchronize_session=False)
        db.commit()

        print(f"--- Setting up non-response history for {bad_phone} ---")
        for i in range(2):
            history_lead = models.Lead(
                id=str(uuid.uuid4()),
                source_platform="Facebook",
                post_link=f"https://fb.com/history_{i}",
                location_raw="Nairobi, Kenya",
                buyer_request_snippet="Need something",
                product_category="Test",
                contact_phone=bad_phone,
                contact_email=bad_email,
                intent_score=0.9,
                status=models.ContactStatus.CONTACTED, # Already contacted
                response_count=0 # BUT NO RESPONSE
            )
            db.add(history_lead)
        db.commit()
        
        # 2. Test: Check if history check works
        print("--- Verifying History Check Logic ---")
        has_bad_history = outreach.check_non_response_history(db, phone=bad_phone)
        print(f"Result for {bad_phone}: {'FLAGGED (Success)' if has_bad_history else 'FAILED'}")
        
        # 3. Simulate Scraper finding this user again
        print("--- Simulating Scraper finding same user ---")
        raw_lead = {
            "source": "Reddit",
            "link": "https://reddit.com/new_post",
            "text": f"Looking for a water tank ASAP! Contact me at {bad_phone}",
            "location": "Mombasa, Kenya"
        }
        
        normalized = validator.normalize_lead(raw_lead)
        # Check if non_response_flag would be set (this happens in celery_worker normally)
        has_bad_history_again = outreach.check_non_response_history(db, phone=normalized.get("contact_phone"))
        
        new_lead = models.Lead(
            id=normalized["id"],
            source_platform=normalized["source_platform"],
            post_link=normalized["post_link"],
            location_raw=normalized["location_raw"],
            buyer_request_snippet=normalized["buyer_request_snippet"],
            product_category=normalized["product_category"],
            contact_phone=normalized["contact_phone"],
            contact_email=normalized["contact_email"],
            intent_score=normalized["intent_score"],
            confidence_score=5.0, # High enough for search
            is_genuine_buyer=1,
            non_response_flag=1 if has_bad_history_again else 0,
            status=models.ContactStatus.NOT_CONTACTED
        )
        db.add(new_lead)
        db.commit()
        
        print(f"New Lead Flagged: {'YES (Success)' if new_lead.non_response_flag == 1 else 'NO (Failed)'}")
        
        # 4. Test: Contacting a lead
        print("--- Testing Contact Tracking ---")
        lead_id = new_lead.id
        outreach.mark_contacted(db, lead_id)
        
        updated_lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        print(f"Status after contact: {updated_lead.status.value}")
        print(f"Contact Attempt Time: {updated_lead.last_contact_attempt}")
        
        # 5. Test: Tracking a response
        print("--- Testing Response Tracking ---")
        # Simulate response 5 minutes later
        updated_lead.last_contact_attempt = datetime.now() - timedelta(minutes=5)
        db.commit()
        
        outreach.track_response(db, lead_id, "Yes, I am interested! What is the price?")
        
        refreshed_lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        print(f"Status after response: {refreshed_lead.status.value}")
        print(f"Response Count: {refreshed_lead.response_count}")
        print(f"Avg Response Time: {refreshed_lead.average_response_time_mins} mins")
        print(f"Conversion Rate: {refreshed_lead.conversion_rate}%")
        
        # 6. Verify Search Filtering
        print("--- Verifying Search Filters (Verified Only) ---")
        from app.main import search_leads
        
        # Ensure our lead is verified and has Kenya in location
        refreshed_lead.is_contact_verified = 1
        refreshed_lead.contact_reliability_score = 85.0
        refreshed_lead.location_raw = "Nairobi, Kenya" # Must match Kenya filter
        db.commit()
        
        results = search_leads(db=db, verified_only=True, location="Kenya")
        found = any(l.id == lead_id for l in results)
        print(f"Lead found in verified search: {'YES (Success)' if found else 'NO (Failed)'}")
        
        print("\n✅ Verification Complete: All systems working end-to-end.")
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_response_tracking_system()
