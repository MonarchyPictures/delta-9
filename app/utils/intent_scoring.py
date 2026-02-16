import re
import logging
from typing import Tuple, List, Dict, Any

# Use the robust NLP service (Singleton pattern via module variable)
from ..nlp.intent_service import BuyingIntentNLP

logger = logging.getLogger(__name__)

# Global singleton to avoid reloading spaCy model on every request
_nlp_engine = None

def get_nlp_engine():
    global _nlp_engine
    if _nlp_engine is None:
        _nlp_engine = BuyingIntentNLP()
    return _nlp_engine

class IntentScorer:
    def __init__(self):
        self.engine = get_nlp_engine()
        
    def calculate_intent_score(self, text: str) -> float:
        """Calculate intent score from 0.0 to 1.0 using the NLP Engine."""
        if not text:
            return 0.0
        return self.engine.calculate_intent_score(text)

    def analyze_readiness(self, text: str) -> Tuple[str, float]:
        """
        Classify Buyer Readiness using NLP Engine.
        Returns: (readiness_level, score_out_of_10)
        """
        if not text:
            return "RESEARCHING", 0.0
        return self.engine.analyze_readiness(text)

    def validate_lead(self, text: str) -> bool:
        """
        Strict validation of whether the text represents a buyer.
        Delegates to NLP Engine's classification.
        """
        if not text:
            return False
            
        classification = self.engine.classify_intent(text)
        
        if classification == "BUYER":
            return True
            
        if classification == "SELLER":
            logger.debug(f"validate_lead: Rejected as SELLER: {text[:50]}...")
            return False
            
        # If UNCLEAR, we might still accept if score is high enough (fallback)
        # But for strict production, we prefer explicit BUYER signal.
        # Let's check the score as a tie-breaker for UNCLEAR.
        score = self.calculate_intent_score(text)
        if score >= 0.6: # High threshold for unclear text
            logger.info(f"validate_lead: Rescued UNCLEAR lead with high score ({score}): {text[:50]}...")
            return True
            
        logger.debug(f"validate_lead: Rejected as {classification} (Score: {score}): {text[:50]}...")
        return False

    def validate_lead_debug(self, text: str) -> Dict[str, Any]:
        """Debug version of validate_lead that returns reasons."""
        if not text:
            return {"valid": False, "reasons": ["Empty text"], "score": 0.0}
            
        classification = self.engine.classify_intent(text)
        score = self.calculate_intent_score(text)
        
        reasons = []
        if classification != "BUYER":
            reasons.append(f"Classified as {classification}")
            
        if classification == "UNCLEAR" and score < 0.6:
            reasons.append(f"Score {score} below rescue threshold 0.6")
            
        if classification == "SELLER":
            reasons.append("Hard rejection for SELLER intent")
            
        return {
            "valid": (classification == "BUYER") or (classification == "UNCLEAR" and score >= 0.6),
            "score": score,
            "reasons": reasons,
            "classification": classification
        }
