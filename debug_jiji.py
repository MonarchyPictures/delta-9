
import asyncio
import logging
from app.scrapers.jiji import ClassifiedsScraper

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    scraper = ClassifiedsScraper()
    query = "looking for iphone 15"
    
    print(f"Running Jiji Scraper with query: '{query}'")
    results = await scraper.search(query, location="Kenya")
    
    print(f"\nFinal Results: {len(results)}")
    for result in results:
        print(f"- {result['title']} (Price: {result['price']})")

if __name__ == "__main__":
    asyncio.run(main())
