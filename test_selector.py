
import logging
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.scrapers.registry import SCRAPER_REGISTRY, refresh_scraper_states
from app.scrapers.selector import decide_scrapers
from app.scrapers.mock_scraper import MockScraper

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestSelector")

def test_selector():
    print("--- Checking SCRAPER_REGISTRY ---")
    for name, config in SCRAPER_REGISTRY.items():
        print(f"Scraper: {name}, Config: {config}")
    
    print("\n--- Checking MockScraper Registration ---")
    if "MockScraper" in SCRAPER_REGISTRY:
        print("MockScraper is in REGISTRY")
    else:
        print("MockScraper is NOT in REGISTRY")

    print("\n--- Testing decide_scrapers ---")
    active_scrapers = decide_scrapers(
        query="test",
        location="Nairobi",
        is_prod=False
    )
    print(f"Active Scrapers: {active_scrapers}")

    if "MockScraper" in active_scrapers:
        print("SUCCESS: MockScraper is selected.")
    else:
        print("FAILURE: MockScraper is NOT selected.")

if __name__ == "__main__":
    test_selector()
