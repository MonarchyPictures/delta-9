import os
import hmac
import hashlib
from fastapi import HTTPException, Request, Header
from app.config import ADMIN_SECRET_KEY

def require_admin(request: Request, x_role: str = Header(None), x_admin_signature: str = Header(None)):
    """
    🔐 Render-ready PROD hardening: Role-based access control with Signed Headers.
    To prevent header spoofing in production, admin overrides require a valid HMAC signature.
    """
    if x_role != "user":
        raise HTTPException(status_code=403, detail="Access denied: Required role 'user' not found.")
    
    # In production, require a signed header for any action that bypasses user limits
    if os.getenv("DELTA9_ENV") == "prod":
        if not x_admin_signature:
            raise HTTPException(status_code=401, detail="Production Security: Missing admin signature.")
        
        # Verify signature: HMAC-SHA256(key=ADMIN_SECRET_KEY, msg=x_role)
        expected_signature = hmac.new(
            ADMIN_SECRET_KEY.encode(),
            x_role.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(x_admin_signature, expected_signature):
            raise HTTPException(status_code=401, detail="Production Security: Invalid admin signature.")
            
    return x_role
