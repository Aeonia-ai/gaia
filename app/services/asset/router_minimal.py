from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import time
from datetime import datetime

from .models.asset import AssetRequest, AssetCategory
from app.shared.security import get_current_auth_legacy
from app.shared.logging import get_logger
from .generation_service import AIGenerationService

logger = get_logger(__name__)
assets_router = APIRouter(prefix="/assets", tags=["Assets"])

# Initialize generation service
generation_service = AIGenerationService()


@assets_router.get("/")
async def list_assets(
    current_auth = Depends(get_current_auth_legacy)
):
    """List assets - placeholder implementation"""
    return {
        "assets": [],
        "total": 0,
        "message": "Asset listing functionality - implementation in progress",
        "timestamp": datetime.utcnow().isoformat()
    }

@assets_router.get("/test")
async def test_endpoint():
    """Test endpoint to verify service is running"""
    return {
        "status": "ok",
        "service": "asset-service",
        "message": "Asset service is running",
        "timestamp": datetime.utcnow().isoformat()
    }


@assets_router.post("/request")
async def request_asset(
    request: AssetRequest,
    current_auth = Depends(get_current_auth_legacy)
):
    """
    Main asset request endpoint - Full generation pipeline
    Compatible with LLM Platform API format
    """
    start_time = time.time()
    
    try:
        logger.info(f"Asset request received: {request.category.value} - {request.style} - {request.description[:100]}...")
        
        # Generate asset using the full pipeline
        response = await generation_service.generate_asset(request)
        
        logger.info(f"Asset generation completed in {response.response_time_ms}ms for ${response.cost:.4f}")
        
        return response
        
    except Exception as e:
        logger.error(f"Asset request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Asset request failed: {str(e)}")


@assets_router.get("/health")
async def asset_server_health():
    """Asset server health check"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "pending",  # TODO: Actual health check
                "nats": "pending",     # TODO: Actual health check
                "storage": "pending",   # TODO: Actual health check
                "external_apis": "pending"  # TODO: Actual health check
            }
        }
        
    except Exception as e:
        logger.error(f"Asset server health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }