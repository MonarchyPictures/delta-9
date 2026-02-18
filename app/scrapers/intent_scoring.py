
def score_intent(title: str) -> float:
    """
    Simple NLP Layer for Intent Scoring.
    Base score: 0.5
    +0.2 for each strong urgency signal (urgent, immediately, asap) found
    +0.2 for buying intent keywords (buy, looking)
    Max score: 1.0
    """
    if not title:
        return 0.5 # Default base score for empty title? Or 0.0? User code starts with 0.5. 
                   # But if title is None/empty, maybe 0.5 is fine or handled by caller.
                   # Let's assume title is valid str as per type hint.

    # User logic implies case-sensitive or insensitive? 
    # Usually NLP is case-insensitive. User didn't specify .lower().
    # But "urgent" in "Urgent needed" would fail if not lowercased.
    # Given "Simple NLP Layer", I'll assume case-insensitivity for robustness, 
    # but the user's code didn't have it.
    # However, usually users provide simplified logic. 
    # I will stick to the user's logic structure but add .lower() for practical NLP utility 
    # unless strictly forbidden. The user's Jiji scraper used .lower(), so it's a safe bet.
    
    title_lower = title.lower()
    score = 0.5

    strong_signals = ["urgent", "immediately", "asap"]
    for word in strong_signals:
        if word in title_lower:
            score += 0.2

    if any(keyword in title_lower for keyword in ["buy", "looking", "need", "wtb", "seeking"]):
        score += 0.2

    return min(score, 1.0)
