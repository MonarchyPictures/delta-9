
def buyer_match_score(vehicle, buyer): 
    """
    Calculates the match score between a vehicle (lead) and a buyer profile.
    
    Args:
        vehicle: An object or dict with .type (or ['product_category']), .price, .location, .urgency_score, .final_score
        buyer: An object or dict with .vehicle_type, .budget_min, .budget_max, .location, .urgency
    """
    score = 0.0 

    # Helper to get values from either object or dict
    def get_val(obj, key, default=None):
        if hasattr(obj, key):
            return getattr(obj, key)
        if isinstance(obj, dict):
            # Map common keys if they differ
            mapping = {
                'type': 'product_category',
                'price': 'price',
                'location': 'location_raw', # Fixed to use location_raw from lead data
                'urgency_score': 'intent_strength', # Mapping from lead data
                'final_score': 'intent_strength'    # Using intent_strength as final_score fallback
            }
            actual_key = mapping.get(key, key)
            return obj.get(actual_key, default)
        return default

    v_type = get_val(vehicle, 'type')
    b_type = get_val(buyer, 'vehicle_type')
    if b_type and v_type and b_type.lower() in v_type.lower(): 
        score += 0.25 

    v_price = get_val(vehicle, 'price')
    b_min = get_val(buyer, 'budget_min')
    b_max = get_val(buyer, 'budget_max')
    if b_min and b_max and v_price: 
        if b_min <= v_price <= b_max: 
            score += 0.30 

    v_loc = get_val(vehicle, 'location')
    b_loc = get_val(buyer, 'location')
    if b_loc and v_loc and b_loc.lower() == v_loc.lower(): 
        score += 0.15 

    b_urgency = get_val(buyer, 'urgency', 0)
    v_urgency = get_val(vehicle, 'urgency_score', 0)
    if b_urgency > 0.7 and v_urgency > 0.7: 
        score += 0.20 

    v_final = get_val(vehicle, 'final_score', 0)
    if v_final > 0.75: 
        score += 0.10 

    return round(min(score, 1.0), 2)
