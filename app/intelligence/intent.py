"""
Universal Buyer Intent Engine
Generalizes intent detection across all categories (water pipes, cement, phones, cars, etc.)
Focuses exclusively on BUYERS, not sellers or ads.
"""

BUYER_PATTERNS = [
    # English
    "looking for",
    "need",
    "want to buy",
    "where can i buy",
    "anyone selling",
    "need supplier",
    "need vendor",
    "urgent need",
    "searching for",
    "interested in buying",
    "i want to purchase",
    "how much is",
    "price for",
    "get me",
    "find me",
    "can i get",
    "i need a",
    "i need an",
    "looking to acquire",
    "in the market for",
    "seeking",
    "where to find",
    "who sells",
    "any leads on",
    "supplier of",
    "any supplier",

    # B2B / Industrial signals (New Upgrade)
    "rfq",
    "quotation",
    "quotations",
    "supplier needed",
    "suppliers needed",
    "bulk order",
    "price per meter",
    "price per foot",
    "price per unit",
    "contractor looking",
    "tender",
    "procurement",
    "wholesale price",
    "delivery schedule",
    "business looking for",

    # Sheng (Kenyan slang/creole)
    "nataka",
    "nipe",
    "naeza pata",
    "ko wapi nipate",
    "una sell",
    "una kuuza",
    "ko bidii",
    "ko kitu",
    "naikua",
    "niskie",
    "ko na",
    "meko na",
    "niambie",
    "tupeane",
    "ko fresh",
    "niko na budget",
    "ko supply",
    "una supply",
    "nipe price",
    "ko bei",
    "nataka ku-buy",
    "ko link",
    "nao pia",
    "ko hio",
    "meko na hio",
    "nipatie",
    "ko pesa",
    "tunatafuta",
    "wanatafuta",

    # Swahili
    "ninataka",
    "ninaomba",
    "ninahitaji",
    "napenda kununua",
    "ninaweza kupata wapi",
    "anayeiuza",
    "muuzaji",
    "duka",
    "bei ya",
    "nipe",
    "tafadhali nisaidie",
    "ninatafuta",
    "mahali pa kununua",
    "ninachotafuta",
    "ninahitaji muuzaji",
    "kuna mtu anayeuza",
    "ninaweza kupata",
    "nipatie",
    "ninaweza kununua",
    "nina shida ya",
    "ko na",
    "naweza kuona",
    "natumai kupata",
    "ninatafuta muuzaji wa",
    "ninahitaji kununua",
]

def is_buyer_intent(text: str) -> bool:
    """
    CORE LOGIC: Returns True if text exhibits clear buyer intent.
    Works for any category (water pipes, cement, phones, cars, etc.)
    """
    if not text:
        return False
    text = text.lower()
    return any(p in text for p in BUYER_PATTERNS)

def buyer_intent_score(text: str, query: str = None) -> float:
    """
    Calculates a buyer intent score from 0.0 to 1.0.
    Heuristic: presence of buyer patterns + urgency + specs.
    """
    if not text:
        return 0.0
        
    text = text.lower()
    score = 0.0

    # 🏭 Industry Awareness
    from app.intelligence_v2.industry_aware import is_industrial_query
    is_industrial = is_industrial_query(query) if query else False

    # Base intent from patterns
    matched_patterns = [p for p in BUYER_PATTERNS if p in text]
    if matched_patterns:
        score += 0.4
        # Deduplicate overlapping patterns (e.g., "looking for" and "looking")
        # Sort by length descending and only count non-overlapping
        unique_matches = []
        sorted_patterns = sorted(matched_patterns, key=len, reverse=True)
        temp_text = text
        for p in sorted_patterns:
            if p in temp_text:
                unique_matches.append(p)
                temp_text = temp_text.replace(p, "###")
        
        score += min(len(unique_matches) * 0.1, 0.3) # Bonus for multiple signals

    # Urgency signals
    urgency_keywords = ["asap", "urgent", "immediately", "now", "today", "fast", "needed by", "quick"]
    if any(f" {u} " in f" {text} " for u in urgency_keywords):
        score += 0.2

    # Specificity signals (numbers, units, quantities)
    import re
    # Base pattern for quantities - match numbers followed by units
    # We require a unit to avoid matching random numbers like "iPhone 15"
    qty_pattern = r'(\d+)\s+(l|kg|units|pcs|ton|20\d{2}|ksh|sh|k\b|m|cm|mm|ft|inches|meters|metres|bags|bundles|rolls|drums)'
    if re.search(qty_pattern, text, re.IGNORECASE):
        # Check if it matched a year-like number (e.g., 2024)
        match = re.search(qty_pattern, text, re.IGNORECASE)
        matched_text = match.group(0).lower()
        # If it's just a number like "15" without a unit, don't count it as a quantity unless it's a specific B2B unit
        score += 0.1
        # 🏭 Industry Boost: Extra points for quantity in B2B
        if is_industrial:
            score += 0.1

    # 🏭 RFQ/Quotation Boost for Industrial
    if is_industrial:
        rfq_patterns = ["rfq", "quotation", "quote", "supplier", "bulk", "wholesale"]
        if any(rp in text for rp in rfq_patterns):
            score += 0.1

    return min(score, 1.0)
