import logging
import re
from typing import Dict, Any, Tuple

from .intent import BUYER_PATTERNS, is_buyer_intent, buyer_intent_score

logger = logging.getLogger(__name__)

# Legacy support
BUYER_KEYWORDS = BUYER_PATTERNS
STRICT_BUYER_KEYWORDS = BUYER_PATTERNS
HIGH_INTENT = BUYER_PATTERNS # Simplified for now
MEDIUM_INTENT = BUYER_PATTERNS
LOW_INTENT = BUYER_PATTERNS
FINANCIAL_KEYWORDS = BUYER_PATTERNS
URGENCY_KEYWORDS = BUYER_PATTERNS
LOCAL_CONTEXT = BUYER_PATTERNS

# ❌ SELLER KEYWORDS (Hard Reject - DROP IT)
# Generalized to remove vehicle-specific "full duty paid", "accepting trade-ins" etc.
SELLER_KEYWORDS = [
    "for sale", "selling", "units available", "brand new", "dealers", "showroom", 
    "just arrived", "bank finance", "in stock", "we sell", "shop", "promo",
    "wholesale", "retail", "special offer", "discount", "order now"
]

# ❌ NEGATIVE / NON-BUYER INTENT (Immediate Disqualification)
NEGATIVE_INTENT = [
    "free", "not buying", "just looking", "too expensive", "no money", "fake", "scam", "not interested",
    "ya bure", "sitanunua", "naangalia tu", "ni ghali", "sina pesa", "ni feki", "si serious", "siko interested",
    "tuangalie tu", "ni bei mingi", "pesa zimeisha", "mchezo", "si mimi"
]

# Legacy support for existing logic
SELLER_PATTERNS = SELLER_KEYWORDS

# 🎯 STRICT BUYER GATEKEEPERS (Legacy support - now using BUYER_KEYWORDS)
STRICT_BUYER_KEYWORDS = BUYER_KEYWORDS

def classify_post(text: str) -> str:
    """
    Strictly classifies a post as 'buyer' or 'seller' based on intent rules.
    RULE: If a post matches ANY seller keyword -> DROP IT (return 'seller'), 
    even if it has buyer words.
    """
    if not text:
        return "unclear"
    
    t = text.lower()

    # 1. HARD REJECT: Seller Keywords (Priority #1)
    # Exception: "anyone selling", "wholesale price", "supplier needed" are common buyer phrases
    if any(phrase in t for phrase in SELLER_KEYWORDS) and not any(bp in t for bp in ["anyone selling", "wholesale price", "supplier needed", "rfq", "quotation", "any supplier", "supplier of"]):
        return "seller"

    # 2. Check for Negative Intent
    if any(phrase in t for phrase in NEGATIVE_INTENT):
        return "seller"

    # 3. CORE LOGIC: Use is_buyer_intent
    if not is_buyer_intent(text):
        return "seller"
    
    return "buyer"

def get_intent_score(text: str) -> float:
    """
    Calculates an intent score from 0.0 to 1.0 based on intensity of phrases.
    Uses the new generic Buyer Intent Engine.
    """
    return buyer_intent_score(text)
