
import logging
import sys
from app.utils.intent_scoring import IntentScorer

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def test_rejection():
    scorer = IntentScorer()
    
    # Text from the log that was rejected
    # "Laptops Laptops ; Lenovo ThinkPad T470s 14” FHD IP..."
    # This looks like a title/snippet from a store page
    rejected_text = "Laptops Laptops ; Lenovo ThinkPad T470s 14” FHD IP... Nairobi Computer Shop MacBooks8 Laptop S..."
    
    print(f"--- Testing Rejected Text ---")
    print(f"Text: {rejected_text}")
    
    # Check Debug
    result = scorer.validate_lead_debug(rejected_text)
    print(f"Validation Result: {result}")
    
    if result['valid']:
        print("✅ Correctly accepted (Soft Flagged)")
        if "Soft Flagged for SELLER intent" in str(result.get('reasons')):
             print("   - Verified: Flagged as SELLER")
    else:
        print("❌ Unexpectedly rejected (Hard Block should be removed!)")

    # Test a valid text for comparison
    valid_text = "Looking for a Lenovo ThinkPad T470s in Nairobi, budget 30k"
    print(f"\n--- Testing Valid Text ---")
    print(f"Text: {valid_text}")
    result_valid = scorer.validate_lead_debug(valid_text)
    print(f"Validation Result: {result_valid}")
    
    if result_valid['valid']:
        print("✅ Correctly accepted (Buyer)")
    else:
        print("❌ Unexpectedly rejected!")

if __name__ == "__main__":
    test_rejection()
