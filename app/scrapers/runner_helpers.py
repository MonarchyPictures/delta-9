import logging
from typing import List, Dict, Any
from app.scrapers.intent_scoring import score_intent

logger = logging.getLogger(__name__)

def _normalize_results(signals: List[Dict[str, Any]], name: str) -> List[Dict[str, Any]]:
    """
    Normalizes scraper signals into the format expected by ingestion.
    """
    normalized_results = []
    for signal in signals:
        snippet = signal.get("text") or signal.get("snippet", "")
        # Use snippet as the 'title' for intent scoring since it contains the ad content
        confidence = score_intent(snippet)
        
        normalized_results.append({
            "title": signal.get("author") or "Unknown Source",
            "snippet": snippet,
            "source": signal.get("source", name),
            "url": signal.get("url"),
            "phone": signal.get("phone"),
            "location": signal.get("location"),
            "timestamp": signal.get("timestamp"),
            "confidence": confidence
        })
    
    logger.info(f"✅ [RUNNER] {name} returned {len(normalized_results)} results")
    return normalized_results
