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
    "FacebookMarketplaceScraper",
    "GoogleMapsScraper",
    "ClassifiedsScraper",
    "TwitterScraper",
    "RedditScraper",
    "InstagramScraper",
    "GoogleCSEScraper",
    "GoogleScraper",
    "WhatsAppPublicGroupScraper"
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
        "enabled": True,
        "core": False,
        "mode": "production",
        "cost": "free",
        "noise": "high",
        "categories": ["all"],
        "enabled_until": None
    },
    "InstagramScraper": {
        "enabled": True,
        "core": False,
        "mode": "production",
        "cost": "free",
        "noise": "high",
        "categories": ["all"],
        "enabled_until": None
    },
    "GoogleCSEScraper": {
        "enabled": True,
        "core": False,
        "mode": "production",
        "cost": "paid",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    },
    "GoogleScraper": {
        "enabled": True,
        "core": True,
        "mode": "production",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    },
    "WhatsAppPublicGroupScraper": {
        "enabled": True,
        "core": True,
        "mode": "production",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    },
    "BootstrapScraper": {
        "enabled": False,
        "core": False,
        "mode": "bootstrap",
        "cost": "free",
        "noise": "low",
        "categories": ["all"],
        "enabled_until": None
    }
}

def refresh_scraper_states():
    """Cleanup expired TTLs and enforce safety rules."""
    now = datetime.utcnow()
    
    # Sync with GLOBAL SCRAPER_CONFIG
    mapping = {
        "facebook": "FacebookMarketplaceScraper",
        "twitter": "TwitterScraper",
        "reddit": "RedditScraper",
        "google_cse": "GoogleCSEScraper"
    }
    for k, v in SCRAPER_CONFIG.items():
        if k in mapping:
            s_name = mapping[k]
            if s_name in SCRAPER_REGISTRY:
                SCRAPER_REGISTRY[s_name]["enabled"] = v.get("enabled", False)

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
    
    # Update DB if disabled by Optimizer
    if not enabled and caller == "Self-Optimization Engine":
        try:
            from app.db.database import SessionLocal
            from app.db import models
            db = SessionLocal()
            db_metric = db.query(models.ScraperMetric).filter_by(scraper_name=name).first()
            if db_metric:
                db_metric.auto_disabled = 1
                db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Failed to sync auto_disabled to DB for {name}: {e}")
        
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
