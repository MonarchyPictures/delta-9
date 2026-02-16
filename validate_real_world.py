import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.scrapers.classifieds import ClassifiedsScraper
import json

def test_real_search():
    scraper = ClassifiedsScraper()
    # Try a very specific real-world query for Nairobi
    query = 'toyota nairobi'
    print(f"Testing real-world Jiji search for: {query}")
    
    results = scraper.scrape(query, time_window_hours=72)
    
    if results:
        print(f"Found {len(results)} results.")
        # Print the first result in detail
        first = results[0]
        print(json.dumps(first, indent=2))
        
        # Validation steps
        print("\n--- Validation ---")
        print(f"1. Phone number extracted: {first.get('phone')}")
        print(f"2. Source URL: {first.get('url')}")
        print(f"3. Snippet contains phone? {'Yes' if first.get('phone') and first.get('phone') in first.get('text', '') else 'No'}")
        
    else:
        print("No results found. Check API key/Quota.")

if __name__ == "__main__":
    test_real_search()
