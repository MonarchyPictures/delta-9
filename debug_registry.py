
import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.getcwd())

from app.scrapers.registry import get_active_scrapers_sorted, SCRAPER_REGISTRY, ACTIVE_SCRAPERS

print("Registry contents:", list(SCRAPER_REGISTRY.keys()))
print("Active scrapers set:", ACTIVE_SCRAPERS)

try:
    sorted_scrapers = get_active_scrapers_sorted()
    print("Sorted active scrapers:", [s.__class__.__name__ for s in sorted_scrapers])
except Exception as e:
    print(f"Error getting sorted scrapers: {e}")

# Check SerpAPI config
from app.core.config import settings
print(f"SERPAPI_KEY set: {bool(settings.SERPAPI_KEY)}")
print(f"SERPAPI_ENGINE: {settings.SERPAPI_ENGINE}")
