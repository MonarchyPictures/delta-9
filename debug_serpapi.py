
import asyncio
import logging
from app.scrapers.serpapi_scraper import SerpAPIScraper

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    scraper = SerpAPIScraper()
    query = "looking for iphone 15"
    location = "Kenya"
    
    print(f"Running SerpAPIScraper with query: '{query}'")
    results = await scraper.search(query, location)
    
    print(f"\nFinal Results: {len(results)}")
    for result in results:
        print(f"- {result['title']} (Intent: {result['intent_score']}, Market: {result['market_side']})")

if __name__ == "__main__":
    asyncio.run(main())
