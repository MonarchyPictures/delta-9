import os
import sys

# Ensure the app module is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.sdk import Delta9

def main():
    print("--- Delta9 SDK Demo ---")
    
    # Initialize SDK
    # Make sure DATABASE_URL is set in environment or .env
    sdk = Delta9()
    
    print("1. Checking active scrapers...")
    scrapers = sdk.get_scrapers()
    print(f"Active scrapers: {len(scrapers)}")
    
    # Enable GoogleMapsScraper for demo
    print("2. Enabling GoogleMapsScraper...")
    sdk.enable_scraper("GoogleMapsScraper")
    
    query = "maize suppliers"
    location = "Nairobi"
    
    print(f"3. Searching for '{query}' in '{location}'...")
    leads = sdk.search(query, location, limit=5)
    
    print(f"4. Found {len(leads)} leads:")
    for i, lead in enumerate(leads):
        print(f"   {i+1}. {lead.buyer_name} ({lead.contact_phone}) - {lead.source_platform}")
        
    print("5. Closing SDK...")
    sdk.close()
    print("--- Demo Complete ---")

if __name__ == "__main__":
    main()
