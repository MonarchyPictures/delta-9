# Expansion Roadmap: Delta9 Category Cloning

This document outlines the protocol for expanding Delta9 beyond the Vehicles category. Expansion must only occur after the Vehicles category has consistently hit its success metrics (5-10 leads/day, 1+ tap/hour).

## Phase 1: The Proof (Current)
- **Status**: Vehicles Only.
- **Goal**: Establish a baseline of 5-10 high-confidence vehicle leads per day.
- **KPI Visibility**: Monitor the **Money Metrics Grid** on the Dashboard.

## Phase 2: Pipeline Cloning
The pipeline has been modularized to allow cloning via `app/core/category_config.py`.

### Step 1: Define the Next Category
Add a new entry to `CategoryConfig.CATEGORIES` in `[category_config.py](file:///e:/delta-9/delta-9-1/app/core/category_config.py)`:
- **Keywords**: Industry-specific terms for content filtering.
- **Search Terms**: High-intent phrases for scraper discovery.
- **Price Bands**: Typical price ranges to validate lead confidence.
- **Locations**: Target geographic regions.

### Step 2: Adjust Language & Price Bands
- **Language**: Update `language_templates` in the config for category-specific intent (e.g., "looking for rental" vs "looking for toyota").
- **Price Bands**: Ensure bands reflect the new category's market value. The NLP engine in `[intent_service.py](file:///e:/delta-9/delta-9-1/app/nlp/intent_service.py)` will automatically use these to penalize out-of-band "noise" signals.

### Step 3: Activation
Once the configuration is ready, set `is_active: True` for the new category.
```python
"real_estate": {
    ...
    "is_active": True # Enable this only after Vehicles proof
}
```

## Phase 3: Domain Lockdown
To prevent "category bleed", the system will only process data for categories marked as `is_active`. This ensures that even if a scraper finds a real estate lead while the system is in "Vehicles Only" mode, it will be filtered out at the NLP layer.

---
**Hard Rule**: If Vehicles isn’t amazing, nothing else matters. Do not activate Phase 3 until Phase 1 is verified.
