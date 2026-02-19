import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")

# Production strict mode toggle
PROD_STRICT = False
ALLOW_MOCK = True  # Default to True for dev

# Intent scoring threshold
INTENT_THRESHOLD = 0.15
MIN_INTENT_SCORE = INTENT_THRESHOLD  # Alias for compatibility

# Require independent verification
REQUIRE_VERIFICATION = False

# High Recall Mode (New Feature Flag)
HIGH_RECALL_MODE = True

# Production Safety Guard
if ENV == "production" or os.getenv("PIPELINE_MODE") == "strict":
    HIGH_RECALL_MODE = False
    # Lower threshold to 0.45 even in strict mode to fix "restriction" complaints
    INTENT_THRESHOLD = float(os.getenv("MIN_INTENT_SCORE", 0.45))
    MIN_INTENT_SCORE = INTENT_THRESHOLD  # Update alias
    REQUIRE_VERIFICATION = True # Real verified sources only
    PROD_STRICT = True  # Enforce strict mode in production
    ALLOW_MOCK = False # FORCE MOCK OFF IN PROD
elif os.getenv("ALLOW_MOCK", "false").lower() == "false":
    ALLOW_MOCK = False # Respect manual override even in dev



# Legacy compatibility (optional, derived from new flags)
# If strict is explicitly on, we are strict. Otherwise, likely relaxed.
from app.core.pipeline_mode import PIPELINE_MODE
BOOTSTRAP = PIPELINE_MODE == "bootstrap"
PROD_RELAXED = PIPELINE_MODE == "relaxed"
