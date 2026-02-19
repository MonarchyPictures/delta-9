
def calculate_confidence(intent_score: float, urgency_score: float, source_reliability: float = 0.8) -> float:
    """
    Calculate a final confidence score (0.0 - 1.0)
    """
    # Weighted formula
    # Intent is king (50%)
    # Urgency adds value (30%)
    # Source reliability (20%)
    
    score = (intent_score * 0.5) + (urgency_score * 0.3) + (source_reliability * 0.2)
    return min(score, 0.99)
