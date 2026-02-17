import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")

# Production strict mode toggle
PROD_STRICT = False

# Intent scoring threshold
INTENT_THRESHOLD = 0.15

# Require independent verification
REQUIRE_VERIFICATION = False

# High Recall Mode (New Feature Flag)
HIGH_RECALL_MODE = True

# Production Safety Guard
if ENV == "production":
    HIGH_RECALL_MODE = False
    INTENT_THRESHOLD = 0.3
    PROD_STRICT = True  # Enforce strict mode in production


# Legacy compatibility (optional, derived from new flags)
# If strict is explicitly on, we are strict. Otherwise, likely relaxed.
from app.core.pipeline_mode import PIPELINE_MODE
BOOTSTRAP = PIPELINE_MODE == "bootstrap"
PROD_RELAXED = PIPELINE_MODE == "relaxed"
