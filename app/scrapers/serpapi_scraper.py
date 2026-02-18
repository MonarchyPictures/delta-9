
import logging
import httpx
from typing import List, Dict, Any
from app.core.config import settings
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BUYER_PATTERNS = [
    "looking for",
    "want to buy",
    "wtb",
    "need",
    "seeking"
]

class SerpAPIScraper(BaseScraper):
    
    def __init__(self):
        super().__init__()
        self.source = "serpapi_google"

    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """
        Legacy method required by BaseScraper ABC.
        Returns empty list as this scraper uses the async search interface.
        """
        return []

    async def search(self, query: str, location: str = "Kenya"):
        if not settings.SERPAPI_KEY:
            logger.warning("SERPAPI_KEY is not set. Skipping SerpAPI search.")
            return []

        transformed_query = self.transform_query(query)
        
        params = {
            "engine": settings.SERPAPI_ENGINE,
            "q": transformed_query,
            "api_key": settings.SERPAPI_KEY,
            "gl": settings.SERPAPI_REGION,
            "hl": settings.SERPAPI_LANGUAGE,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            logger.error(f"SerpAPI request failed: {e}")
            return []

        results = []
        organic_results = data.get("organic_results", [])

        for item in organic_results:
            title = item.get("title", "").lower()

            if not self.is_buyer(title):
                continue
            
            results.append({
                "title": title,
                "url": item.get("link"),
                "source": "serpapi_google"
            })

        return results

    def transform_query(self, query):
        if any(k in query.lower() for k in BUYER_PATTERNS):
            return query
        return f"looking for {query} {settings.SERPAPI_REGION.upper()}"

    def is_buyer(self, title):
        return any(pattern in title for pattern in BUYER_PATTERNS)
