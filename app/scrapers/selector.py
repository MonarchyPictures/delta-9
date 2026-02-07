import logging
from typing import Dict, Any, Optional, List
from .registry import SCRAPER_REGISTRY, refresh_scraper_states, update_scraper_state
from ..config.categories.vehicles_ke import VEHICLES_KE

logger = logging.getLogger("ScraperSelector")

# Category -> Preferred Scrapers Map
CATEGORY_SCRAPER_MAP = { 
    "vehicles": ["TwitterScraper", "RedditScraper", "FacebookMarketplaceScraper", "ClassifiedsScraper"], 
    "real estate": ["GoogleMapsScraper", "ClassifiedsScraper"], 
    "electronics": ["RedditScraper", "FacebookMarketplaceScraper", "ClassifiedsScraper"], 
    "jobs": ["TwitterScraper", "WhatsAppPublicGroupScraper"],
} 

def get_best_candidates_for_category(category: str) -> List[str]:
    """Find scrapers that have performed well for a given category."""
    from .metrics import SCRAPER_METRICS
    
    # 1. Start with the mapped scrapers
    candidates = CATEGORY_SCRAPER_MAP.get(category, [])
    
    # 2. Score scrapers based on overall verified count and success history
    # This allows us to discover scrapers that might not be in the map but are performing well
    scored_scrapers = []
    for name, metrics in SCRAPER_METRICS.items():
        if name in candidates:
            score = 100 # Boost already mapped scrapers
        else:
            score = 0
            
        # Success rate bonus (verified / runs)
        if metrics["runs"] > 0:
            success_rate = metrics["verified"] / metrics["runs"]
            score += success_rate * 50
            
        # Volume bonus
        score += min(metrics["verified"], 50)
        
        scored_scrapers.append((name, score))
    
    # Sort by score descending
    scored_scrapers.sort(key=lambda x: x[1], reverse=True)
    
    # Return top 3 candidates not already active or known good ones
    return [name for name, score in scored_scrapers[:3] if score > 0]

def decide_scrapers(
    query: str,
    location: str = "Kenya",
    category: Optional[str] = None,
    time_window_hours: int = 2,
    is_prod: bool = False,
    last_result_count: int = 0
) -> List[str]:
    """
    Trae AI decision engine for toggling scrapers based on context and reasoning.
    """
    refresh_scraper_states()
    
    active_scrapers = []
    
    # 🔒 LOCKED CATEGORY ENFORCEMENT
    # If not provided, detect from VEHICLES_KE configuration
    if not category:
        q_lower = query.lower()
        if any(obj in q_lower for obj in VEHICLES_KE["objects"]):
            category = "vehicles"
        elif any(word in q_lower for word in ["job", "hiring", "work"]):
            category = "jobs"
        elif any(word in q_lower for word in ["phone", "laptop", "macbook", "iphone", "electronics"]):
            category = "electronics"
        elif any(word in q_lower for word in ["house", "rent", "land", "apartment"]):
            category = "real estate"

    # AI Reasoning Logic
    reasoning = []
    
    # 🧠 TRAE AI: Search failed adaptation loop
    if is_prod and last_result_count == 0:
        reasoning.append(f"TRAE AI: 0 results for '{query}'. Starting adaptation...")
        
        # 1. Try to find the best candidates for this category/query
        if category:
            best_candidates = get_best_candidates_for_category(category)
            if best_candidates:
                reasoning.append(f"Enabling best candidates for {category}: {', '.join(best_candidates)}")
                for scraper_name in best_candidates:
                    update_scraper_state(scraper_name, True, ttl_minutes=30, caller="Trae AI (Category Expansion)")
        
        # 2. Always enable high-discovery candidates as fallback
        reasoning.append("Enabling emergency discovery scrapers (Twitter, Reddit, Instagram) for 30m.")
        for scraper in ["TwitterScraper", "RedditScraper", "InstagramScraper"]:
            update_scraper_state(scraper, True, ttl_minutes=30, caller="Trae AI (Search Adaptation)")

    # Case: Real estate in Nairobi -> High specificity
    if category == "real estate" and "nairobi" in location.lower():
        reasoning.append("Real estate in Nairobi: prioritized high-trust local signals.")

    for source, config in SCRAPER_REGISTRY.items():
        # Rule 0: Sandbox scrapers are always included if enabled (for testing)
        if config.get("mode") == "sandbox" and config.get("enabled"):
            active_scrapers.append(source)
            continue

        # Rule 1: Core scrapers are always on
        if config.get("core"):
            active_scrapers.append(source)
            continue
            
        # Rule 2: Explicitly disabled in registry (respect manual/TTL state)
        if not config.get("enabled"):
            continue

        # Rule 3: Category Signal (Strict Filtering)
        if category and category in CATEGORY_SCRAPER_MAP:
            if source not in CATEGORY_SCRAPER_MAP[category] and not config.get("core"):
                continue
        
        # Rule 4: Time Window Signal
        if source == "TwitterScraper" and time_window_hours > 12:
            continue
            
        # Rule 5: Location Signal (Nairobi specificity example)
        if category == "real estate" and source in ["TwitterScraper", "RedditScraper"]:
            # Too much noise for real estate discovery
            continue

        active_scrapers.append(source)

    if reasoning:
        logger.info(f"TRAE AI REASONING: {'; '.join(reasoning)}")

    return active_scrapers
