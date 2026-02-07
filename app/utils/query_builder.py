from app.config.categories.vehicles_ke import VEHICLES_KE

def build_vehicle_query(raw_query: str) -> str:
    """
    Normalizes raw user queries into high-intent vehicle search strings.
    Ensures that scrapers receive optimized queries including objects, intent, and location.
    """
    base = raw_query.strip()
    
    # 🏎️ Extract top signals from locked config
    intent = " OR ".join(VEHICLES_KE["intent"][:3])
    objects = " OR ".join(VEHICLES_KE["objects"][:5])
    locations = " OR ".join(VEHICLES_KE["locations"][:3])

    # 🛠️ Construct the normalized query
    normalized = f"{base} ({objects}) ({intent}) ({locations})"
    
    # Clean up any potential double spaces and return
    return " ".join(normalized.split()).strip()
