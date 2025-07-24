"""
v0.2 API Router for KB Service

Provides backward compatibility with v0.2 API patterns.
"""

from fastapi import APIRouter, Depends
from app.shared.security import get_current_auth_legacy as get_current_auth

router = APIRouter()

@router.get("/kb/status")
async def kb_status(auth: dict = Depends(get_current_auth)):
    """Get KB service status"""
    return {
        "service": "kb",
        "status": "healthy",
        "version": "0.2",
        "kb_enabled": True
    }