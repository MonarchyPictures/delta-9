import logging
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger("ScraperRegistry")

# 🔒 STEP 3 — Enable / Disable Scrapers (Vehicles Only)
# This mapping ensures only authorized, high-signal scrapers are used for the vehicles_ke category.
CATEGORY_SCRAPER_REGISTRY = {
    "vehicles_ke": {
        "enabled": [
            "FacebookMarketplaceScraper",
            "GoogleMapsScraper",
            "ClassifiedsScraper"
        ],
        "disabled": [
            "RedditScraper",
            "TwitterScraper",
            "GoogleCSEScraper",
            "InstagramScraper"
        ]
    }
}

def get_active_scrapers(category_key: str) -> List[str]:
    """
    🚫 Disabled scrapers never execute
    🚫 No wasted time
    🚫 No noise
    """
    registry = CATEGORY_SCRAPER_REGISTRY.get(category_key, {})
    return registry.get("enabled", [])

# Safety & Quota Tracking
QUOTAS = {
    "GoogleCSEScraper": {"limit": 100, "used": 0, "reset_at": 0},
}

# Core registry defining the static properties of each scraper
SCRAPER_REGISTRY = {
    "GoogleMapsScraper": {
        "enabled": True,
        "core": True,
        "mode": "production",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None # None means permanent
    },
    "ClassifiedsScraper": {
        "enabled": True,
        "core": True,
        "mode": "production",
        "cost": "free",
        "noise": "low",
        "categories": ["electronics", "cars", "real estate", "construction materials"],
        "enabled_until": None
    },
    "FacebookMarketplaceScraper": {
        "enabled": True,
        "core": True,
        "mode": "production",
        "cost": "free",
        "noise": "medium",
        "categories": ["electronics", "cars", "furniture", "tires"],
        "enabled_until": None
    },
    "TwitterScraper": {
        "enabled": False,
        "core": False,
        "mode": "production",
        "cost": "free",
        "noise": "high",
        "categories": ["jobs", "news", "events", "trending"],
        "enabled_until": None,
    },
    "RedditScraper": {
        "enabled": False,
        "core": False,
        "mode": "production",
        "cost": "free",
        "noise": "high",
        "categories": ["reviews", "discussions", "electronics"],
        "enabled_until": None,
    },
    "GoogleCSEScraper": {
        "enabled": False,
        "core": False,
        "mode": "production",
        "cost": "paid",
        "noise": "medium",
        "categories": ["all"],
        "enabled_until": None,
    },
    "InstagramScraper": {
        "enabled": False,
        "core": False,
        "mode": "sandbox",
        "cost": "free",
        "noise": "high",
        "categories": ["lifestyle", "electronics", "fashion"],
        "enabled_until": None,
    },
    "WhatsAppPublicGroupScraper": {
        "enabled": True,
        "core": False,
        "mode": "production",
        "cost": "free",
        "noise": "high",
        "categories": ["all"],
        "enabled_until": None
    }
}

def refresh_scraper_states():
    """Cleanup expired TTLs and enforce safety rules."""
    now = datetime.utcnow()
    for name, config in SCRAPER_REGISTRY.items():
        # Rule: Trae AI cannot disable core scrapers
        if config.get("core") and not config.get("enabled"):
            logger.warning(f"SAFETY: Restoring core scraper '{name}' which was incorrectly disabled.")
            config["enabled"] = True
            
        # TTL Auto-disable
        if not config.get("core") and config.get("enabled") and config.get("enabled_until"):
            if now > config["enabled_until"]:
                logger.info(f"TTL EXPIRED: Auto-disabling scraper '{name}'")
                config["enabled"] = False
                config["enabled_until"] = None

def update_scraper_state(name: str, enabled: bool, ttl_minutes: Optional[int] = None, caller: str = "System"):
    """Safely update scraper state with logging and safety checks."""
    if name not in SCRAPER_REGISTRY:
        return False, "Scraper not found"
        
    config = SCRAPER_REGISTRY[name]
    
    # ❌ SAFETY: Cannot disable core scrapers
    if config.get("core") and not enabled:
        logger.warning(f"SAFETY VIOLATION: Caller '{caller}' attempted to disable core scraper '{name}'. Blocked.")
        return False, "Cannot disable core scrapers"
        
    # ❌ SAFETY: Paid scrapers need quota approval
    if enabled and config.get("cost") == "paid":
        quota = QUOTAS.get(name, {})
        if quota.get("used", 0) >= quota.get("limit", 0):
            logger.error(f"QUOTA EXCEEDED: Caller '{caller}' failed to enable paid scraper '{name}' (Limit: {quota.get('limit')})")
            return False, f"Quota exceeded for paid scraper {name}"
        logger.info(f"QUOTA OK: Paid scraper '{name}' enabled by '{caller}' (Used: {quota.get('used')}/{quota.get('limit')})")

    # Set state
    config["enabled"] = enabled
    if enabled and ttl_minutes:
        config["enabled_until"] = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        logger.info(f"TOGGLE: '{caller}' enabled {name} until {config['enabled_until']} UTC (TTL: {ttl_minutes}m)")
    else:
        config["enabled_until"] = None
        logger.info(f"TOGGLE: '{caller}' {'enabled' if enabled else 'disabled'} {name}")
        
    return True, "Success"

def update_scraper_mode(name: str, mode: str, caller: str = "System"):
    """Update scraper mode (production/sandbox) with logging."""
    if name not in SCRAPER_REGISTRY:
        return False, "Scraper not found"
        
    if mode not in ["production", "sandbox"]:
        return False, f"Invalid mode: {mode}"
        
    config = SCRAPER_REGISTRY[name]
    old_mode = config.get("mode", "production")
    config["mode"] = mode
    
    logger.info(f"MODE CHANGE: '{caller}' changed {name} from {old_mode} to {mode}")
    return True, "Success"
