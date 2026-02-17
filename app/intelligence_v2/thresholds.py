from app.config.runtime import INTENT_THRESHOLD, PROD_STRICT

# 🚦 Intelligence Thresholds
# Global floors for production stability.

# Non-negotiable thresholds
STRICT_PUBLIC = INTENT_THRESHOLD if not PROD_STRICT else 0.65  # Use config threshold unless strict mode is forced
HIGH_INTENT   = 0.6
BOOTSTRAP     = 0.3
FLOOR         = 0.35  # Relaxed floor to match default intent threshold

# Operational windows
FRESHNESS_WINDOW_HOURS = 72
URGENT_FRESHNESS_HOURS = 24

# Legacy aliases (for backward compatibility)
MATCH_SCORE_THRESHOLD = STRICT_PUBLIC
HOT_LEAD_THRESHOLD = HIGH_INTENT
