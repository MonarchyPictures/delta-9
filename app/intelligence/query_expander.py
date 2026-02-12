
import logging
from typing import List

logger = logging.getLogger("QueryExpander")

# 🚗 AUTOMOTIVE & VEHICLE CONTEXT (Dominant Market in Kenya)
# These expansions ensure we hit colloquialisms and specific model variations
VEHICLE_SYNONYMS = {
    "toyota": ["vitz", "axio", "fiedler", "prado", "land cruiser", "hilux", "rav4", "premio"],
    "nissan": ["note", "tiida", "sylphy", "x-trail", "navara", "serena", "advan"],
    "mazda": ["demio", "cx-5", "axela", "atenza"],
    "honda": ["fit", "cr-v", "civic", "vezel", "stream"],
    "isuzu": ["nkr", "nqr", "frr", "d-max", "mux"],
    "mitsubishi": ["fuso", "canter", "lancer", "pajero", "outlander"],
    "subaru": ["forester", "impreza", "outback", "legacy"],
    "car": ["vehicle", "motorcar", "ride", "automobile"],
    "truck": ["lorry", "pickup", "canter", "fuso"],
    "spare parts": ["spares", "engine", "gearbox", "suspension", "rims", "tyres"]
}

# 🇰🇪 KENYAN COLLOQUIALISMS & INTENT VARIANTS
KENYAN_INTENT_VARIANTS = [
    "uko na", "who has", "anyone selling", "where can i find", 
    "nataka", "natafuta", "bei ya", "how much is"
]

class AIQueryExpander:
    """
    AI-driven query expansion layer to increase discovery yield.
    Focuses on semantic synonyms and local market variations.
    """
    
    @staticmethod
    def expand(query: str) -> List[str]:
        if not query:
            return []
            
        q = query.lower().strip()
        expanded_set = {q}
        
        # 1. Pluralization / Singularization
        if q.endswith('s') and len(q) > 3:
            expanded_set.add(q[:-1])
        elif not q.endswith('s'):
            expanded_set.add(f"{q}s")
            
        # 2. Automotive Context Expansion (Kenya specific)
        for base, synonyms in VEHICLE_SYNONYMS.items():
            if base in q:
                for syn in synonyms:
                    expanded_set.add(syn)
            # Reverse check: if they search for "vitz", we should also search for "toyota"
            elif any(syn in q for syn in synonyms):
                expanded_set.add(base)

        # 3. Handle multi-word queries (e.g., "toyota spare parts")
        words = q.split()
        if len(words) > 1:
            for word in words:
                if len(word) > 3:
                    expanded_set.add(word)

        final_queries = list(expanded_set)
        logger.info(f"AI EXPAND: '{query}' -> {final_queries}")
        return final_queries

def get_expanded_queries(query: str) -> List[str]:
    """Helper function for ingestion pipeline integration."""
    return AIQueryExpander.expand(query)
