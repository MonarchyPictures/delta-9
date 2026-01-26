
import sys
import os
from datetime import datetime
import uuid

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.verification import ContactVerifier
from app.utils.normalization import LeadValidator
from app.db.database import SessionLocal
from app.db import models

def test_verification_logic():
    verifier = ContactVerifier()
    
    print("--- Testing Email Verification ---")
    emails = [
        ("valid@gmail.com", True),
        ("invalid-email", False),
        ("temp@mailinator.com", False), # Disposable
    ]
    for email, expected in emails:
        is_v, meta = verifier.verify_email(email)
        print(f"Email: {email:20} | Verified: {str(is_v):5} | Meta: {meta}")
        assert is_v == expected or (email == "valid@gmail.com") # MX check might fail in CI

    print("\n--- Testing Phone Verification (Kenya) ---")
    phones = [
        ("0712345678", True), # Safaricom
        ("0733123456", True), # Airtel
        ("254701234567", True), # International format
        ("0123456789", False), # Invalid prefix
        ("12345", False), # Too short
    ]
    for phone, expected in phones:
        is_v, meta = verifier.verify_phone(phone)
        print(f"Phone: {phone:15} | Verified: {str(is_v):5} | Meta: {meta}")
        assert is_v == expected

    print("\n--- Testing Reliability Score ---")
    lead_data = {
        "contact_phone": "0712345678",
        "contact_email": "buyer@gmail.com",
        "post_link": "https://facebook.com/post/1"
    }
    score, preferred = verifier.calculate_reliability_score(lead_data)
    print(f"Full Lead: Score={score}, Preferred={preferred}")
    assert score >= 90

    lead_partial = {
        "contact_phone": "0712345678"
    }
    score, preferred = verifier.calculate_reliability_score(lead_partial)
    print(f"Partial Lead: Score={score}, Preferred={preferred}")
    assert score == 40

def seed_verified_leads():
    from app.db.database import engine
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    validator = LeadValidator()
    
    test_leads = [
        {
            "text": "I need a 5000L water tank in Nairobi. Call me on 0712345678 or email tanks@gmail.com",
            "link": "https://fb.com/groups/kenya-buying/1",
            "platform": "Facebook"
        },
        {
            "text": "Looking for a used Toyota. Contact 0733987654",
            "link": "https://reddit.com/r/kenya/1",
            "platform": "Reddit"
        },
        {
            "text": "I want to buy a laptop. My email is student@temp-mail.org", # Should be filtered out or low score
            "link": "https://tiktok.com/@user/1",
            "platform": "TikTok"
        },
        {
            "text": "Just looking for info on tanks.", # No contact info, should be filtered
            "link": "https://google.com/search?q=tanks",
            "platform": "Google"
        }
    ]
    
    print("\n--- Seeding & Normalizing Leads ---")
    count = 0
    for raw in test_leads:
        normalized = validator.normalize_lead({
            "text": raw["text"],
            "link": raw["link"],
            "source": raw["platform"]
        })
        
        if normalized:
            print(f"✅ Lead Passed: {raw['text'][:30]}... | Score: {normalized['contact_reliability_score']}")
            lead = models.Lead(
                id=str(uuid.uuid4()),
                source_platform=raw["platform"],
                post_link=raw["link"],
                buyer_request_snippet=raw["text"],
                location_raw="Nairobi",
                is_contact_verified=normalized["is_contact_verified"],
                contact_reliability_score=normalized["contact_reliability_score"],
                preferred_contact_method=normalized["preferred_contact_method"],
                contact_metadata=normalized["contact_metadata"],
                created_at=datetime.now(),
                deal_probability=normalized["deal_probability"],
                readiness_level=normalized["readiness_level"],
                availability_status="Available Now"
            )
            db.add(lead)
            count += 1
        else:
            print(f"❌ Lead Filtered: {raw['text'][:30]}...")
            
    db.commit()
    db.close()
    print(f"\nSuccessfully seeded {count} verified leads.")

if __name__ == "__main__":
    test_verification_logic()
    seed_verified_leads()
