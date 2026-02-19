HIGH_INTENT_TERMS = [
    "urgent",
    "asap",
    "today",
    "immediately",
    "ready to buy",
    "cash buyer"
]

def calculate_intent_score(text: str):
    if not text:
        return 0.5
        
    text = text.lower()

    score = 0.5  # base

    for term in HIGH_INTENT_TERMS:
        if term in text:
            score += 0.1

    if "?" in text:
        score += 0.05

    if "price" in text:
        score += 0.05

    return min(score, 1.0)
