import os 
from app.core.pipeline_mode import PIPELINE_MODE, PIPELINE_CATEGORY

# Simplified flags for deprecated config
PROD_STRICT = PIPELINE_MODE == "strict"
BOOTSTRAP = PIPELINE_MODE == "bootstrap"

# --- Render-ready PROD Hardening ---
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "d9_dev_local_secret_2024")

# Log the status for visibility
import logging
logger = logging.getLogger("ConfigDeprecated")
logger.info(f"--- DEPRECATED CONFIG: MODE={PIPELINE_MODE}, CATEGORY={PIPELINE_CATEGORY} ---")
