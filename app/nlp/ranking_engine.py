from datetime import datetime, timedelta

class RankingEngine:
    def __init__(self):
        self.weights = {
            "intent": 0.5,
            "freshness": 0.3,
            "distance": 0.2
        }

    def calculate_rank(self, intent_score, timestamp, distance_km=None, max_distance=50):
        """
        Calculate a final rank score (0-1) for a lead.
        - intent_score: 0 to 1
        - timestamp: datetime object
        - distance_km: distance in km from search center
        """
        # 1. Freshness Score (Last 72 hours)
        age_hours = (datetime.utcnow() - timestamp).total_seconds() / 3600
        freshness_score = max(0, (72 - age_hours) / 72)
        
        # 2. Distance Score
        distance_score = 1.0
        if distance_km is not None:
            distance_score = max(0, (max_distance - distance_km) / max_distance)
            
        # 3. Weighted Sum
        final_score = (
            (intent_score * self.weights["intent"]) +
            (freshness_score * self.weights["freshness"]) +
            (distance_score * self.weights["distance"])
        )
        
        return final_score

    def rank_leads(self, leads, center_coords=None, max_distance=50):
        """Rank a list of leads."""
        from app.utils.geo_service import GeoService
        geo = GeoService()
        
        ranked_results = []
        for lead in leads:
            # Calculate distance if center_coords provided
            dist = None
            if center_coords and lead.latitude and lead.longitude:
                dist = geo.calculate_distance(center_coords, (lead.latitude, lead.longitude))
            
            rank = self.calculate_rank(
                lead.intent_score,
                lead.created_at,
                distance_km=dist,
                max_distance=max_distance
            )
            
            # Add rank to lead data (converted to dict for API)
            lead_dict = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
            lead_dict["rank_score"] = rank
            lead_dict["distance_km"] = dist
            ranked_results.append(lead_dict)
            
        # Sort by rank score descending
        return sorted(ranked_results, key=lambda x: x["rank_score"], reverse=True)
