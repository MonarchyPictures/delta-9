from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks, Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import os
import logging

from app.db import models
from app.db.database import get_db, SessionLocal
from app.ingestion import LiveLeadIngestor
from app.config import PIPELINE_MODE

router = APIRouter(tags=["Admin"])

# API Key verification
API_KEY = os.getenv("API_KEY", "d9_prod_secret_key_2024")

def verify_api_key(request: Request, x_api_key: str = Header(None)):
    if request.method == "OPTIONS":
        return
    if not x_api_key or x_api_key != API_KEY:
        # Soft flagging instead of hard rejection
        print(f"WARNING: Invalid API Key: {x_api_key}")
        # raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# Agent routes moved to app/api/routes/agents.py

@router.get("/settings", dependencies=[Depends(verify_api_key)])
def get_settings():
    """Return platform settings."""
    return {
        "notifications_enabled": True,
        "sound_enabled": True,
        "region": "Kenya",
        "currency": "KES",
        "geo_lock": "Kenya",
        "mode": "PROD_STRICT"
    }

# Notification routes moved to app/api/routes/notifications.py
