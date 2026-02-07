import re
import logging
from typing import Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

class IntentScorer:
    def __init__(self):
        # Explicit buyer signals
        self.buyer_keywords = [
            "looking for", "need", "need urgently", "want to buy", 
            "where can i buy", "anyone selling", "recommend me", 
            "who sells", "where can i get", "seeking", "iso", "wtb",
            "can i get", "i need", "anyone with", "looking to buy",
            "recommendation for", "best place to buy", "recommend a supplier",
            "natafuta", "nahitaji", "nimehitaji", "nataka kununua", 
            "ni wapi naweza pata", "mnisaidie kupata", "iko wapi",
            "nitapata wapi", "nataka", "unauza wapi", "how much is",
            "price for", "get one", "find one", "looking at buying",
            "recommend", "anyone know where", "where to get"
        ]

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
        """Calculate intent score from 0.0 to 1.0."""
        if not text:
            return 0.0
            
        text_lower = text.lower()
        score = 0.0

        # 1. Keyword match (Strong intent signals)
        high_intent = [
            "looking for", "want to buy", "buying", "need to purchase", 
            "searching for", "where can i find", "anyone selling", 
            "recommend", "where can i buy", "need urgently", "dm me", 
            "inbox me", "wtb", "ready to buy", "trying to find", "trying to get",
            "want to get", "looking to find", "in search of", "natafuta", "nahitaji"
        ]
        medium_intent = [
            "price for", "how much is", "cost of", "recommendations for", 
            "best place for", "who has", "where is", "anyone know where",
            "where to get", "any leads", "budget is", "can i get", "i need"
        ]

        for pattern in high_intent:
            if pattern in text_lower:
                score += 0.5
                break 
                
        for pattern in medium_intent:
            if pattern in text_lower:
                score += 0.3
                break

        # 2. Urgency check
        if any(u in text_lower for u in self.urgency_keywords):
            score += 0.3
            
        # 3. Contact info check (High intent signal)
        if re.search(r'(\+?254|0)(7|1)\d{8}', text) or re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            score += 0.3
            
        # 4. Quantity/Budget signals
        if re.search(r'\b\d+\s*(kg|liters|l|units|pieces|pcs|ksh|sh)\b', text_lower):
            score += 0.2

        # 5. Seller penalty (Negative intent)
        if any(s in text_lower for s in self.seller_blacklist):
            score -= 0.4

        final_score = max(0.0, min(score, 1.0))
        return final_score

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
        has_specs = bool(re.search(r'(\d+)\s*(l|kg|units|pcs|ton|20\d{2}|ksh|sh|k\b)', text_lower))
        
        if score > 0.7 and (has_urgency or has_specs):
            return "HOT", min(score * 10, 10.0)
        elif score > 0.4:
            return "WARM", min(score * 8, 10.0)
        else:
            return "RESEARCHING", min(score * 5, 10.0)

    def validate_lead(self, text: str) -> bool:
        """Strict validation of whether the text represents a buyer."""
        text_lower = text.lower()
        
        is_seller = any(s in text_lower for s in self.seller_blacklist)
        is_buyer = any(b in text_lower for b in self.buyer_keywords)
        
        # If it has seller language, it's usually not a lead unless it has strong buyer signals
        if is_seller and not is_buyer:
            return False
            
        # Must have at least a baseline intent score
        score = self.calculate_intent_score(text)
        return score > 0.4
