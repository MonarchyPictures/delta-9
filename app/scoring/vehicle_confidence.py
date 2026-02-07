def score_vehicle_signal(signal: dict) -> float:
    """
    Calculates a confidence score specifically for vehicle market signals.
    Score components:
    - Price availability: +0.25
    - Location availability: +0.20
    - Contact info availability: +0.25
    - High-trust sources (FB/Classifieds): +0.20
    - Recency signal: +0.10
    """
    score = 0.0

    # 💰 Price availability
    if signal.get("price") or signal.get("buyer_budget"):
        score += 0.25
    
    # 📍 Location availability
    if signal.get("location") or signal.get("location_raw"):
        score += 0.20
    
    # 📞 Contact info (phone, whatsapp, etc)
    if signal.get("contact") or signal.get("buyer_contact") or signal.get("whatsapp_link"):
        score += 0.25
    
    # 🏛️ Trusted Sources for Vehicles
    source = str(signal.get("source", "")).lower()
    scraper_name = str(signal.get("_scraper_name", "")).lower()
    if any(s in source or s in scraper_name for s in ["facebook", "classifieds", "jiji"]):
        score += 0.20
    
    # ⏱️ Recency signal (within the last 24h or explicitly marked as recent)
    if signal.get("timestamp_recent") or signal.get("is_recent"):
        score += 0.10

    return round(score, 2)
