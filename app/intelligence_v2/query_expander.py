
from typing import List, Optional
from app.intelligence_v2.language_signals import SWAHILI_PATTERNS, ENGLISH_PATTERNS

def expand_query(product: str, location: str = "Kenya", category: Optional[str] = None) -> List[str]:
    """
    Expands a simple product/location pair into a high-yield search matrix.
    Replaces hard-coded brand lists with dynamic intent-based expansion.
    """
    if not product:
        return []

    # 1. Base variations
    queries = [
        f"{product} {location}",
        f"{product} for sale {location}",
    ]

    # 2. English Intent Expansion (Top 3 most effective for search)
    en_intents = ["looking for", "need", "anyone selling"]
    for intent in en_intents:
        queries.append(f"{intent} {product} {location}")

    # 3. Swahili/Local Intent Expansion (The "Natafuta" layer)
    sw_intents = ["natafuta", "nahitaji", "pata"]
    for intent in sw_intents:
        queries.append(f"{intent} {product} {location}")

    # 4. Category-specific context (if provided)
    if category:
        queries.append(f"{product} {category} {location}")
        queries.append(f"buy {product} {category} in {location}")

    # 5. Market-specific "Price" queries
    queries.append(f"price of {product} in {location}")
    queries.append(f"bei ya {product} {location}")

    # Deduplicate and return
    return list(dict.fromkeys(queries))
