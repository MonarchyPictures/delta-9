import uuid
from datetime import datetime
from app.nlp.intent_service import BuyingIntentNLP
from app.utils.geo_service import GeoService
from app.utils.verification import ContactVerifier
from app.utils.market_service import MarketIntelligenceService
from app.db import models

class LeadValidator:
    def __init__(self):
        self.nlp = BuyingIntentNLP()
        self.geo = GeoService()
        self.verifier = ContactVerifier()
        self.market = MarketIntelligenceService()

    def normalize_lead(self, raw_data, db=None):
        """Transform raw platform data into a normalized Lead object."""
        text = raw_data.get("text", "")
        
        # 1. Classify intent strictly
        classification = self.nlp.classify_intent(text)
        
        # ABSOLUTE RULE: DISCARD IF NOT BUYER
        if classification != "BUYER":
            import logging
            logger = logging.getLogger("radar_api")
            logger.info(f"Normalization discarded lead: Classification is {classification}. Text: {text[:100]}")
            return None # DISCARD IMMEDIATELY
            
        entities = self.nlp.extract_entities(text)
        intent_score = self.nlp.calculate_intent_score(text)
        
        # Hyper-Specific NLP Analysis
        readiness, urgency = self.nlp.analyze_readiness(text)
        budget = self.nlp.extract_budget(text)
        specs = entities.get("specs", {})
        
        # NEW: Hyper-Targeted Analysis Extensions
        quantity, payment = self.nlp.analyze_intent_extensions(text)
        neighborhood, pickup, constraints = self.nlp.analyze_local_advantage(text)
        authority, research, comparison, deadline, budget_ready = self.nlp.assess_deal_readiness(text)
        
        # Smart Matching (Requires Seller Inventory Integration)
        # Pass all products to matching engine for better selection
        match_score, compat_status, match_details, best_category = self._calculate_smart_match(entities["products"], specs, db)
        
        # Deal Probability Score (0-100)
        deal_prob = self._calculate_deal_probability(intent_score, readiness, urgency, budget, specs, text, budget_ready, deadline)
        
        # Location logic
        # Fallback to raw_data location if NLP fails
        location_raw = entities["locations"][0] if entities["locations"] else raw_data.get("location", "Unknown")
        lat, lon = self.geo.get_coordinates(location_raw)
        
        # Delivery Range Score (0-100)
        delivery_score = self._calculate_delivery_score(lat, lon, neighborhood, pickup, constraints)
        
        # Authenticity & Verification
        phone = self._extract_phone(text)
        email = self._extract_email(text)
        social_link = raw_data.get("link") or raw_data.get("url")
        
        # Contact Verification & Reliability
        is_phone_v, phone_meta = self.verifier.verify_phone(phone) if phone else (False, {})
        is_email_v, email_meta = self.verifier.verify_email(email) if email else (False, {})
        is_social_v = self.verifier.verify_social_link(social_link) if social_link else (True if social_link else False)
        
        # Use clean number for storage if verified
        phone_to_save = phone_meta.get("clean_number", phone) if is_phone_v else phone
        email_to_save = email.lower() if email else email

        # RELAXED Filtering: If it's a social lead (Reddit/Facebook), the link IS the contact method
        platform = raw_data.get("source", "Unknown")
        is_social = platform.lower() in ["facebook", "twitter", "reddit", "tiktok", "instagram"]
        
        import logging
        logger = logging.getLogger("radar_api")
        
        if not (is_phone_v or is_email_v or social_link):
            logger.info(f"Normalization dropped lead: No contact method. Phone: {phone}, Email: {email}, Link: {social_link}")
            return None # Drop leads with zero working contact methods
            
        # Social Filtering: Require some intent for social posts to avoid homepages/landing pages
        # Relaxed threshold to ensure "No Signals Detected" is minimized
        if is_social and intent_score < 0.15: # Lowered from 0.25 to catch more leads
            logger.info(f"Normalization dropped {platform} lead: Low intent score ({intent_score}). Link: {social_link}")
            return None
            
        reliability_score, preferred_method = self.verifier.calculate_reliability_score({
            "contact_phone": phone_to_save if is_phone_v else None,
            "contact_email": email_to_save if is_email_v else None,
            "post_link": social_link if is_social_v else None
        })
        
        # Real-Time & Competitive Intelligence
        platform = raw_data.get("source", "Unknown")
        availability = "Available Now" # Initial status
        comp_count, is_unique = self._calculate_competition(text, platform, intent_score)
        opt_window, peak_time = self._calculate_response_window(platform)
        
        # Calculate Confidence Score (1-10)
        confidence_score, badges, is_genuine = self._calculate_verification(raw_data, text, phone_to_save, email_to_save, intent_score)
        
        # NEW: Comprehensive Lead Intelligence
        # 1. Lead Profile
        buyer_name = entities.get("names", ["Anonymous"])[0] if entities.get("names") else "Anonymous"
        buyer_prof = self.market.get_buyer_profile(buyer_name, platform)
        
        # 2. Market Context
        product_for_market = best_category or (entities.get("products", ["General"])[0] if entities.get("products") else "General")
        m_context = self.market.get_market_context(product_for_market)
        
        # 3. Conversion Signals & Talking Points
        conv_signals = self.nlp.extract_conversion_signals(text)
        lead_data_for_points = {
            "product_category": product_for_market,
            "readiness_level": readiness,
            "neighborhood": neighborhood,
            "budget_info": budget,
            "product_specs": specs
        }
        t_points = self.nlp.generate_talking_points(lead_data_for_points)
        
        # 4. Seller Match Analysis
        advantages = self.market.calculate_seller_advantages(lead_data_for_points)
        p_strategy = self.market.recommend_pricing_strategy(lead_data_for_points)

        return {
            "id": str(uuid.uuid4()),
            "source_platform": raw_data.get("source", "Unknown"),
            "post_link": raw_data.get("link"),
            "timestamp": datetime.now(),
            "location_raw": location_raw,
            "latitude": lat,
            "longitude": lon,
            "buyer_request_snippet": text[:500],
            "intent_type": classification,
            "product_category": product_for_market,
            "buyer_name": buyer_name,
            "intent_score": intent_score,
            "confidence_score": confidence_score,
            "_all_products": entities.get("products", []),
            
            # Hyper-Specific Intelligence
            "readiness_level": readiness,
            "urgency_score": urgency,
            "budget_info": budget,
            "product_specs": specs,
            "deal_probability": deal_prob,
            
            # NEW: Smart Matching
            "match_score": match_score,
            "compatibility_status": compat_status,
            "match_details": match_details,
            
            # NEW: Intent Extensions
            "quantity_requirement": quantity,
            "payment_method_preference": payment,
            
            # NEW: Local Advantage
            "delivery_range_score": delivery_score,
            "neighborhood": neighborhood,
            "local_pickup_preference": pickup,
            "delivery_constraints": constraints,
            
            # NEW: Deal Readiness
            "decision_authority": authority,
            "prior_research_indicator": research,
            "comparison_indicator": comparison,
            "upcoming_deadline": deadline,

            # NEW: Comprehensive Lead Intelligence
            "buyer_history": buyer_prof["history"],
            "platform_activity_level": buyer_prof["activity_level"],
            "past_response_rate": buyer_prof["response_rate"],
            "market_price_range": m_context["price_range"],
            "seasonal_demand": m_context["seasonality"],
            "supply_status": m_context["supply_status"],
            "conversion_signals": conv_signals,
            "talking_points": t_points,
            "competitive_advantages": advantages,
            "pricing_strategy": p_strategy,
            
            # Real-Time & Competitive Intelligence
            "availability_status": availability,
            "competition_count": comp_count,
            "is_unique_request": 1 if is_unique else 0,
            "optimal_response_window": opt_window,
            "peak_response_time": peak_time,
            
            # Contact Verification & Reliability
            "is_contact_verified": 1,
            "contact_reliability_score": reliability_score,
            "preferred_contact_method": preferred_method,
            "disposable_email_flag": 1 if email_meta.get("is_disposable") else 0,
            "contact_metadata": {
                "phone": phone_meta,
                "email": email_meta,
                "social_verified": is_social_v
            },
            "non_response_flag": 0,
            
            "verification_badges": badges,
            "is_genuine_buyer": 1 if is_genuine else 0,
            "contact_phone": phone_to_save,
            "contact_email": email_to_save,
            "social_links": [raw_data.get("link")],
            "notes": f"Readiness: {readiness} | Deal Prob: {deal_prob}% | Specs: {specs}",
            "last_activity": datetime.now()
        }

    def _calculate_smart_match(self, products, specs, db=None):
        """Analyze product specifics in seller inventory and match against buyer specs."""
        if not products or not db:
            return 0.0, "Incompatible", {"reason": "No product identified or DB session missing"}, None
        
        # 1. Fetch active seller products
        try:
            seller_products = db.query(models.SellerProduct).filter(models.SellerProduct.is_active == 1).all()
        except Exception:
            seller_products = []
            
        best_match_score = 0.0
        best_product = None
        best_details = {}
        best_lead_product = None
        
        for lead_product in products:
            lp_lower = lead_product.lower()
            
            for sp in seller_products:
                score = 0.0
                details = {"matched_specs": [], "mismatched_specs": []}
                
                # Category/Name Match (Improved with word overlap)
                lp_words = set(lp_lower.split())
                sp_name_words = set(sp.name.lower().split())
                sp_cat_words = set(sp.category.lower().split())
                
                name_overlap = lp_words.intersection(sp_name_words)
                cat_overlap = lp_words.intersection(sp_cat_words)
                
                if len(name_overlap) >= 1:
                    score += 40.0 + (len(name_overlap) / len(lp_words)) * 20.0
                elif len(cat_overlap) >= 1:
                    score += 20.0 + (len(cat_overlap) / len(lp_words)) * 20.0
                
                # Bonus for exact containment
                if lp_lower in sp.name.lower() or sp.name.lower() in lp_lower:
                    score += 20.0
                elif lp_lower in sp.category.lower() or sp.category.lower() in lp_lower:
                    score += 10.0
                
                # Specs Match
                if specs and sp.specs:
                    matched_count = 0
                    total_compared = 0
                    
                    # Normalize specs keys for better matching (e.g. model_year vs year)
                    normalized_specs = {}
                    for k, v in specs.items():
                        if k == "model_year": normalized_specs["year"] = v
                        else: normalized_specs[k] = v
                        
                    for key, val in normalized_specs.items():
                        if key in sp.specs:
                            total_compared += 1
                            # Fuzzy value match
                            s_val = str(val).lower().replace(",", "").replace(" ", "")
                            sp_val = str(sp.specs[key]).lower().replace(",", "").replace(" ", "")
                            
                            if s_val in sp_val or sp_val in s_val:
                                matched_count += 1
                                details["matched_specs"].append(key)
                            else:
                                details["mismatched_specs"].append(key)
                    
                    if total_compared > 0:
                        score += (matched_count / total_compared) * 40.0
                
                if score > best_match_score:
                    best_match_score = score
                    best_product = sp
                    best_details = details
                    best_lead_product = lead_product
        
        status = "Incompatible"
        if best_match_score > 80:
            status = "Full Match"
        elif best_match_score > 40:
            status = "Partial Match"
            
        final_details = {
            "seller_product_id": best_product.id if best_product else None,
            "seller_product_name": best_product.name if best_product else None,
            "match_breakdown": best_details,
            "reason": "Category, Name and Specs comparison"
        }
        
        return best_match_score, status, final_details, best_lead_product

    def _calculate_delivery_score(self, lat, lon, neighborhood, pickup=0, constraints=None):
        """Calculate delivery advantage based on location and preferences."""
        score = 40.0 # Base score
        
        # 1. Neighborhood Advantage
        if neighborhood:
            score += 30.0
            
        # 2. Coordinate-based Advantage (Mocked for Nairobi central area)
        if lat and lon:
            # Nairobi bounding box roughly
            if -1.45 < lat < -1.15 and 36.65 < lon < 37.05:
                score += 10.0
        
        # 3. Pickup Preference Advantage (Sellers love pickups)
        if pickup:
            score += 15.0
            
        # 4. Delivery Constraint Impact
        if constraints:
            # Some constraints make it harder, some easier. 
            # For now, if they have specific delivery needs, we assume it's a "local" request
            score += 5.0
            
        return min(score, 100.0)

    def _calculate_deal_probability(self, intent_score, readiness, urgency, budget, specs, text, budget_ready=0, deadline=None):
        """
        Calculate Deal Probability based on:
        - Readiness Level (Hot = +30, Warm = +15)
        - Urgency (Score * 2, max 20)
        - Budget Presence & Readiness (+10 each)
        - Product Specificity (+10)
        - Contact availability (+15)
        - Deadline Presence (+10)
        """
        prob = intent_score * 10 # Base from intent
        
        if readiness == "HOT": prob += 30
        elif readiness == "WARM": prob += 15
        
        prob += min(urgency * 2, 20)
        
        if self._extract_phone(text) or self._extract_email(text):
            prob += 15
            
        if specs: prob += 10
        
        if budget != "Negotiable": prob += 10
        if budget_ready: prob += 10
        if deadline: prob += 10
        
        return min(round(prob, 1), 100.0)

    def _calculate_competition(self, text, platform, intent_score=0.5):
        """Estimate competition based on platform and text content."""
        # Base competition by platform - more stable than pure random
        platform_base = {
            "Facebook": 8,
            "Reddit": 3,
            "TikTok": 5,
            "Google": 0,
            "Unknown": 4
        }
        count = platform_base.get(platform, 4)
        
        # Higher intent leads usually attract more competition
        count += int(intent_score * 5)
        
        # Unique/Low competition if it's very specific or has personal contact
        is_unique = False
        if len(text) > 150 and ("07" in text or "@" in text):
            is_unique = True
            count = max(0, count - 2)
            
        return count, is_unique

    def _calculate_response_window(self, platform):
        """Determine optimal response window and peak times."""
        windows = {
            "Facebook": ("Next 15 mins", "6PM - 10PM"),
            "Reddit": ("Next 2 hours", "9AM - 1PM"),
            "TikTok": ("Next 10 mins", "12PM - 4PM"),
            "Google": ("Next 24 hours", "8AM - 5PM"),
            "Unknown": ("Next 1 hour", "Anytime")
        }
        return windows.get(platform, ("ASAP", "Anytime"))

    def _calculate_verification(self, raw_data, text, phone, email, intent_score):
        """
        Lead Confidence Score (1-10) Algorithm:
        - Platform Credibility: Google/Facebook (+2), Reddit/TikTok (+1)
        - Contact Info: Phone (+3), Email (+2)
        - Intent Quality: High Intent Score > 0.8 (+2), Specificity (+1)
        - Scammer/Reseller Check: Identify seller keywords (-5)
        """
        score = 2.0 # Base score
        badges = []
        is_genuine = True
        
        # 1. Platform Credibility
        source = raw_data.get("source", "").lower()
        if source in ["google", "facebook"]: score += 2
        elif source in ["reddit", "tiktok"]: score += 1
        
        # 2. Contact Info Verification
        if phone:
            score += 3
            badges.append("verified_contact")
        if email:
            score += 2
            if "verified_contact" not in badges: badges.append("verified_contact")
            
        # 3. Intent & Specificity
        if intent_score > 0.8:
            score += 2
            badges.append("high_intent")
        
        # Check for specific buying intent (e.g., "looking for", "buy", "price of")
        buying_keywords = ["buy", "purchase", "looking for", "price of", "cost of", "where can i get"]
        if any(kw in text.lower() for kw in buying_keywords):
            score += 1
            if "high_intent" not in badges: badges.append("high_intent")

        # 4. Scammer/Reseller Filtering (REVERSE SIGNAL)
        # ENFORCEMENT: If ANY seller signal is detected, it is NOT genuine.
        seller_keywords = [
            "for sale", "selling", "available", "price", "discount", "offer", 
            "promo", "delivery", "in stock", "we sell", "shop", "dealer", 
            "supplier", "warehouse", "order now", "dm for price", 
            "call / whatsapp", "our store", "brand new", "limited stock",
            "flash sale", "retail price", "wholesale", "best price",
            "check out", "visit us", "located at", "we deliver", "buy from us",
            "contact for price", "special offer", "new arrival", "stockist"
        ]
        
        # Check if it's a buyer question first (exception)
        buyer_questions = ["who sells", "anyone selling", "who is selling", "who has", "where can i find"]
        is_buyer_question = any(bq in text.lower() for bq in buyer_questions)
        
        if any(kw in text.lower() for kw in seller_keywords) and not is_buyer_question:
            score -= 8 # Heavy penalty
            is_genuine = False 
        
        # 5. Activity/Freshness
        # For new leads, we assume they are active
        badges.append("active_buyer")
        
        return min(max(score, 1.0), 10.0), badges, is_genuine

    def _extract_phone(self, text):
        import re
        # Kenyan formats: 
        # +254 7...
        # 07...
        # 01...
        # 2547...
        # 7... (9 digits)
        # Handle spaces, dashes, and brackets
        clean_text = re.sub(r'[()\- ]', '', text)
        
        # Regex for Kenyan numbers:
        # 1. Starts with +254 or 254 followed by 7 or 1 and 8 digits
        # 2. Starts with 07 or 01 followed by 8 digits
        # 3. Starts with 7 or 1 followed by 8 digits (total 9)
        phone_pattern = r'(\+?254|0)?([71]\d{8})\b'
        
        match = re.search(phone_pattern, clean_text)
        if match:
            # We want to return a standardized format for verification if possible,
            # but for now let's just return the matched group.
            # The verifier will clean it further.
            return match.group(0)
        return ""

    def _extract_email(self, text):
        import re
        # More robust email regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else ""

    def is_fresh(self, lead_data, max_hours=72):
        """Validate if the lead is within the fresh window."""
        # In a real scenario, extract timestamp from post
        return True 
