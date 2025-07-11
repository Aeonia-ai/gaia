from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.services.assets.advanced_pricing_service import AdvancedPricingService, UsageMetrics
from app.models.assets import AssetCategory
from app.core.security import get_current_auth
from app.core import logger

cost_estimator_router = APIRouter(prefix="/cost-estimator", tags=["Cost Estimation"])


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""
    provider: str
    asset_category: AssetCategory
    estimated_usage: Dict[str, Any]  # Flexible usage metrics
    user_context: Optional[Dict[str, Any]] = None


class CostEstimateResponse(BaseModel):
    """Detailed cost estimate response."""
    provider: str
    operation: str
    estimated_cost: float
    cost_breakdown: Dict[str, Any]
    usage_factors: Dict[str, Any]
    tier_info: Optional[Dict[str, Any]] = None
    cost_optimization_tips: Optional[Dict[str, Any]] = None


@cost_estimator_router.post("/estimate", response_model=CostEstimateResponse)
async def estimate_generation_cost(
    request: CostEstimateRequest,
    current_auth = Depends(get_current_auth)
):
    """
    Estimate cost for asset generation before making the request.
    
    Supports all pricing models:
    - DALL-E: Tier-based + per-image
    - Meshy: Credit-based  
    - Token-based: GPT, Claude, etc.
    """
    try:
        pricing_service = AdvancedPricingService()
        
        # Convert request to UsageMetrics
        usage = UsageMetrics(
            image_count=request.estimated_usage.get("image_count", 1),
            input_tokens=request.estimated_usage.get("input_tokens", 0),
            output_tokens=request.estimated_usage.get("output_tokens", 0),
            character_count=request.estimated_usage.get("character_count", 0),
            credits_consumed=request.estimated_usage.get("credits_consumed", 0),
            compute_seconds=request.estimated_usage.get("compute_seconds", 0.0),
            requests_per_minute=request.estimated_usage.get("requests_per_minute", 1)
        )
        
        # Get cost prediction
        cost_calc = await pricing_service.get_cost_prediction(
            provider=request.provider,
            asset_category=request.asset_category,
            estimated_usage=usage,
            user_context=request.user_context
        )
        
        # Generate optimization tips
        optimization_tips = _generate_optimization_tips(request.provider, cost_calc)
        
        return CostEstimateResponse(
            provider=request.provider,
            operation=f"{request.asset_category.value}_generation",
            estimated_cost=cost_calc.total_cost,
            cost_breakdown={
                "base_cost": cost_calc.base_cost,
                "tier_fee": cost_calc.tier_fee,
                "ancillary_costs": cost_calc.ancillary_costs,
                "total_cost": cost_calc.total_cost
            },
            usage_factors=cost_calc.cost_factors or {},
            cost_optimization_tips=optimization_tips
        )
        
    except Exception as e:
        logger.error(f"Cost estimation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cost estimation failed: {str(e)}")


@cost_estimator_router.get("/dalle-tiers")
async def get_dalle_tier_info(
    current_auth = Depends(get_current_auth)
):
    """
    Get DALL-E tier information and pricing.
    
    Shows tiered rate limits and monthly fees.
    """
    try:
        pricing_service = AdvancedPricingService()
        
        tiers = []
        for tier in pricing_service.dalle_tiers:
            tiers.append({
                "tier_name": tier.tier_name,
                "monthly_fee": tier.monthly_fee,
                "max_requests_per_minute": tier.max_requests_per_minute,
                "max_monthly_usage": tier.max_monthly_usage,
                "recommended_for": _get_tier_recommendation(tier)
            })
        
        return {
            "dalle_tiers": tiers,
            "per_image_rates": {
                "standard_1024x1024": 0.040,
                "hd_1024x1024": 0.080,
                "standard_1792x1024": 0.080,
                "hd_1792x1024": 0.120
            },
            "billing_formula": "total_cost = (image_count × per_image_rate) + tier_fee",
            "tier_upgrade_info": "Tiers automatically upgrade when rate limits exceeded"
        }
        
    except Exception as e:
        logger.error(f"Failed to get DALL-E tier info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@cost_estimator_router.get("/meshy-packages")
async def get_meshy_package_info(
    current_auth = Depends(get_current_auth)
):
    """
    Get Meshy credit packages and operation costs.
    
    Shows credit-based pricing structure.
    """
    try:
        pricing_service = AdvancedPricingService()
        
        packages = []
        for name, info in pricing_service.meshy_packages.items():
            cost_per_credit = info["cost"] / info["credits"]
            packages.append({
                "package_name": name,
                "total_cost": info["cost"],
                "credits_included": info["credits"],
                "cost_per_credit": cost_per_credit,
                "recommended_for": _get_package_recommendation(name)
            })
        
        return {
            "credit_packages": packages,
            "operation_costs": pricing_service.meshy_operations,
            "billing_formula": "total_cost = (operation_credits × credit_cost)",
            "cost_examples": {
                "text_to_3d": f"5 credits × ${packages[1]['cost_per_credit']:.3f} = ${5 * packages[1]['cost_per_credit']:.3f}",
                "text_to_3d_with_texture": f"15 credits × ${packages[1]['cost_per_credit']:.3f} = ${15 * packages[1]['cost_per_credit']:.3f}"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get Meshy package info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@cost_estimator_router.get("/provider-comparison")
async def compare_provider_costs(
    asset_category: AssetCategory,
    quality: str = "standard",
    quantity: int = 1,
    current_auth = Depends(get_current_auth)
):
    """
    Compare costs across different providers for the same asset type.
    
    Helps optimize provider selection for cost efficiency.
    """
    try:
        pricing_service = AdvancedPricingService()
        
        providers = []
        if asset_category == AssetCategory.IMAGE:
            providers = ["OpenAI", "Stability AI"]
        elif asset_category in [AssetCategory.PROP, AssetCategory.CHARACTER]:
            providers = ["Meshy"]
        elif asset_category == AssetCategory.AUDIO:
            providers = ["ElevenLabs"]
        
        comparisons = []
        for provider in providers:
            try:
                usage = UsageMetrics(image_count=quantity)
                
                cost_calc = await pricing_service.get_cost_prediction(
                    provider=provider,
                    asset_category=asset_category,
                    estimated_usage=usage,
                    user_context={"quality": quality}
                )
                
                comparisons.append({
                    "provider": provider,
                    "total_cost": cost_calc.total_cost,
                    "cost_per_unit": cost_calc.total_cost / quantity,
                    "cost_breakdown": {
                        "base_cost": cost_calc.base_cost,
                        "tier_fee": cost_calc.tier_fee,
                        "ancillary_costs": cost_calc.ancillary_costs
                    },
                    "pricing_model": cost_calc.cost_factors.get("pricing_model", "unknown") if cost_calc.cost_factors else "unknown"
                })
                
            except Exception as e:
                logger.warning(f"Failed to get cost for {provider}: {e}")
        
        # Sort by total cost
        comparisons.sort(key=lambda x: x["total_cost"])
        
        return {
            "asset_category": asset_category,
            "quality": quality,
            "quantity": quantity,
            "provider_comparison": comparisons,
            "cost_leader": comparisons[0]["provider"] if comparisons else None,
            "max_savings": comparisons[-1]["total_cost"] - comparisons[0]["total_cost"] if len(comparisons) > 1 else 0
        }
        
    except Exception as e:
        logger.error(f"Provider comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _generate_optimization_tips(provider: str, cost_calc) -> Dict[str, Any]:
    """Generate cost optimization recommendations."""
    tips = {}
    
    if provider.lower() == "openai":
        if cost_calc.tier_fee > cost_calc.base_cost:
            tips["tier_optimization"] = "Consider batching requests to maximize tier value"
        
        if cost_calc.cost_factors and cost_calc.cost_factors.get("quality") == "hd":
            tips["quality_optimization"] = "Standard quality costs 50% less than HD"
            
    elif provider.lower() == "meshy":
        if cost_calc.ancillary_costs > 0:
            tips["credit_optimization"] = "Pre-purchase larger credit packages for better rates"
    
    return tips


def _get_tier_recommendation(tier) -> str:
    """Get recommendation for DALL-E tier usage."""
    if tier.tier_name == "tier_1":
        return "Testing and low-volume usage (up to 5 images/minute)"
    elif tier.tier_name == "tier_2":  
        return "Production applications (up to 50 images/minute)"
    else:
        return "High-volume enterprise usage (up to 500 images/minute)"


def _get_package_recommendation(package_name: str) -> str:
    """Get recommendation for Meshy package usage."""
    if package_name == "starter":
        return "Testing and prototyping (200 credits)"
    elif package_name == "professional":
        return "Regular production use (1000 credits)"
    else:
        return "High-volume enterprise usage (5000 credits)"