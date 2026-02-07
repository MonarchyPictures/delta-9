import os 
from app.core.pipeline_mode import PIPELINE_MODE, ENV as DELTA9_ENV

PROD_STRICT = PIPELINE_MODE == "prod_strict"

# --- Render-ready PROD Hardening ---
# Shared secret for signing admin headers. 
# MUST be set in Render environment variables for prod.
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "d9_dev_local_secret_2024")

# --- Adaptive Scraper Control (Trae AI Driven) ---
# This is now managed via app/scrapers/registry.py
def is_source_enabled(source: str) -> bool:
    """
    Legacy wrapper for source enablement. 
    In the new architecture, LiveLeadIngestor uses decide_scrapers() for dynamic control.
    """
    from app.scrapers.registry import SCRAPER_REGISTRY
    config = SCRAPER_REGISTRY.get(source, {})
    if config.get("core"):
        return True
    return config.get("enabled", False)

# Log the status for visibility
import logging
logger = logging.getLogger("Config")
logger.info(f"--- Configuration Loaded: ENV={DELTA9_ENV}, PROD_STRICT={PROD_STRICT}, PIPELINE_MODE={PIPELINE_MODE} ---")
