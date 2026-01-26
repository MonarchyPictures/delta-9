import uuid
from datetime import datetime

class LeadUtils:
    @staticmethod
    def infer_location(text):
        """Extract or infer location from text."""
        # Simple regex-based inference for common patterns
        # In a real app, use spaCy or a Geo-parsing API
        locations = ["Austin", "London", "Dubai", "New York", "Chicago", "Lagos", "Nairobi", "Singapore", "Toronto"]
        for loc in locations:
            if loc.lower() in text.lower():
                return loc
        return "Unknown"

    @staticmethod
    def generate_message(lead):
        """Generate a personalized message for the lead."""
        name = lead.get('buyer_name', 'there')
        product = lead.get('product_category', 'what you are looking for')
        location = lead.get('location', '')
        
        message = f"Hi {name}, I saw your post about needing {product}"
        if location and location != "Unknown":
            message += f" in {location}"
        message += ". We have a few options available that might fit your needs perfectly. Are you still looking to buy?"
        
        return message

    @staticmethod
    def format_lead(platform, post_link, text, category, name, location=None):
        """Format raw data into the required JSON structure."""
        return {
            "lead_id": f"LGD-{uuid.uuid4().hex[:6].upper()}",
            "source_platform": platform,
            "post_link": post_link,
            "timestamp": datetime.now().isoformat(),
            "location": location or LeadUtils.infer_location(text),
            "radius_km": 0,
            "buyer_request_snippet": text[:200] + "..." if len(text) > 200 else text,
            "product_category": category,
            "buyer_name": name,
            "contact_phone": "",
            "contact_email": "",
            "social_links": [post_link],
            "intent_score": 0.0, # To be filled by intent engine
            "notes": ""
        }
