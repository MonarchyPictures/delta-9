from scraper import LeadScraper
import json

def test_queries():
    scraper = LeadScraper()
    queries = [
        'site:reddit.com ("looking for" OR "where can I buy") "tires" ("Kenya" OR "Nairobi")',
        '"tires" Kenya "looking for"',
        '"tires" Kenya "natafuta"'
    ]
    
    for q in queries:
        print(f"\n--- Testing Query: {q} ---")
        results = scraper.duckduckgo_search(q, location="Kenya")
        print(f"Found {len(results)} results")
        for r in results[:3]:
            print(f" - {r['link']}: {r['text'][:100]}...")

if __name__ == "__main__":
    test_queries()
