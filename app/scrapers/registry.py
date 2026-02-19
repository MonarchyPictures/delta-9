
SCRAPER_REGISTRY = {} 
SCRAPER_PRIORITY = {} 
ACTIVE_SCRAPERS = set() 

def register_scraper(name, scraper, priority=10): 
    SCRAPER_REGISTRY[name] = scraper 
    SCRAPER_PRIORITY[name] = priority 
    ACTIVE_SCRAPERS.add(name) 

def enable_scraper(name): 
    ACTIVE_SCRAPERS.add(name) 

def disable_scraper(name): 
    ACTIVE_SCRAPERS.discard(name) 

def get_scraper_name(scraper): 
    for name, obj in SCRAPER_REGISTRY.items(): 
        if obj == scraper: 
            return name
    return None

def get_active_scrapers_sorted(): 
    active = list(ACTIVE_SCRAPERS) 
    return sorted( 
        [SCRAPER_REGISTRY[name] for name in active], 
        key=lambda s: SCRAPER_PRIORITY.get(get_scraper_name(s), 10), 
        reverse=True  # higher number = higher priority 
    ) 

def get_active_scrapers(): 
    # Forward to sorted version for consistency
    return get_active_scrapers_sorted()


# Register only real scrapers: 

from .jiji import ClassifiedsScraper 
from .google_maps import GoogleMapsScraper
from .duckduckgo import DuckDuckGoScraper
from .serpapi_scraper import SerpAPIScraper
from .facebook_marketplace import FacebookMarketplaceScraper

# Core Scrapers
register_scraper("jiji", ClassifiedsScraper(), priority=50) 
register_scraper("google_maps", GoogleMapsScraper(), priority=10)
register_scraper("duckduckgo", DuckDuckGoScraper(), priority=10)
register_scraper("serpapi", SerpAPIScraper(), priority=100)
register_scraper("facebook", FacebookMarketplaceScraper(), priority=20)

# Optional Scrapers (disabled by default in this new registry logic unless registered)
# To match previous state where Reddit was disabled, I won't register it or I will register then disable.
# But the user code says "Register only real scrapers". 
# If I register it, it is active by default (register adds to ACTIVE_SCRAPERS).
# So I should only register the ones I want active.
# Jiji, Google Maps, DuckDuckGo were active. Reddit was not.
# So I will register Jiji, GoogleMaps, DuckDuckGo.

# No mock anywhere.

# --- Backward Compatibility Hooks ---
def update_scraper_state(name, state, ttl_minutes=None, caller=None):
    """
    Legacy hook for updating scraper state.
    In the new registry, we just enable/disable.
    """
    # Handle state being boolean or string ("active")
    is_active = state if isinstance(state, bool) else (state == "active")

    if name not in SCRAPER_REGISTRY:
        return False, f"Scraper '{name}' not found."

    if is_active:
        enable_scraper(name)
        action = "enabled"
    else:
        disable_scraper(name)
        action = "disabled"
        
    return True, f"Scraper '{name}' {action} successfully."

def update_scraper_mode(name, mode, caller=None):
    """Legacy hook for scraper mode."""
    if name not in SCRAPER_REGISTRY:
        return False, f"Scraper '{name}' not found."
    # Since we don't store mode anymore (or default to 'production'), we just acknowledge
    return True, f"Scraper '{name}' mode updated to '{mode}' (virtual)."

def refresh_scraper_states():
    """Legacy hook to refresh states from DB."""
    pass
