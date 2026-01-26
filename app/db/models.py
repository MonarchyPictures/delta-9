from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Enum, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class ContactStatus(enum.Enum):
    NOT_CONTACTED = "not_contacted"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    REJECTED = "rejected"

class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, index=True)
    source_platform = Column(String, index=True)
    post_link = Column(String, unique=True)
    timestamp = Column(DateTime, server_default=func.now())
    
    # Geolocation
    location_raw = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    radius_km = Column(Float, default=0.0)
    
    # Intent Data
    buyer_request_snippet = Column(String)
    product_category = Column(String, index=True)
    buyer_name = Column(String)
    intent_score = Column(Float)
    confidence_score = Column(Float, default=0.0)
    
    # Hyper-Specific Intent Intelligence
    readiness_level = Column(String, index=True) # HOT, WARM, RESEARCHING
    urgency_score = Column(Float, default=0.0) # 0-10
    budget_info = Column(String) # e.g. "Ksh 50,000", "Negotiable"
    product_specs = Column(JSON) # Extracted details (size, model, color)
    deal_probability = Column(Float, default=0.0) # 0-100
    
    # NEW: Smart Matching & Compatibility
    match_score = Column(Float, default=0.0) # 0-100%
    compatibility_status = Column(String) # "Full Match", "Partial Match", "Incompatible"
    match_details = Column(JSON) # Detailed breakdown of why it matches
    
    # NEW: Intent Analysis Extensions
    quantity_requirement = Column(String) # e.g. "10 units", "Bulk"
    payment_method_preference = Column(String) # e.g. "M-Pesa", "Installments"
    
    # NEW: Local Advantage
    delivery_range_score = Column(Float, default=0.0) # 0-100
    neighborhood = Column(String) # Specific area/estate
    local_pickup_preference = Column(Integer, default=0) # 1 if mentions pickup
    delivery_constraints = Column(String) # e.g. "Must deliver before 5PM"
    
    # NEW: Deal Readiness Assessment
    decision_authority = Column(Integer, default=0) # 1 if mentions "I am buying", "My company"
    prior_research_indicator = Column(Integer, default=0) # 1 if compares models/prices
    comparison_indicator = Column(Integer, default=0) # 1 if mentions competitors
    upcoming_deadline = Column(DateTime) # Extracted deadline if any
    
    # Real-Time & Competitive Intelligence
    availability_status = Column(String, default="Available Now") # Available Now, Recently Contacted, Likely Closed
    competition_count = Column(Integer, default=0)
    is_unique_request = Column(Integer, default=0) # 1 if low competition/unique
    optimal_response_window = Column(String) # e.g. "Next 30 mins", "ASAP"
    peak_response_time = Column(String) # e.g. "9AM-11AM"
    
    # Contact Verification & Reliability
    is_contact_verified = Column(Integer, default=0) # 1 if verified
    contact_reliability_score = Column(Float, default=0.0) # 0-100
    preferred_contact_method = Column(String) # "WhatsApp", "Phone", "Email", "Social"
    disposable_email_flag = Column(Integer, default=0)
    contact_metadata = Column(JSON) # Carrier, domain status, etc.
    
    # Response Tracking System
    response_count = Column(Integer, default=0)
    average_response_time_mins = Column(Float)
    last_contact_attempt = Column(DateTime)
    last_response_received = Column(DateTime)
    conversion_rate = Column(Float, default=0.0)
    non_response_flag = Column(Integer, default=0) # 1 if lead has history of non-response
    
    # Verification & Badges
    verification_badges = Column(JSON) # ["verified_contact", "active_buyer", "high_intent"]
    account_age_days = Column(Integer)
    is_genuine_buyer = Column(Integer, default=1) # 0 if suspected reseller/scammer
    last_activity = Column(DateTime)
    
    # NEW: Comprehensive Lead Intelligence
    # 1. Lead Profile
    buyer_history = Column(JSON) # e.g. {"purchase_count": 2, "avg_decision_days": 3}
    platform_activity_level = Column(String) # "High", "Medium", "Low"
    past_response_rate = Column(Float) # 0-100%
    
    # 2. Market Context
    market_price_range = Column(String) # e.g. "Ksh 40k - 55k"
    seasonal_demand = Column(String) # "Peak", "Normal", "Off-season"
    supply_status = Column(String) # "Shortage", "Stable", "Oversupply"
    
    # 3. Conversion Signals
    conversion_signals = Column(JSON) # ["budget_approved", "financing_mentioned", "deadline_fixed"]
    talking_points = Column(JSON) # Suggested opening lines
    
    # 4. Seller Match Analysis
    competitive_advantages = Column(JSON) # ["Fastest Delivery", "Best Price", "Verified Seller"]
    pricing_strategy = Column(String) # "Premium", "Competitive", "Aggressive"
    
    # Contact Info
    contact_phone = Column(String)
    contact_email = Column(String)
    social_links = Column(JSON)
    
    # Metadata
    status = Column(Enum(ContactStatus), default=ContactStatus.NOT_CONTACTED)
    is_saved = Column(Integer, default=0) # 1 if saved for follow-up
    notes = Column(String)
    personalized_message = Column(String)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class SearchPattern(Base):
    __tablename__ = "search_patterns"
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String, unique=True)
    category = Column(String)
    is_active = Column(Integer, default=1)

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    query = Column(String)
    location = Column(String, default="Kenya")
    is_active = Column(Integer, default=1)
    enable_alerts = Column(Integer, default=1) # New: enable real-time alerts
    last_run = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    lead_id = Column(String, ForeignKey("leads.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    message = Column(String)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True)
    value = Column(JSON)
    updated_at = Column(DateTime, onupdate=func.now())

class SellerProduct(Base):
    __tablename__ = "seller_products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    category = Column(String)
    specs = Column(JSON) # e.g. {"capacity": "50000L", "material": "Plastic"}
    price = Column(Float)
    location = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
