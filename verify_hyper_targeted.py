
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.normalization import LeadValidator
from app.db.database import SessionLocal
from app.db import models

def test_hyper_targeted_normalization():
    validator = LeadValidator()
    db = SessionLocal()
    
    # 1. Test Lead: 50,000L tank in Nairobi
    raw_lead = {
        "text": "I am looking for a 50,000L tank in Nairobi ASAP. Budget is around 400k. Contact me on 0712345678 or email john@example.com. Need it delivered to Westlands.",
        "source": "Facebook",
        "link": "https://facebook.com/posts/123"
    }
    
    normalized = validator.normalize_lead(raw_lead, db)
    
    print("\n--- TEST LEAD: WATER TANK ---")
    if normalized:
        print(f"Products: {normalized.get('_all_products', 'N/A')}")
        print(f"Category: {normalized['product_category']}")
        print(f"Specs: {normalized['product_specs']}")
        print(f"Match Score: {normalized['match_score']}%")
        print(f"Match Status: {normalized['compatibility_status']}")
        print(f"Matched Product: {normalized['match_details'].get('seller_product_name')}")
        print(f"Deal Probability: {normalized['deal_probability']}%")
        print(f"Readiness: {normalized['readiness_level']}")
        print(f"Neighborhood: {normalized['neighborhood']}")
        print(f"Local Advantage: {normalized['delivery_range_score']}%")
        print(f"Quantity: {normalized['quantity_requirement']}")
        print(f"Payment: {normalized['payment_method_preference']}")
    else:
        print("Lead dropped by validator")

    # 2. Test Lead: Toyota Camry 2005
    raw_lead_2 = {
        "text": "Searching for a clean Toyota Camry 2005 model. Must be in good condition. I have 800k cash. Call 0722000000.",
        "source": "Reddit",
        "link": "https://reddit.com/r/kenya/123"
    }
    
    normalized_2 = validator.normalize_lead(raw_lead_2, db)
    
    print("\n--- TEST LEAD: TOYOTA CAMRY ---")
    if normalized_2:
        print(f"Products: {normalized_2.get('_all_products', 'N/A')}")
        print(f"Category: {normalized_2['product_category']}")
        print(f"Specs: {normalized_2['product_specs']}")
        print(f"Match Score: {normalized_2['match_score']}%")
        print(f"Match Status: {normalized_2['compatibility_status']}")
        print(f"Matched Product: {normalized_2['match_details'].get('seller_product_name')}")
        print(f"Payment: {normalized_2['payment_method_preference']}")
        print(f"Decision Authority: {normalized_2['decision_authority']}")
    else:
        print("Lead 2 dropped")

    # 3. Test Lead: Budget Ready + Deadline
    raw_lead_3 = {
        "text": "Looking for a construction tank 50000l urgently. I have the budget ready and need it by Friday. Contact 0722000000. Delivered to Kilimani.",
        "source": "Reddit",
        "link": "https://reddit.com/r/kenya/comments/456"
    }
    
    normalized_3 = validator.normalize_lead(raw_lead_3, db)
    
    print("\n--- TEST LEAD: BUDGET READY + DEADLINE ---")
    if normalized_3:
        print(f"Products: {normalized_3.get('_all_products', 'N/A')}")
        print(f"Match Score: {normalized_3['match_score']}%")
        print(f"Deal Probability: {normalized_3['deal_probability']}%")
        print(f"Readiness: {normalized_3['readiness_level']}")
        print(f"Deadline: {normalized_3['upcoming_deadline']}")
        print(f"Neighborhood: {normalized_3['neighborhood']}")
        print(f"Local Advantage: {normalized_3['delivery_range_score']}%")
        print(f"Constraints: {normalized_3['delivery_constraints']}")
    else:
        print("Lead 3 dropped")

    db.close()

if __name__ == "__main__":
    test_hyper_targeted_normalization()
