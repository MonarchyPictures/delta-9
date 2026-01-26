
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.normalization import LeadValidator
from app.db.database import SessionLocal
from app.db import models

def test_comprehensive_intelligence():
    validator = LeadValidator()
    db = SessionLocal()
    
    # Test Lead: High Intent with specific signals
    raw_lead = {
        "text": "I am looking for a 50,000L tank in Nairobi ASAP. Budget is approved and I have cash in hand. Need it by tomorrow morning for a construction project. Contact me on 0712345678. Delivered to Westlands.",
        "source": "Facebook",
        "link": "https://facebook.com/posts/intel_test_1"
    }
    
    normalized = validator.normalize_lead(raw_lead, db)
    
    print("\n=== COMPREHENSIVE INTELLIGENCE TEST ===")
    if normalized:
        print(f"Lead: {normalized['buyer_name']} | Product: {normalized['product_category']}")
        
        print("\n--- 1. Lead Profile ---")
        print(f"History: {normalized['buyer_history']}")
        print(f"Activity Level: {normalized['platform_activity_level']}")
        print(f"Past Response Rate: {normalized['past_response_rate']}%")
        
        print("\n--- 2. Market Context ---")
        print(f"Market Price: {normalized['market_price_range']}")
        print(f"Seasonality: {normalized['seasonal_demand']}")
        print(f"Supply Status: {normalized['supply_status']}")
        
        print("\n--- 3. Conversion Signals ---")
        print(f"Signals Detected: {normalized['conversion_signals']}")
        print(f"Deadline: {normalized['upcoming_deadline']}")
        
        print("\n--- 4. Seller Match Analysis ---")
        print(f"Match Score: {normalized['match_score']}%")
        print(f"Competitive Advantages: {normalized['competitive_advantages']}")
        print(f"Pricing Strategy: {normalized['pricing_strategy']}")
        print(f"Talking Points: {normalized['talking_points']}")
        
        # Verify specific signals were caught
        assert "budget_approved" in normalized['conversion_signals']
        assert "imminent_purchase" in normalized['conversion_signals']
        assert len(normalized['talking_points']) > 0
        assert normalized['market_price_range'] != "Negotiable"
        
        print("\n✅ TEST PASSED: Comprehensive intelligence populated correctly.")
    else:
        print("❌ TEST FAILED: Lead dropped by validator")

    db.close()

if __name__ == "__main__":
    test_comprehensive_intelligence()
