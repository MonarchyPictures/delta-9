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

class CRMStatus(enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    REPLIED = "REPLIED"
    NEGOTIATING = "NEGOTIATING"
    CONVERTED = "CONVERTED"
    DEAD = "DEAD"

class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = {'extend_existing': True}

    # Lead Identification & Metadata
    id = Column(String, primary_key=True, index=True) # Maps to lead_id
    buyer_name = Column(String)
    contact_phone = Column(String, index=True) # Maps to phone
    product_category = Column(String, index=True) # Maps to product
    quantity_requirement = Column(String) # Maps to quantity
    intent_score = Column(Float) # Maps to intent_strength
    location_raw = Column(String) # Maps to location
    radius_km = Column(Float, default=0.0) # Maps to distance_km
    source_platform = Column(String, index=True) # Maps to source
    request_timestamp = Column(DateTime) # Maps to timestamp
    
    # NEW: WhatsApp Integration
    whatsapp_link = Column(String)
    contact_method = Column(String) # NEW: Explicit contact method from scraper
    
    # NEW: Status & Proof of Life (PROD STRICT)
    status = Column(Enum(CRMStatus), default=CRMStatus.NEW)
    source_url = Column(String)
    http_status = Column(Integer)
    latency_ms = Column(Integer)
    
    # Standardized Buyer Fields
    is_hot_lead = Column(Integer, default=0)
    buyer_request_snippet = Column(String)
    urgency_level = Column(String, default="low") # NEW: High/Medium/Low
    confidence_score = Column(Float, default=0.0)
    price = Column(Float, nullable=True) # Extracted price if available
    is_saved = Column(Integer, default=0)
    is_verified_signal = Column(Integer, default=1) # PROD_STRICT: Signal verification flag
    notes = Column(String)
    contact_source = Column(String) # public | inferred | unavailable
    budget = Column(String) # e.g. "1.1M" or "800k"
    buyer_match_score = Column(Float, default=0.0)
    contact_status = Column(String, default="verified") # verified | needs_outreach
    property_country = Column(String, default="Kenya")
    geo_score = Column(Float, default=0.0) # NEW: 0.0 -> 1.0 geographic relevance
    geo_strength = Column(String, default="low") # NEW: high | medium | low
    geo_region = Column(String, default="Global") # NEW: Nairobi | Mombasa | etc
    tap_count = Column(Integer, default=0) # Track clicks for schema compliance
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, onupdate=func.now())

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
            "geo_region": self.geo_region or "Global"
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

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, index=True, nullable=True) # RECIPIENT EMAIL
    query = Column(String)
    location = Column(String, default="Kenya")
    radius = Column(Integer, default=50) # Discovery radius in km
    min_intent_score = Column(Float, default=0.7) # Minimum intent score to accept
    
    # Scheduling fields
    interval_hours = Column(Integer, default=2) # e.g. every 2 hours
    duration_days = Column(Integer, default=7) # e.g. for 7 days
    next_run_at = Column(DateTime)
    
    is_active = Column(Integer, default=1)
    enable_alerts = Column(Integer, default=1) # New: enable real-time alerts
    last_run = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "query": self.query,
            "location": self.location,
            "interval_hours": self.interval_hours,
            "duration_days": self.duration_days,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "is_active": bool(self.is_active),
            "enable_alerts": bool(self.enable_alerts),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class AgentLead(Base):
    __tablename__ = "agent_leads"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    lead_id = Column(String, ForeignKey("leads.id"))
    discovered_at = Column(DateTime, server_default=func.now())

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