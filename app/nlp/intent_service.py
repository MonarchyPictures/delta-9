import re
from datetime import datetime, timedelta

class BuyingIntentNLP:
    def __init__(self):
        # Disable spacy on Python 3.12+ due to Pydantic V1 incompatibility
        self.nlp = None
        # self.nlp = spacy.load("en_core_web_sm")
        
        self.intent_patterns = [
            "buying", "need", "looking for", "want to purchase", 
            "urgent", "asap", "price for", "bulk order",
            "ready to buy", "wtb", "iso", "searching for"
        ]

    def extract_entities(self, text):
        """Extract products, locations, and names."""
        entities = {"products": [], "locations": [], "names": []}
        
        if self.nlp:
            try:
                doc = self.nlp(text)
                entities["locations"] = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]]
                entities["names"] = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
                
                # Simple product extraction logic (Noun Phrases)
                for chunk in doc.noun_chunks:
                    if not any(word in chunk.text.lower() for word in self.intent_patterns):
                        entities["products"].append(chunk.text)
                return entities
            except Exception:
                pass # Fallback to regex if spacy fails at runtime

        # REGEX FALLBACK
        # Basic Kenya location detection
        kenya_cities = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Kenya", "Thika", "Naivasha", "Malindi"]
        for city in kenya_cities:
            if re.search(rf"\b{city}\b", text, re.IGNORECASE):
                entities["locations"].append(city)
        
        # Product Specificity Algorithm
        # Extract specs like size (50,000l, 10kg), model (2005, v8), price (50k)
        specs = {}
        # Improved regex for numbers with commas and units
        size_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)\s*(l|liters|kg|units|pcs|pieces|ton|tons|ft|inches)\b', text, re.IGNORECASE)
        if size_match:
            specs["size"] = f"{size_match.group(1)} {size_match.group(2)}"
            
        model_match = re.search(r'\b(20\d{2}|19\d{2})\b', text)
        if model_match:
            specs["model_year"] = model_match.group(1)

        entities["specs"] = specs
        
        # Basic name detection (Capitalized words that aren't start of sentence)
        
        # Basic product detection (words after intent patterns)
        # Improved product extraction: look for nouns after intent keywords
        noise_words = [
            'clean', 'new', 'used', 'cheap', 'good', 'searching', 'looking', 
            'it', 'this', 'that', 'something', 'someone', 'delivered', 
            'to', 'for', 'a', 'an', 'the', 'in', 'at', 'by', 'with', 'asap',
            'delivery', 'urgent', 'urgently', 'me', 'us', 'i', 'my'
        ]
        
        for pattern in self.intent_patterns:
            # Match until a known delimiter or end of sentence, but be greedy enough to capture the product
            # Use non-greedy match to stop at first delimiter
            match = re.search(rf"{pattern}\s+(?:a|an|the)?\s*([\w\s,]+?)(?:\s+in\b|\s+at\b|\s+by\b|\s+with\b|\s+for\b|\s+asap\b|\s+delivered\b|\.|$)", text, re.IGNORECASE)
            if match:
                product_raw = match.group(1).strip()
                # Split by common conjunctions and take the first part if it's too long
                product_parts = re.split(r'\b(and|or|with|to)\b', product_raw, flags=re.IGNORECASE)
                product = product_parts[0].strip()
                
                # Clean up product string (remove common noise)
                words = product.split()
                cleaned_words = [w for w in words if w.lower() not in noise_words]
                product = " ".join(cleaned_words).strip()
                
                # Further filter: if it contains a city/neighborhood, it's likely noise or location
                is_location = any(loc.lower() in product.lower() for loc in entities["locations"])
                if not is_location and product and len(product) > 3: 
                    if product.lower() not in [p.lower() for p in entities["products"]]:
                        entities["products"].append(product)
        
        # If no products found, try simple keyword match from common high-intent categories
        if not entities["products"]:
            common_products = ["chicken feed", "poultry feed", "car", "phone", "land", "apartment", "house", "furniture", "water", "tank"]
            for cp in common_products:
                if cp in text.lower():
                    entities["products"].append(cp.title())
                    break
                
        return entities

    def analyze_readiness(self, text):
        """
        Classify Buyer Readiness:
        - HOT: Immediate purchase intent + specs + urgency
        - WARM: Interest + products
        - RESEARCHING: General mentions
        """
        text_lower = text.lower()
        score = self.calculate_intent_score(text)
        
        # Urgency Indicators
        urgency_keywords = ["asap", "urgent", "immediately", "now", "today", "fast", "needed by", "quick"]
        has_urgency = any(u in text_lower for u in urgency_keywords)
        
        # Spec Indicators (Size, Model, Price)
        has_specs = bool(re.search(r'(\d+)\s*(l|kg|units|pcs|ton|20\d{2}|ksh|sh|k\b)', text_lower))
        
        # Classification
        if score > 0.7 and (has_urgency or has_specs):
            return "HOT", min(score * 10, 10.0)
        elif score > 0.4:
            return "WARM", min(score * 8, 10.0)
        else:
            return "RESEARCHING", min(score * 5, 10.0)

    def extract_budget(self, text):
        """Extract price mentions or budget ranges."""
        # Kenyan budget formats: Ksh 50k, 50,000/-, 50k, 50000 sh
        budget_pattern = r'(ksh|sh|shilling|shillings)?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(k|m)?\s*(/-|sh|ksh)?'
        match = re.search(budget_pattern, text, re.IGNORECASE)
        if match:
            val = match.group(2).replace(',', '')
            suffix = match.group(3).lower() if match.group(3) else ''
            if suffix == 'k': val = f"{int(val) * 1000}"
            elif suffix == 'm': val = f"{int(val) * 1000000}"
            return f"Ksh {int(val):,}"
        return "Negotiable"

    def calculate_intent_score(self, text):
        """Calculate intent using linguistic features."""
        score = 0.0
        text_lower = text.lower()
        
        # 1. Keyword match (Strong intent signals)
        high_intent = ["looking for", "want to buy", "buying", "need to purchase", "searching for", "where can i find", "anyone selling", "recommend", "where can i buy"]
        medium_intent = ["price for", "how much is", "cost of", "recommendations for", "best place for", "who has", "where is"]
        
        # Social media specific intent signals
        social_intent = ["pls assist", "help me find", "anyone know where", "kindly suggest", "where to get"]
        if any(si in text_lower for si in social_intent):
            score += 0.3

        for pattern in high_intent:
            if pattern in text_lower:
                score += 0.5 # Increased from 0.4
                break 
                
        for pattern in medium_intent:
            if pattern in text_lower:
                score += 0.3 # Increased from 0.2
                break
        
        # 2. Urgency check
        urgency_keywords = ["urgent", "asap", "immediately", "now", "today", "fast"]
        if any(u in text_lower for u in urgency_keywords):
            score += 0.3
            
        # 3. Contact info check (High intent signal)
        if re.search(r'(\+?254|0)(7|1)\d{8}', text) or re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            score += 0.3
            
        # 4. Quantity/Budget signals
        if re.search(r'\b\d+\s*(kg|liters|l|units|pieces|pcs|ksh|sh)\b', text_lower):
            score += 0.2
            
        # 5. Length penalty/bonus
        # Very short snippets (less than 30 chars) are often noise
        if len(text_lower) < 30:
            # If it has a high intent keyword, don't penalize as much
            if any(p in text_lower for p in high_intent):
                score -= 0.1
            else:
                score -= 0.3
        # Medium length snippets are often better
        elif 50 < len(text_lower) < 300:
            score += 0.1

        return max(0.0, min(score, 1.0))

    def analyze_intent_extensions(self, text):
        """Extract quantity, payment methods, etc."""
        text_lower = text.lower()
        
        # 1. Quantity Detection
        quantity = "Single Unit"
        qty_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)\s*(units|pcs|pieces|kg|liters|l|ton|bags|boxes)', text_lower)
        if qty_match:
            quantity = f"{qty_match.group(1)} {qty_match.group(2)}"
        elif "bulk" in text_lower or "wholesale" in text_lower:
            quantity = "Bulk"
            
        # 2. Payment Method Detection
        payment = "Negotiable"
        payment_map = {
            "m-pesa": ["mpesa", "m-pesa", "lipa na mpesa", "send money"],
            "cash": ["cash", "on delivery", "cod"],
            "installments": ["installments", "pole pole", "monthly", "credit"],
            "bank": ["bank transfer", "eft", "rtgs"]
        }
        for method, keywords in payment_map.items():
            if any(kw in text_lower for kw in keywords):
                payment = method.capitalize()
                break
                
        return quantity, payment

    def analyze_local_advantage(self, text):
        """Extract neighborhood and local preferences."""
        text_lower = text.lower()
        
        # 1. Neighborhood Detection (Kenya Specific)
        neighborhoods = [
            "Westlands", "Kilimani", "Kileleshwa", "Karen", "Runda", "South B", "South C", "Langata", "Embassy",
            "Pangani", "Parklands", "Donholm", "Buruburu", "Syokimau", "Kitengela", "Ruiru", "Juja", "Kiambu",
            "Nyali", "Bamburi", "Mtwapa", "Milimani", "Kondele", "Tom Mboya"
        ]
        neighborhood = None
        for n in neighborhoods:
            if re.search(rf"\b{n}\b", text, re.IGNORECASE):
                neighborhood = n
                break
        
        # 2. Pickup Preference
        pickup = 0
        if any(kw in text_lower for kw in ["pickup", "pick up", "collection", "collect"]):
            pickup = 1
            
        # 3. Delivery Constraints
        constraints = None
        delivery_keywords = ["deliver before", "same day", "within", "must be delivered", "drop off at", "delivered to"]
        for kw in delivery_keywords:
            if kw in text_lower:
                match = re.search(rf"{kw}\s+([^,.]+)", text_lower)
                if match:
                    constraints = f"{kw} {match.group(1).strip()}"
                    break
                    
        return neighborhood, pickup, constraints

    def assess_deal_readiness(self, text):
        """Assess decision authority, research, and deadlines."""
        text_lower = text.lower()
        
        # 1. Decision Authority
        authority = 0
        if any(kw in text_lower for kw in ["i am buying", "my company", "i need", "i want", "direct buyer", "for my house", "for my car"]):
            authority = 1
        
        # 2. Budget Approval / Readiness
        budget_ready = 0
        if any(kw in text_lower for kw in ["budget is ready", "cash ready", "finance approved", "already have the money", "willing to pay"]):
            budget_ready = 1
            
        # 3. Prior Research
        research = 0
        if any(kw in text_lower for kw in ["compared", "best price", "reviewed", "checked", "specs say", "seen others"]):
            research = 1
            
        # 4. Comparison
        comparison = 0
        if any(kw in text_lower for kw in ["vs", "better than", "instead of", "alternative to", "compared with"]):
            comparison = 1
            
        # 5. Upcoming Deadline
        deadline = None
        # Handle "by Friday", "before end of month", "deadline 25th", etc.
        deadline_match = re.search(r'(by|before|deadline|due)\s+([A-Za-z]+\s+\d{1,2}|\d{1,2}/\d{1,2}|\d{1,2}\s+[A-Za-z]+|today|tomorrow|friday|monday|next week)', text_lower)
        if deadline_match:
            keyword = deadline_match.group(2).strip()
            if keyword == "today":
                deadline = datetime.now()
            elif keyword == "tomorrow":
                deadline = datetime.now() + timedelta(days=1)
            elif "week" in keyword:
                deadline = datetime.now() + timedelta(days=7)
            else:
                # Default to 3 days if specific date parsing is complex
                deadline = datetime.now() + timedelta(days=3)
            
        return authority, research, comparison, deadline, budget_ready

    def extract_conversion_signals(self, text):
        """Detect language indicating imminent purchase and specific buyer signals."""
        text_lower = text.lower()
        signals = []
        
        # Imminent Purchase Language
        imminent_keywords = ["buying today", "need now", "buying as soon as", "ready to pick up", "where are you located", "asap", "urgently"]
        if any(kw in text_lower for kw in imminent_keywords):
            signals.append("imminent_purchase")
            
        # Financing/Budget
        if any(kw in text_lower for kw in ["financing", "loan", "installment", "mpesa ready", "cash in hand", "budget is approved", "budget ready"]):
            signals.append("budget_approved")
            
        # Comparison Shopping
        if any(kw in text_lower for kw in ["vs", "other sellers", "best offer", "cheaper", "price match"]):
            signals.append("comparison_shopping")
            
        return signals

    def generate_talking_points(self, lead_data):
        """Generate specific talking points based on lead intent and seller match."""
        points = []
        product = lead_data.get("product_category", "item")
        
        # Base on urgency
        if lead_data.get("readiness_level") == "HOT":
            points.append(f"Mention immediate availability for the {product}.")
            
        # Base on location
        if lead_data.get("neighborhood"):
            points.append(f"Highlight same-day delivery to {lead_data['neighborhood']}.")
            
        # Base on budget
        if lead_data.get("budget_info") != "Negotiable":
            points.append(f"Acknowledge the {lead_data['budget_info']} budget and offer our competitive pricing.")
            
        # Base on specs
        if lead_data.get("product_specs"):
            specs_str = ", ".join([f"{k}: {v}" for k, v in lead_data['product_specs'].items()])
            points.append(f"Confirm we have the exact specs: {specs_str}.")
            
        if not points:
            points.append(f"Inquire about specific requirements for the {product}.")
            
        return points
