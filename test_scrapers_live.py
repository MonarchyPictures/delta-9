from scraper import LeadScraper
import logging

logging.basicConfig(level=logging.INFO)

def test():
    scraper = LeadScraper()
    query = "looking for furniture"
    location = "Kenya"
    
    platforms = ["reddit", "google"]
    for platform in platforms:
        print(f"\nTesting {platform}...")
        try:
            results = scraper.scrape_platform(platform, query, location)
            print(f"Found {len(results)} results")
            for r in results[:5]:
                print(f"- Link: {r.get('link')}")
                print(f"  Text: {r.get('text', 'No text')[:100]}...")
        except Exception as e:
            print(f"Error scraping {platform}: {e}")

if __name__ == "__main__":
    test()
