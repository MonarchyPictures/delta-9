from typing import List, Dict

class IntelligenceEngine:
    def __init__(self):
        self.market_prices = {
            "tires": 150.0, # Average price per unit
            "sugar": 0.5,   # Price per kg
            "sofa": 800.0,
            "laptop": 1200.0
        }

    def track_competitor_pricing(self, product_category: str, competitor_price: float):
        """Analyze competitor pricing against market average."""
        avg = self.market_prices.get(product_category.lower(), 0)
        if avg == 0:
            return "New category"
            
        diff = ((competitor_price - avg) / avg) * 100
        return {
            "category": product_category,
            "competitor_price": competitor_price,
            "market_avg": avg,
            "difference_pct": round(diff, 2),
            "is_competitive": diff <= 0
        }

    def identify_market_gaps(self, lead_count: int, supply_count: int):
        """Identify regions or products where demand outstrips supply."""
        if supply_count == 0:
            return "CRITICAL GAP: No supply for existing demand."
        
        ratio = lead_count / supply_count
        if ratio > 2.0:
            return f"HIGH DEMAND GAP: Demand is {round(ratio, 1)}x higher than supply."
        return "Balanced market"

    def generate_listing_description(self, buyer_request: str, product: str):
        """Generate an optimized product listing description (Automated Listing Gen)."""
        # In production, this would use a LLM like GPT-4
        return f"OPTIMIZED LISTING: High-quality {product} matching your request for '{buyer_request}'. Available now with fast delivery and competitive pricing."
