import logging
from typing import Dict, Any, Optional, List
from .registry import SCRAPER_REGISTRY, refresh_scraper_states, update_scraper_state

logger = logging.getLogger("ScraperSelector")

def decide_scrapers(
    query: str,
    location: str = "Global",
    category: Optional[str] = None,
    time_window_hours: int = 2,
    is_prod: bool = False,
    last_result_count: int = 0
) -> List[str]:
    """
    Generic Scraper Selector.
    Enables all core scrapers and handles adaptation if zero results found.
    """
    refresh_scraper_states()
    
    active_scrapers = []
    
    # AI Reasoning Logic
    reasoning = []
    
    # 🧠 Adaptation loop for zero results
    if is_prod and last_result_count == 0:
        reasoning.append(f"ADAPTATION: 0 results for '{query}'. Enabling emergency discovery scrapers.")
        
        # Enable all available scrapers for 30m if zero results
        for scraper_name in SCRAPER_REGISTRY.keys():
            if scraper_name == "WhatsAppPublicGroupScraper":
                continue
            update_scraper_state(scraper_name, True, ttl_minutes=30, caller="Adaptation Engine")

    for source, config in SCRAPER_REGISTRY.items():
        # 🛡️ SELF-OPTIMIZATION: Filter out auto-disabled weak scrapers
        from .metrics import SCRAPER_METRICS
        if SCRAPER_METRICS.get(source, {}).get("auto_disabled", False):
            continue

        # Rule 0: Sandbox scrapers are always included if enabled (for testing)
        if config.get("mode") == "sandbox" and config.get("enabled"):
            active_scrapers.append(source)
            continue

        # Rule 1: Core scrapers are always on
        if config.get("core"):
            active_scrapers.append(source)
            continue
            
        # Rule 2: Respect manual/TTL enabled state
        if config.get("enabled"):
            active_scrapers.append(source)
            continue

    if reasoning:
        logger.info(" | ".join(reasoning))
        
    return active_scrapers
