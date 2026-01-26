import re

class IntentEngine:
    def __init__(self):
        self.intent_keywords = [
            "buying", "need", "looking for", "want to purchase", 
            "urgent", "anyone selling", "where can I get", 
            "price for", "bulk order", "asap", "now", "today",
            "ready to buy", "in stock", "looking to buy", "best price for",
            "wtb", "iso", "in search of", "does anyone have", "ordering",
            "wholesale", "supplier needed", "looking for vendor", "where to buy"
        ]
        self.exclusion_keywords = [
            "review", "news", "history", "like", "best of", "tutorial",
            "how to", "opinion", "thought on", "thinking about", "scam"
        ]

    def calculate_intent_score(self, text):
        """Calculate a score from 0.0 to 1.0 based on buyer intent."""
        text = text.lower()
        
        # Check for exclusions first
        for word in self.exclusion_keywords:
            if word in text:
                return 0.0
        
        score = 0.0
        matches = 0
        for word in self.intent_keywords:
            if word in text:
                matches += 1
                # Weight urgent words higher
                if word in ["urgent", "asap", "now", "today"]:
                    score += 0.3
                else:
                    score += 0.15
        
        # Normalize score
        final_score = min(score, 1.0)
        return round(final_score, 2)

    def is_valid_lead(self, text):
        """Boolean check for lead validity."""
        return self.calculate_intent_score(text) > 0.4

if __name__ == "__main__":
    engine = IntentEngine()
    test_text = "I urgently need 4 new tires for my truck today. Anyone selling?"
    print(f"Score: {engine.calculate_intent_score(test_text)}")
