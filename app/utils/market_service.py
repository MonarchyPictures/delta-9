import random

class MarketIntelligenceService:
    def __init__(self):
        # Mock market data for Kenyan context
        self.market_prices = {
            "water tank": "Ksh 5,000 - 500,000",
            "toyota camry": "Ksh 600,000 - 2,500,000",
            "construction": "Ksh 20,000 - 1,000,000",
            "electronics": "Ksh 10,000 - 200,000"
        }
        
    def get_market_context(self, product_category):
        """Provide market context for a given product category."""
        category = product_category.lower()
        
        # Use a seed based on category to make "random" values stable
        seed = sum(ord(c) for c in category)
        rng = random.Random(seed)
        
        # 1. Price Range
        price_range = "Negotiable"
        # Split category into words for better matching
        cat_words = set(category.lower().split())
        for key, val in self.market_prices.items():
            key_words = set(key.lower().split())
            if key_words.intersection(cat_words):
                price_range = val
                break
                
        # 2. Seasonal Demand
        seasonality = rng.choice(["Peak", "Normal", "Off-season"])
        if any(kw in category for kw in ["tank", "construction", "water"]):
            seasonality = "Peak" # Always high demand in Kenya for these
            
        # 3. Supply Status
        supply = rng.choice(["Shortage", "Stable", "Oversupply"])
        if "50,000" in category:
            supply = "Shortage" # Large tanks are often in short supply
            
        return {
            "price_range": price_range,
            "seasonality": seasonality,
            "supply_status": supply
        }

    def get_buyer_profile(self, buyer_name, platform):
        """Mock buyer profile history based on platform and name."""
        # Use a seed based on buyer name to make "random" values stable
        seed = sum(ord(c) for c in buyer_name.lower())
        rng = random.Random(seed)
        
        activity = "Medium"
        if platform == "Facebook": activity = "High"
        elif platform == "Reddit": activity = "Low"
        
        return {
            "history": {
                "purchase_count": rng.randint(0, 5),
                "avg_decision_days": rng.randint(1, 14)
            },
            "activity_level": activity,
            "response_rate": rng.randint(30, 95)
        }

    def calculate_seller_advantages(self, lead_data, seller_inventory=None):
        """Identify competitive advantages for the seller."""
        advantages = ["Verified Seller", "Local Business"]
        
        if lead_data.get("delivery_range_score", 0) > 80:
            advantages.append("Fastest Delivery")
            
        if lead_data.get("match_score", 0) > 90:
            advantages.append("Exact Inventory Match")
            
        if lead_data.get("readiness_level") == "HOT":
            advantages.append("Ready for Immediate Sale")
            
        return advantages

    def recommend_pricing_strategy(self, lead_data):
        """Recommend a pricing strategy based on lead intelligence."""
        if lead_data.get("readiness_level") == "HOT" and lead_data.get("urgency_score", 0) > 8:
            return "Premium" # High urgency, high willingness to pay
        elif lead_data.get("competition_count", 0) > 10:
            return "Aggressive" # High competition
        else:
            return "Competitive" # Standard approach
