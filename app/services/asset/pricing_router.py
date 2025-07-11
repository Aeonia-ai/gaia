from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.assets import PricingService
from app.core.security import get_current_auth
from app.core import logger

pricing_router = APIRouter(prefix="/pricing", tags=["Asset Pricing"])


@pricing_router.get("/current")
async def get_current_pricing(
    provider: str,
    category: str,
    quality: str = "standard",
    current_auth = Depends(get_current_auth)
):
    """
    Get current pricing for a specific provider and asset category.
    
    Example: /api/v1/assets/pricing/current?provider=OpenAI&category=image&quality=hd
    """
    try:
        pricing_service = PricingService()
        
        cost = await pricing_service.get_generation_cost(
            provider=provider,
            category=category,
            quality=quality
        )
        
        return {
            "provider": provider,
            "category": category,
            "quality": quality,
            "cost_per_unit": cost,
            "currency": "USD",
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get pricing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pricing: {str(e)}")


@pricing_router.get("/analytics")
async def get_cost_analytics(
    days: int = 30,
    current_auth = Depends(get_current_auth)
):
    """
    Get cost analytics for the specified period.
    
    Returns total costs, costs by provider, and usage statistics.
    """
    try:
        pricing_service = PricingService()
        analytics = await pricing_service.get_cost_analytics(days)
        
        return {
            "period_days": days,
            "analytics": analytics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get cost analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@pricing_router.post("/update")
async def update_pricing(
    provider: str,
    current_auth = Depends(get_current_auth)
):
    """
    Trigger a pricing update for a specific provider.
    
    This would typically be called by a scheduled job or admin interface.
    """
    try:
        pricing_service = PricingService()
        await pricing_service.update_pricing_from_provider(provider)
        
        return {
            "status": "success",
            "message": f"Pricing update triggered for {provider}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update pricing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update pricing: {str(e)}")


@pricing_router.get("/providers")
async def list_pricing_providers(
    current_auth = Depends(get_current_auth)
):
    """
    List all available pricing providers and their supported categories.
    """
    # This would query the api_providers table
    providers = [
        {
            "name": "OpenAI",
            "type": "image_generation",
            "categories": ["image", "texture"],
            "pricing_tiers": ["standard", "hd"]
        },
        {
            "name": "Stability AI",
            "type": "image_generation", 
            "categories": ["image"],
            "pricing_tiers": ["standard"]
        },
        {
            "name": "ElevenLabs",
            "type": "audio_generation",
            "categories": ["audio"],
            "pricing_tiers": ["standard", "premium"]
        },
        {
            "name": "Meshy AI",
            "type": "3d_generation",
            "categories": ["prop", "character", "environment"],
            "pricing_tiers": ["standard", "pro"]
        }
    ]
    
    return {
        "providers": providers,
        "total_count": len(providers)
    }