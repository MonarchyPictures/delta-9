import re
import logging
from typing import Tuple, List, Dict, Any

from ..intelligence.intent import BUYER_PATTERNS, is_buyer_intent, buyer_intent_score

logger = logging.getLogger(__name__)

class IntentScorer:
    def __init__(self):
        # Explicit buyer signals
        self.buyer_keywords = BUYER_PATTERNS

        # Hard seller block list
        self.seller_blacklist = [
            "for sale", "selling", "available", "price", "discount", "offer", 
            "promo", "delivery", "in stock", "we sell", "shop", "dealer", 
            "supplier", "warehouse", "order now", "dm for price", 
            "call / whatsapp", "our store", "brand new", "limited stock",
            "flash sale", "retail price", "wholesale", "best price",
            "check out", "visit us", "located at", "we deliver", "buy from us",
            "contact for price", "special offer", "new arrival", "stockist",
            "dm to order", "shipping available", "price is", "kwa bei ya",
            "tunauza", "mzigo mpya", "punguzo", "call me for", "contact me for",
            "we are selling", "buy now", "click here", "follow us", "best deals",
            "order today", "price:", "contact:", "dm for", "sold by", "authorized dealer",
            "warranty included", "limited time offer", "check price", "get yours",
            "brand new", "imported", "affordable", "wholesale price", "retail",
            "visit our shop", "we are located", "delivery available", "countrywide",
            "pay on delivery", "lipa baada ya", "mzigo umefika", "bei nafuu",
            "tuko na", "pata yako", "agiza sasa", "welcome to", "call us", "contact us",
            "our shop", "our store", "check our", "see more", "click the link",
            "available in", "brand new", "we offer", "we provide", "expert in",
            "specializing in", "quality service", "best in kenya", "top rated"
        ]

        # Urgency indicators
        self.urgency_keywords = ["asap", "urgent", "immediately", "now", "today", "fast", "needed by", "quick"]

    def calculate_intent_score(self, text: str) -> float:
        """Calculate intent score from 0.0 to 1.0 using the Generic Buyer Intent Engine."""
        return buyer_intent_score(text)

    def analyze_readiness(self, text: str) -> Tuple[str, float]:
        """
        Classify Buyer Readiness:
        - HOT: Immediate purchase intent + specs + urgency
        - WARM: Interest + products
        - RESEARCHING: General mentions
        """
        text_lower = text.lower()
        score = self.calculate_intent_score(text)
        
        has_urgency = any(u in text_lower for u in self.urgency_keywords)
        has_specs = bool(re.search(r'(\d+)\s*(l|kg|units|pcs|ton|20\d{2}|ksh|sh|k\b|m|cm|mm|ft|inches)', text_lower))
        
        if score > 0.7 and (has_urgency or has_specs):
            return "HOT", min(score * 10, 10.0)
        elif score > 0.4:
            return "WARM", min(score * 8, 10.0)
        else:
            return "RESEARCHING", min(score * 5, 10.0)

    def validate_lead(self, text: str) -> bool:
        """Strict validation of whether the text represents a buyer."""
        if not is_buyer_intent(text):
            return False
            
        text_lower = text.lower()
        is_seller = any(s in text_lower for s in self.seller_blacklist)
        
        # If it has seller language, it's usually not a lead unless it has strong buyer signals
        # We trust is_buyer_intent more now, but we still want to avoid pure ads.
        if is_seller:
            # Check if it's REALLY a buyer (e.g., "looking for anyone selling" vs "selling cars")
            # If it has "looking for" and "selling", it's likely a buyer.
            # If it just has "selling", it's a seller.
            strong_buyer_signals = ["looking for", "need", "want to buy", "where can i buy"]
            if not any(s in text_lower for s in strong_buyer_signals):
                return False
            
        # Must have at least a baseline intent score
        score = self.calculate_intent_score(text)
        return score >= 0.4
