import sys
import os
import logging

# Ensure app is in path
sys.path.append(os.getcwd())

from app.utils.intent_scoring import IntentScorer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_intent_scorer():
    logger.info("🧪 Starting Intent Scorer Validation...")
    scorer = IntentScorer()
    
    test_cases = [
        {
            "text": "I am looking for a toyota vitz 2015 model urgent",
            "expected_valid": True,
            "desc": "Explicit Buyer (Vehicle)"
        },
        {
            "text": "Anyone selling water tanks 5000 liters? Need asap",
            "expected_valid": True,
            "desc": "Explicit Buyer (General)"
        },
        {
            "text": "We are selling brand new shoes at 50% discount. Visit us today!",
            "expected_valid": False,
            "desc": "Explicit Seller (Ads)"
        },
        {
            "text": "Where can I find cheap cement in Nairobi?",
            "expected_valid": True,
            "desc": "Buyer Question"
        },
        {
            "text": "Natafuta fundi wa stima haraka",
            "expected_valid": True,
            "desc": "Swahili Buyer"
        }
    ]
    
    passed = 0
    for case in test_cases:
        text = case["text"]
        logger.info(f"\n📝 Testing: {case['desc']}")
        logger.info(f"   Input: {text}")
        
        debug_info = scorer.validate_lead_debug(text)
        is_valid = debug_info["valid"]
        score = debug_info["score"]
        classification = debug_info["classification"]
        
        logger.info(f"   Result: Valid={is_valid} | Score={score:.2f} | Class={classification}")
        
        if is_valid == case["expected_valid"]:
            logger.info("   ✅ PASS")
            passed += 1
        else:
            logger.error(f"   ❌ FAIL (Expected {case['expected_valid']})")
            logger.error(f"      Reasons: {debug_info['reasons']}")

    logger.info(f"\n📊 Summary: {passed}/{len(test_cases)} Passed")
    
    if passed == len(test_cases):
        logger.info("✅ Intent Scorer Verification SUCCESS")
    else:
        logger.error("❌ Intent Scorer Verification FAILED")
        sys.exit(1)

if __name__ == "__main__":
    test_intent_scorer()
