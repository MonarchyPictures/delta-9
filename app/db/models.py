from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Enum, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
import hashlib
from app.db.base_class import Base

class ContactStatus(enum.Enum):
    NOT_CONTACTED = "not_contacted"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    REJECTED = "rejected"

class CRMStatus(enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    REPLIED = "REPLIED"
    NEGOTIATING = "NEGOTIATING"
    CONVERTED = "CONVERTED"
    DEAD = "DEAD"

class Lead(Base):
    __tablename__ = "leads"
    
    # Lead Identification & Metadata
    id = Column(String, primary_key=True, index=True) # Maps to lead_id
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True, index=True)
    query = Column(String, nullable=True)
    location = Column(String, nullable=True)
    buyer_name = Column(String, index=True)
    contact_phone = Column(String, index=True) # Maps to phone
    contact_email = Column(String, index=True) # NEW: Email support
    product_category = Column(String, index=True) # Maps to product
    quantity_requirement = Column(String) # Maps to quantity
    intent_score = Column(Float, index=True) # Maps to intent_strength
    location_raw = Column(String) # Maps to location
    radius_km = Column(Float, default=0.0) # Maps to distance_km
    source_platform = Column(String, index=True) # Maps to source
    request_timestamp = Column(DateTime, index=True) # Maps to timestamp
    
    # NEW: WhatsApp Integration
    whatsapp_link = Column(String)
    contact_method = Column(String) # NEW: Explicit contact method from scraper
    
    # NEW: Status & Proof of Life (PROD STRICT)
    status = Column(Enum(CRMStatus), default=CRMStatus.NEW, index=True)
    source_url = Column(String)
    http_status = Column(Integer)
    latency_ms = Column(Integer)
    
    # Standardized Buyer Fields
    is_hot_lead = Column(Integer, default=0, index=True)
    buyer_request_snippet = Column(String)
    urgency_level = Column(String, default="low", index=True) # NEW: High/Medium/Low
    confidence_score = Column(Float, default=0.0, index=True)
    price = Column(Float, nullable=True) # Extracted price if available
    is_saved = Column(Integer, default=0)
    is_verified_signal = Column(Integer, default=1, index=True) # PROD_STRICT: Signal verification flag
    notes = Column(String)
    contact_source = Column(String) # public | inferred | unavailable
    budget = Column(String) # e.g. "1.1M" or "800k"
    buyer_match_score = Column(Float, default=0.0)
    contact_status = Column(String, default="verified") # verified | needs_outreach
    property_country = Column(String, default="Kenya")
    geo_score = Column(Float, default=0.0) # NEW: 0.0 -> 1.0 geographic relevance
    geo_strength = Column(String, default="low") # NEW: high | medium | low
    geo_region = Column(String, default="Global") # NEW: Nairobi | Mombasa | etc
    
    # 🎯 RANKING ENGINE (Runs After Save)
    ranked_score = Column(Float, default=0.0, index=True) # Unified priority score
    rank_score = Column(Float, default=0.0, index=True) # Intelligent Ranking Engine Score
    
    # Response Tracking
    response_count = Column(Integer, default=0)
    non_response_flag = Column(Integer, default=0)
    
    # Hyper-Specific Intent Intelligence
    readiness_level = Column(String)
    urgency_score = Column(Float)
    budget_info = Column(String)
    product_specs = Column(JSON)
    deal_probability = Column(Float)
    intent_type = Column(String)
    
    # Smart Matching
    match_score = Column(Float, default=0.0)
    compatibility_status = Column(String)
    match_details = Column(JSON)
    
    # Intent Analysis Extensions
    payment_method_preference = Column(String)
    
    # Local Advantage
    delivery_range_score = Column(Float, default=0.0)
    neighborhood = Column(String)
    local_pickup_preference = Column(Integer, default=0)
    delivery_constraints = Column(String)
    
    # Deal Readiness
    decision_authority = Column(Integer, default=0)
    prior_research_indicator = Column(Integer, default=0)
    comparison_indicator = Column(Integer, default=0)
    upcoming_deadline = Column(DateTime)
    
    # Real-Time & Competitive Intelligence
    availability_status = Column(String)
    competition_count = Column(Integer)
    is_unique_request = Column(Integer)
    optimal_response_window = Column(String)
    peak_response_time = Column(String)
    
    # Contact Verification & Reliability
    is_contact_verified = Column(Integer, default=0)
    contact_reliability_score = Column(Float, default=0.0)
    preferred_contact_method = Column(String)
    disposable_email_flag = Column(Integer, default=0)
    contact_metadata = Column(JSON)
    
    # Response Tracking System (Extended)
    average_response_time_mins = Column(Float)
    conversion_rate = Column(Float, default=0.0)
    
    # Comprehensive Lead Intelligence
    buyer_history = Column(JSON)
    platform_activity_level = Column(String)
    past_response_rate = Column(Float, default=0.0)
    market_price_range = Column(String)
    seasonal_demand = Column(String)
    supply_status = Column(String)
    conversion_signals = Column(JSON)
    talking_points = Column(JSON)
    competitive_advantages = Column(JSON)
    pricing_strategy = Column(String)
    
    verification_badges = Column(JSON)
    is_genuine_buyer = Column(Integer, default=1)
    last_activity = Column(DateTime)

    tap_count = Column(Integer, default=0) # Track clicks for schema compliance
    
    # Deduplication
    content_hash = Column(String, index=True) # Hash of core content

    __table_args__ = (
        UniqueConstraint("agent_id", "source_url", name="uix_agent_url"),
        {'extend_existing': True}
    )

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, onupdate=func.now())

    @property
    def title(self):
        return self.buyer_name

    @property
    def content(self):
        return self.buyer_request_snippet

    @property
    def source(self):
        return self.source_platform

    @property
    def url(self):
        return self.source_url

    @property
    def confidence(self):
        return self.confidence_score

    def __init__(self, **kwargs):
        # Map user-friendly aliases to DB columns
        if 'title' in kwargs:
            self.buyer_name = kwargs.pop('title')
        if 'content' in kwargs:
            self.buyer_request_snippet = kwargs.pop('content')
        if 'source' in kwargs:
            self.source_platform = kwargs.pop('source')
        if 'url' in kwargs:
            self.source_url = kwargs.pop('url')
        if 'confidence' in kwargs:
            self.confidence_score = kwargs.pop('confidence')
            
        # Set remaining kwargs as attributes
        for k, v in kwargs.items():
            setattr(self, k, v)
            
        # Ensure ID is generated if not provided
        if not getattr(self, 'id', None):
             self.id = str(uuid.uuid4())

    def to_dict(self):
        from ..intelligence.outreach import OutreachEngine
        from ..utils.outreach import whatsapp_link
        outreach_engine = OutreachEngine()
        
        msg = outreach_engine.generate_message(self)
        phone = self.contact_phone or self.whatsapp_link
        
        # Mandatory Schema (User Requirement)
        return {
            "id": self.id,
            "query": self.product_category,
            "location": self.location_raw,
            "source": self.source_platform,
            "intent_strength": self.intent_score,
            "intent_label": self.urgency_level or "medium",
            "confidence": self.confidence_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "whatsapp_url": whatsapp_link(phone, msg) if phone else self.whatsapp_link,
            "tap_count": self.tap_count or 0,
            
            # Legacy/Internal fields for frontend components
            "lead_id": self.id,
            "buyer_name": self.buyer_name,
            "product": self.product_category,
            "phone": self.contact_phone,
            "whatsapp_link": self.whatsapp_link,
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "source_url": self.source_url,
            "buyer_intent_quote": self.buyer_request_snippet,
            "outreach_suggestion": msg,
            "is_hot_lead": bool(self.is_hot_lead),
            "buyer_match_score": self.buyer_match_score or 0.0,
            "geo_score": self.geo_score or 0.0,
            "geo_strength": self.geo_strength or "low",
            "geo_region": self.geo_region or "Global",
            "ranked_score": self.ranked_score or 0.0
        }

class BuyerLead(Base):
    """
    🎯 BUYERS TABLE (MINIMAL) - Standardized schema for buyer-only ingestion.
    """
    __tablename__ = "buyer_leads"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    platform = Column(String)
    intent = Column(String)
    location = Column(String)
    contact = Column(String)
    contact_status = Column(String)
    confidence = Column(Float) # SQL REAL maps to Float in SQLAlchemy
    posted_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

class AgentRunLog(Base):
    __tablename__ = "agent_run_logs"

    id = Column(Integer, primary_key=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    run_time = Column(DateTime, default=func.now())
    leads_found = Column(Integer, default=0)
    errors = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0)

    agent = relationship("Agent", backref="run_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "intent": self.intent,
            "location": self.location,
            "contact": self.contact,
            "contact_status": self.contact_status,
            "confidence": self.confidence,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }



class BuyerIntent(Base):
    __tablename__ = "buyer_intents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True) # The agent or user who has this intent
    interest_type = Column(String, index=True) # Flexible: "Toyota", "iPhone", "Apartment"
    vehicle_type = Column(String, index=True) # DEPRECATED: use interest_type
    budget_min = Column(Float, default=0.0)
    budget_max = Column(Float)
    location = Column(String, index=True)
    urgency = Column(String, default="medium") # high, medium, low
    
    # Metadata
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "interest_type": self.interest_type or self.vehicle_type,
            "vehicle_type": self.vehicle_type, # Legacy support
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "location": self.location,
            "urgency": self.urgency,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class SearchPattern(Base):
    __tablename__ = "search_patterns"
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String, unique=True)
    category = Column(String)
    is_active = Column(Integer, default=1)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String, index=True) # WHATSAPP_TAP, LEAD_DISCOVERED, SEARCH_PERFORMED
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    session_id = Column(String, index=True, nullable=True) # To group user behavior
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    extra_metadata = Column(JSON, nullable=True) # For additional info like product name, etc.

# Import Agent from new location but allow it to be accessed via models.Agent
from app.models.agent import Agent
from app.models.agent_raw_lead import AgentRawLead
from app.models.notification import Notification

class AgentLead(Base):
    __tablename__ = "agent_leads"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"))
    lead_id = Column(String, ForeignKey("leads.id"))
    discovered_at = Column(DateTime, server_default=func.now())

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True)
    value = Column(JSON)
    updated_at = Column(DateTime, onupdate=func.now())

class ScraperMetric(Base):
    __tablename__ = "scraper_metrics"
    
    id = Column(Integer, primary_key=True)
    scraper_name = Column(String, unique=True, index=True)
    runs = Column(Integer, default=0)
    leads_found = Column(Integer, default=0)
    verified_leads = Column(Integer, default=0)
    failures = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)
    avg_latency = Column(Float, default=0.0) # Average runtime in seconds
    avg_confidence = Column(Float, default=0.0) # Average intent score of leads
    avg_freshness = Column(Float, default=0.0) # NEW: Average age of signals in minutes
    avg_geo_score = Column(Float, default=0.0) # NEW: Average geographic relevance of leads
    priority_score = Column(Float, default=0.0) # Unified ranking score
    priority_boost = Column(Float, default=1.0) # Priority multiplier
    auto_disabled = Column(Integer, default=0) # 0 = active, 1 = disabled
    last_success = Column(DateTime)
    history = Column(JSON) # List of last 20 runs
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class CategoryMetric(Base):
    __tablename__ = "category_metrics"
    
    id = Column(Integer, primary_key=True)
    category_name = Column(String, unique=True, index=True)
    total_leads = Column(Integer, default=0)
    verified_leads = Column(Integer, default=0)
    verified_rate = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String, index=True, nullable=True)
    scraper_name = Column(String, index=True, nullable=True)
    error_type = Column(String, index=True) # TIMEOUT, CRASH, NETWORK
    error_message = Column(Text)
    stack_trace = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())