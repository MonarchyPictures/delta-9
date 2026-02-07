import os

# 🌍 Environment Detection
ENV = os.getenv("DELTA9_ENV", "local")

if ENV == "local":
    PIPELINE_MODE = "bootstrap"
else:
    PIPELINE_MODE = "prod_strict"

# 🚀 Bootstrap rules for local development
# 🚫 Never show PROD_STRICT errors in local dev again.
BOOTSTRAP_RULES = {
    "min_sources": 1,
    "min_confidence": 0.4,
    "allow_unverified": True,
    "label": "Early signal (local)"
}

def is_prod() -> bool:
    return PIPELINE_MODE == "prod_strict"
