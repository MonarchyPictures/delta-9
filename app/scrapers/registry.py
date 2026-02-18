
SCRAPER_REGISTRY = {} 
ACTIVE_SCRAPERS = set() 

def register_scraper(name, scraper): 
    SCRAPER_REGISTRY[name] = scraper 
    ACTIVE_SCRAPERS.add(name) 

def enable_scraper(name): 
    ACTIVE_SCRAPERS.add(name) 

def disable_scraper(name): 
    ACTIVE_SCRAPERS.discard(name) 

def get_active_scrapers(): 
    return [SCRAPER_REGISTRY[name] for name in ACTIVE_SCRAPERS] 


# Register only real scrapers: 

from .jiji import ClassifiedsScraper 
from .google_maps import GoogleMapsScraper
from .duckduckgo import DuckDuckGoScraper
# from .reddit import RedditScraper

# Core Scrapers
register_scraper("jiji", ClassifiedsScraper()) 
register_scraper("google_maps", GoogleMapsScraper())
register_scraper("duckduckgo", DuckDuckGoScraper())

# Optional Scrapers (disabled by default in this new registry logic unless registered)
# To match previous state where Reddit was disabled, I won't register it or I will register then disable.
# But the user code says "Register only real scrapers". 
# If I register it, it is active by default (register adds to ACTIVE_SCRAPERS).
# So I should only register the ones I want active.
# Jiji, Google Maps, DuckDuckGo were active. Reddit was not.
# So I will register Jiji, GoogleMaps, DuckDuckGo.

# No mock anywhere.

# --- Backward Compatibility Hooks ---
def update_scraper_state(name, state):
    """
    Legacy hook for updating scraper state.
    In the new registry, we just enable/disable.
    """
    if state == "active":
        enable_scraper(name)
    else:
        disable_scraper(name)

def update_scraper_mode(name, mode):
    """Legacy hook for scraper mode."""
    pass

def refresh_scraper_states():
    """Legacy hook to refresh states from DB."""
    pass
