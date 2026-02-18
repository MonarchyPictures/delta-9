import asyncio
import logging
import time
from typing import List, Dict, Any
from app.scrapers.registry import get_active_scrapers
from app.scrapers import (
    GoogleScraper, FacebookMarketplaceScraper, DuckDuckGoScraper,
    SerpApiScraper, GoogleCSEScraper, ClassifiedsScraper,
    TwitterScraper, InstagramScraper, GoogleMapsScraper,
    WhatsAppPublicGroupScraper, RedditScraper
)

logger = logging.getLogger(__name__)

SCRAPER_CLASSES = {
    "GoogleScraper": GoogleScraper,
    "FacebookMarketplaceScraper": FacebookMarketplaceScraper,
    "DuckDuckGoScraper": DuckDuckGoScraper,
    "SerpApiScraper": SerpApiScraper,
    "GoogleCSEScraper": GoogleCSEScraper,
    "ClassifiedsScraper": ClassifiedsScraper,
    "TwitterScraper": TwitterScraper,
    "InstagramScraper": InstagramScraper,
    "GoogleMapsScraper": GoogleMapsScraper,
    "WhatsAppPublicGroupScraper": WhatsAppPublicGroupScraper,
    "RedditScraper": RedditScraper,
}

async def run_scrapers(query: str, location: str = "Kenya") -> List[Dict[str, Any]]:
    """
    Launches active scrapers for the given query and location.
    Returns a list of raw result dictionaries.
    """
    # Auto-scope to Kenya if not present (User Requirement usually)
    if "Kenya" not in location and "Kenya" not in query:
         search_location = f"{location} Kenya"
    else:
         search_location = location

    full_query = f"{query} {search_location}"
    logger.info(f"🚀 [RUNNER] Starting scrapers for: {full_query}")

    active_scrapers = get_active_scrapers()
    # Log active scrapers
    # Use source or class name for logging
    active_names = [getattr(s, "source", s.__class__.__name__) for s in active_scrapers]
    logger.info(f"ℹ️ [RUNNER] Active scrapers: {active_names}")
    results = []
    
    # Run scrapers concurrently
    tasks = []
    for scraper in active_scrapers:
        # Pass scraper instance directly
        name = getattr(scraper, "source", scraper.__class__.__name__)
        tasks.append(run_single_scraper(scraper, name, full_query))

    if not tasks:
        logger.warning("No active scrapers found.")
        return []

    # Execute all scraper tasks
    scraper_results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in scraper_results:
        if isinstance(res, list):
            results.extend(res)
        elif isinstance(res, Exception):
             logger.error(f"Scraper task failed: {res}")

    logger.info(f"🏁 [RUNNER] All scrapers finished. Total raw results: {len(results)}")
    return results

from app.scrapers.runner_helpers import _normalize_results

async def run_single_scraper(scraper, name: str, query: str) -> List[Dict[str, Any]]:
    """
    Runs a single scraper. Supports both async and sync implementations.
    """
    try:
        if asyncio.iscoroutinefunction(scraper.scrape):
            # Run async scraper directly
            logger.info(f"▶️ [RUNNER] Running {name} (Async)...")
            signals = await scraper.scrape(query, time_window_hours=24)
        else:
            # Wrap blocking sync scrape call in thread
            signals = await asyncio.to_thread(_execute_scrape_sync, scraper, name, query)
            
        # Normalize results (shared logic)
        return _normalize_results(signals, name)
    except Exception as e:
        logger.error(f"❌ [RUNNER] {name} failed: {e}")
        return []

def _execute_scrape_sync(scraper, name: str, query: str) -> List[Dict[str, Any]]:
    """
    Synchronous execution wrapper for the scraper.
    """
    logger.info(f"▶️ [RUNNER] Running {name} (Sync)...")
    # Scraper is already instantiated
    return scraper.scrape(query, time_window_hours=24)
