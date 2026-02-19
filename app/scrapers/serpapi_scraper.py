
import logging
import httpx
import re
from typing import List, Dict, Any
from app.core.config import settings
from app.services.query_rewriter import build_buyer_query
from app.services.market_classifier import classify_market_side
from app.services.intent_engine import calculate_intent_score
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BUSINESS_DOMAINS = [
    # ".co.ke", # Too aggressive for Kenya
    # ".com/",  # Too aggressive
    "/shop",
    "/product",
    "/store",
    "jumia.co.ke",
    "kilimall.co.ke",
    "copia.co.ke",
]

def is_business_domain(url: str):
    return any(d in url.lower() for d in BUSINESS_DOMAINS)

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

        # Use new Rewriter Logic
        transformed_query = build_buyer_query(query, location)
        
        logger.info(f"Rewrote query: '{query}' -> '{transformed_query}'")
        
        params = {
            "engine": settings.SERPAPI_ENGINE,
            "q": transformed_query,
            "api_key": settings.SERPAPI_KEY,
            "gl": settings.SERPAPI_REGION,
            "hl": settings.SERPAPI_LANGUAGE,
            "num": 30, # Fetch more results to increase chance of finding buyers
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

        logger.info(f"SerpAPI returned {len(organic_results)} organic results")

        for item in organic_results:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            url = item.get("link", "")
            text_blob = (title + " " + snippet)

            if is_business_domain(url):
                logger.info(f"Filtered (Business Domain): {url}")
                continue

            market_side = classify_market_side(text_blob)

            if market_side != "demand":
                logger.info(f"Filtered (Supply Side): {title}")
                continue  # kill seller pages

            intent_score = calculate_intent_score(text_blob)

            if intent_score < 0.6:
                logger.info(f"Filtered (Low Intent {intent_score}): {title}")
                continue  # remove weak intent

            # Use extraction but default to None as requested
            price = self._extract_price(text_blob) or None
            phone = self._extract_phone(snippet) # Already returns None if no match

            results.append({
                "buyer_name": None,
                "title": title,
                "price": price,
                "location": "Kenya",
                "phone": phone,
                "source": "serpapi_google",
                "intent_score": intent_score,
                "url": item.get("link"),
                "snippet": snippet,
                "market_side": market_side
            })

        return results

    def _extract_price(self, text: str) -> str:
        match = re.search(r'(?:Ksh|KES)\.?\s*([\d,]+)', text, re.IGNORECASE)
        return match.group(0) if match else ""

    def _extract_phone(self, text: str) -> str:
        # Match +254..., 07..., 01..., 7..., 1...
        # Same as search_service.py extract_phone
        match = re.search(r'(\+?254|0)?([17]\d{8})', text)
        return match.group(0) if match else None

    def transform_query(self, query):
        if any(k in query.lower() for k in BUYER_PATTERNS):
            return query
        return f"looking for {query} {settings.SERPAPI_REGION.upper()}"

    def is_buyer(self, title):
        # Even with "looking for" in query, Google can return e-commerce product pages.
        # We need to filter out obvious seller titles.
        
        lower_title = title.lower()
        
        # Explicit SELLER keywords to reject
        SELLER_KEYWORDS = [
            "for sale", "buy online", "price in kenya", "shop online", 
            "store", "add to cart", "checkout", "selling", "best price",
            "discount", "offer"
        ]
        
        # If it explicitly says "looking for" or "wanted", we accept it even if it has price info
        # e.g. "Looking for iPhone 13 - Best Price" -> Accept
        if any(p in lower_title for p in BUYER_PATTERNS):
            return True
            
        # Otherwise, if it has seller keywords, REJECT it.
        if any(s in lower_title for s in SELLER_KEYWORDS):
            return False
            
        # If neutral (no buyer or seller keywords), we accept it because the query was strong.
        # But maybe we should be skeptical?
        # Let's trust it for now but the intent scorer will lower its score if it looks like a product.
        return True
