import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# 🌍 Pipeline Configuration
# KEEP ONLY: bootstrap (local + dev), strict (future prod)
PIPELINE_MODE = os.getenv("PIPELINE_MODE", "bootstrap").lower()
if PIPELINE_MODE not in ["bootstrap", "strict"]:
    PIPELINE_MODE = "bootstrap"

# Single rule: Flexible query-based discovery
PIPELINE_QUERY = os.getenv("PIPELINE_QUERY", "").lower()
PIPELINE_CATEGORY = os.getenv("PIPELINE_CATEGORY", "general").lower()

# 🚀 Bootstrap rules for local development
BOOTSTRAP_RULES = {
    "min_sources": 1,
    "min_confidence": 0.4,
    "allow_unverified": True,
    "label": "Early signal (local)"
}

def is_prod() -> bool:
    return PIPELINE_MODE == "strict"

def is_bootstrap() -> bool:
    return PIPELINE_MODE == "bootstrap"
