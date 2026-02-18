

from unittest.mock import MagicMock
from app.services.pipeline import LeadPipeline
from app.models.lead import Lead
from app.db.database import SessionLocal, engine
from app.db.base_class import Base
import uuid

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def test_pipeline_lead_creation():
    db = SessionLocal()
    pipeline = LeadPipeline(db)
    
    raw_lead = {
        "text": "Looking for a Toyota Corolla 2015 model. Urgent.",
        "url": f"https://example.com/post/{uuid.uuid4()}",
        "source": "Facebook",
        "product_category": "Cars",
        "location": "Nairobi",
        "phone": "+254712345678"
    }
    
    # Mock scorer to avoid external calls or complex logic
    pipeline.scorer.validate_lead_debug = MagicMock(return_value={"valid": True, "classification": "BUYER", "score": 0.9, "reasons": []})
    pipeline.scorer.calculate_intent_score = MagicMock(return_value=0.95)
    pipeline.scorer.analyze_readiness = MagicMock(return_value=("high", 0.9))
    
    # Process
    lead = pipeline.process_raw_lead(raw_lead)
    
    assert lead is not None
    assert isinstance(lead, Lead)
    
    # Check core fields mapped from aliases
    assert lead.title == "Cars" # Mapped from product_category
    assert lead.source == "Facebook" # Mapped from source_platform
    assert lead.url == raw_lead["url"] # Mapped from source_url
    assert lead.location == "Nairobi"
    assert lead.buyer_request_snippet.startswith("Looking for")
    assert lead.intent_score == 0.95
    
    # Check compatibility properties
    assert lead.product_category == "Cars"
    assert lead.source_platform == "Facebook"
    assert lead.source_url == raw_lead["url"]
    
    # Check other fields
    assert lead.whatsapp_link is not None
    assert "Toyota" in lead.whatsapp_link or "Cars" in lead.whatsapp_link
    
    # Save to DB to verify constraints
    db.add(lead)
    db.commit()
    db.refresh(lead)
    
    assert lead.id is not None
    
    # Verify to_dict
    data = lead.to_dict()
    assert data['title'] == "Cars"
    assert data['source'] == "Facebook"
    assert data['query'] == "Cars" # Frontend compatibility
    
    db.close()
    print("Pipeline test passed!")

if __name__ == "__main__":
    test_pipeline_lead_creation()
