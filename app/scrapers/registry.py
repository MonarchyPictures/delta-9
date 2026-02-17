import logging
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..config.scrapers import SCRAPER_CONFIG, is_scraper_allowed

logger = logging.getLogger("ScraperRegistry")

# 🔒 Enable / Disable Scrapers (Generic)
# FULLY GENERIC: No category-specific prioritization.
ENABLED_SCRAPERS = [
    # "FacebookMarketplaceScraper",
    # "GoogleMapsScraper",
    "ClassifiedsScraper",
    # "TwitterScraper",
    "RedditScraper",
    # "InstagramScraper",
    # "GoogleCSEScraper",
    # "GoogleScraper",
    # "WhatsAppPublicGroupScraper",
    "DuckDuckGoScraper",
    "MockScraper"
]

def get_active_scrapers() -> List[str]:
    """
    🚫 Disabled scrapers never execute
    🚫 No wasted time
    🚫 No noise
    """
    # Cross-reference with GLOBAL SCRAPER_CONFIG
    # Map SCRAPER_CONFIG keys to Scraper class names
    mapping = {
        "facebook": "FacebookMarketplaceScraper",
        "twitter": "TwitterScraper",
        "reddit": "RedditScraper",
        "classifieds": "ClassifiedsScraper",
        "google_cse": "GoogleCSEScraper"
    }
    
    final_enabled = []
    for s_name in ENABLED_SCRAPERS:
        # Find if this scraper has a global toggle
        config_key = next((k for k, v in mapping.items() if v == s_name), None)
        if config_key:
            if is_scraper_allowed(config_key):
                final_enabled.append(s_name)
        else:
            # Scrapers not in mapping pass through if in ENABLED_SCRAPERS
            final_enabled.append(s_name)
            
    return final_enabled

# Safety & Quota Tracking
QUOTAS = {
    "GoogleCSEScraper": {"limit": 1000, "used": 0, "reset_at": 0},
}

# Core registry defining the static properties of each scraper
SCRAPER_REGISTRY = {
    "GoogleMapsScraper": {
        "enabled": False, # Temporarily disabled for debugging
        "core": True,
        "mode": "production",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None # None means permanent
    },
    "ClassifiedsScraper": {
        "enabled": False, # Temporarily disabled for debugging
        "core": True,
        "mode": "production",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    },
    "FacebookMarketplaceScraper": {
        "enabled": True,
        "core": True,
        "mode": "production",
        "cost": "free",
        "noise": "medium",
        "categories": ["all"],
        "enabled_until": None
    },
    "TwitterScraper": {
        "enabled": True, # Managed by SCRAPER_CONFIG
        "core": False,
        "mode": "production",
        "cost": "free",
        "noise": "high",
        "categories": ["all"],
        "enabled_until": None,
    },
    "RedditScraper": {
        "enabled": False, # Temporarily disabled for debugging
        "core": False,
        "mode": "production",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    },
    "MockScraper": {
        "enabled": True,
        "core": True,
        "mode": "debug",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    },
    "GoogleCSEScraper": {
        "enabled": False, # Temporarily disabled
        "core": False,
        "mode": "production",
        "cost": "quota",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    },
    "GoogleScraper": {
        "enabled": False, # Temporarily disabled
        "core": False,
        "mode": "production",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    },
    "WhatsAppPublicGroupScraper": {
        "enabled": False, # Temporarily disabled
        "core": False,
        "mode": "production",
        "cost": "free",
        "noise": "medium",
        "categories": ["all"],
        "enabled_until": None
    },
    "DuckDuckGoScraper": {
        "enabled": True,
        "core": True,
        "mode": "production",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    },
    "InstagramScraper": {
        "enabled": False, # Temporarily disabled
        "core": False,
        "mode": "production",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    }
}

def update_scraper_state(scraper_name: str, state: str, details: Optional[Dict[str, Any]] = None):
    """
    Updates the runtime state of a scraper (e.g. rate_limited, error, active).
    This can be used to dynamically disable scrapers that are failing.
    """
    if scraper_name not in SCRAPER_REGISTRY:
        return
        
    # Simple logging for now, could be expanded to persist state
    logger.info(f"Scraper {scraper_name} state updated to {state}: {details}")
    
    # Example: If rate limited, disable for a while
    if state == "rate_limited":
        # logic to temporarily disable
        pass

def refresh_scraper_states():
    """
    Checks if any disabled scrapers should be re-enabled.
    """
    # Logic to reset scrapers if enabled_until has passed
    now = datetime.now()
    for name, config in SCRAPER_REGISTRY.items():
        if config.get("enabled_until") and now > config["enabled_until"]:
            config["enabled"] = True
            config["enabled_until"] = None
            logger.info(f"Scraper {name} re-enabled automatically.")

def update_scraper_mode(scraper_name: str, mode: str):
    """
    Switch a scraper between 'production' and 'debug' modes.
    """
    if scraper_name in SCRAPER_REGISTRY:
        SCRAPER_REGISTRY[scraper_name]["mode"] = mode
        logger.info(f"Scraper {scraper_name} mode switched to {mode}")
