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

    active_scraper_names = get_active_scrapers()
    logger.info(f"ℹ️ [RUNNER] Active scrapers: {active_scraper_names}")
    results = []
    
    # Run scrapers concurrently
    tasks = []
    for name in active_scraper_names:
        scraper_cls = SCRAPER_CLASSES.get(name)
        if not scraper_cls:
            logger.warning(f"⚠️ [RUNNER] Scraper class not found for: {name}")
            continue
            
        tasks.append(run_single_scraper(scraper_cls, name, full_query))

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

async def run_single_scraper(scraper_cls, name: str, query: str) -> List[Dict[str, Any]]:
    """
    Runs a single scraper in a thread to avoid blocking the event loop.
    """
    try:
        # Wrap blocking scrape call in thread
        return await asyncio.to_thread(_execute_scrape_sync, scraper_cls, name, query)
    except Exception as e:
        logger.error(f"❌ [RUNNER] {name} failed: {e}")
        return []

def _execute_scrape_sync(scraper_cls, name: str, query: str) -> List[Dict[str, Any]]:
    """
    Synchronous execution wrapper for the scraper.
    """
    logger.info(f"▶️ [RUNNER] Running {name}...")
    scraper = scraper_cls()
    signals = scraper.scrape(query, time_window_hours=24)
    
    normalized_results = []
    for signal in signals:
        normalized_results.append({
            "title": signal.get("author") or "Unknown Source",
            "snippet": signal.get("text") or signal.get("snippet", ""),
            "source": signal.get("source", name),
            "url": signal.get("url"),
            "phone": signal.get("phone"),
            "location": signal.get("location"),
            "timestamp": signal.get("timestamp"),
            "confidence": 0.0
        })
    
    logger.info(f"✅ [RUNNER] {name} returned {len(normalized_results)} results")
    return normalized_results
