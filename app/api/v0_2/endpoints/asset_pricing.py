"""
Asset Pricing endpoints for cost management and billing
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from app.shared.security import get_current_auth_legacy as get_current_auth

router = APIRouter()
logger = logging.getLogger(__name__)

# Pricing models and cost data
PROVIDER_PRICING = {
    "dalle": {
        "model": "tier_based",
        "tiers": [
            {
                "name": "Tier 1",
                "monthly_fee": 5.00,
                "images_per_minute": 5,
                "monthly_limit": 15000,
                "standard_cost": 0.040,
                "hd_cost": 0.080
            },
            {
                "name": "Tier 2", 
                "monthly_fee": 50.00,
                "images_per_minute": 50,
                "monthly_limit": 150000,
                "standard_cost": 0.040,
                "hd_cost": 0.080
            },
            {
                "name": "Tier 3",
                "monthly_fee": 500.00,
                "images_per_minute": 500,
                "monthly_limit": 1500000,
                "standard_cost": 0.040,
                "hd_cost": 0.080
            }
        ]
    },
    "meshy": {
        "model": "credit_based",
        "packages": [
            {"name": "Starter", "credits": 200, "cost": 6.00},
            {"name": "Professional", "credits": 1000, "cost": 20.00},
            {"name": "Enterprise", "credits": 5000, "cost": 80.00}
        ],
        "operations": {
            "text_to_3d": 5,
            "texture_generation": 3,
            "refinement": 2
        }
    },
    "stability": {
        "model": "per_image",
        "standard_cost": 0.020,
        "hd_cost": 0.040,
        "ultra_cost": 0.080
    },
    "openai_gpt": {
        "model": "token_based",
        "input_cost_per_1k": 0.03,
        "output_cost_per_1k": 0.06
    },
    "claude": {
        "model": "token_based", 
        "input_cost_per_1k": 0.015,
        "output_cost_per_1k": 0.075
    }
}

@router.get("/current")
async def get_current_pricing(
    provider: str = Query(..., description="Provider name (dalle, meshy, stability, etc.)"),
    category: Optional[str] = Query(None, description="Asset category"),
    quality: Optional[str] = Query("standard", description="Quality level"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    Get current pricing for specific provider/category/quality
    """
    try:
        if provider not in PROVIDER_PRICING:
            raise HTTPException(status_code=404, detail=f"Pricing not found for provider: {provider}")
        
        pricing_data = PROVIDER_PRICING[provider].copy()
        pricing_data["provider"] = provider
        pricing_data["quality"] = quality
        pricing_data["last_updated"] = datetime.utcnow().isoformat()
        
        return {
            "pricing": pricing_data,
            "effective_date": datetime.utcnow().isoformat(),
            "currency": "USD"
        }
    except Exception as e:
        logger.error(f"Error getting pricing for {provider}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_pricing_analytics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    Get cost analytics for specified period
    """
    try:
        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Mock analytics data
        analytics = {
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "total_cost": 247.82,
            "cost_breakdown": {
                "dalle": 89.50,
                "meshy": 67.20,
                "stability": 45.12,
                "claude": 31.00,
                "openai_gpt": 15.00
            },
            "usage_metrics": {
                "total_images": 1247,
                "total_3d_models": 89,
                "total_tokens": 892450,
                "total_credits": 445
            },
            "cost_trends": [
                {"date": "2025-01-01", "daily_cost": 8.50},
                {"date": "2025-01-02", "daily_cost": 12.30},
                {"date": "2025-01-03", "daily_cost": 9.75},
                {"date": "2025-01-04", "daily_cost": 15.20},
                {"date": "2025-01-05", "daily_cost": 11.45}
            ],
            "top_cost_operations": [
                {"operation": "text_to_3d", "cost": 89.50, "count": 89},
                {"operation": "image_generation", "cost": 67.80, "count": 847},
                {"operation": "text_completion", "cost": 46.00, "count": 1523}
            ]
        }
        
        if provider:
            analytics["filtered_provider"] = provider
            if provider in analytics["cost_breakdown"]:
                analytics["provider_cost"] = analytics["cost_breakdown"][provider]
        
        return analytics
    except Exception as e:
        logger.error(f"Error getting pricing analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
async def update_pricing(
    provider: str = Query(..., description="Provider to update pricing for"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    Trigger pricing update for a provider
    """
    try:
        if provider not in PROVIDER_PRICING:
            raise HTTPException(status_code=404, detail=f"Provider not found: {provider}")
        
        return {
            "message": f"Pricing update triggered for {provider}",
            "provider": provider,
            "update_time": datetime.utcnow().isoformat(),
            "status": "queued",
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
    except Exception as e:
        logger.error(f"Error updating pricing for {provider}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers")
async def list_pricing_providers(auth_data: dict = Depends(get_current_auth)):
    """
    List all pricing providers and their capabilities
    """
    try:
        providers = []
        for provider_name, config in PROVIDER_PRICING.items():
            provider_info = {
                "name": provider_name,
                "pricing_model": config["model"],
                "status": "active",
                "last_updated": datetime.utcnow().isoformat(),
                "capabilities": []
            }
            
            if config["model"] == "tier_based":
                provider_info["capabilities"] = ["image_generation", "tier_management"]
                provider_info["tier_count"] = len(config["tiers"])
            elif config["model"] == "credit_based":
                provider_info["capabilities"] = ["3d_generation", "texture_generation"]
                provider_info["operations"] = list(config["operations"].keys())
            elif config["model"] == "per_image":
                provider_info["capabilities"] = ["image_generation", "quality_tiers"]
            elif config["model"] == "token_based":
                provider_info["capabilities"] = ["text_completion", "chat"]
                
            providers.append(provider_info)
        
        return {
            "providers": providers,
            "total_providers": len(providers),
            "supported_models": ["tier_based", "credit_based", "per_image", "token_based"]
        }
    except Exception as e:
        logger.error(f"Error listing pricing providers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cost-estimator/estimate")
async def estimate_cost(
    request: Dict[str, Any],
    auth_data: dict = Depends(get_current_auth)
):
    """
    Estimate cost before generation
    """
    try:
        provider = request.get("provider")
        operation = request.get("operation", "standard")
        quantity = request.get("quantity", 1)
        quality = request.get("quality", "standard")
        
        if not provider or provider not in PROVIDER_PRICING:
            raise HTTPException(status_code=400, detail="Valid provider required")
        
        config = PROVIDER_PRICING[provider]
        estimate = {"provider": provider, "operation": operation, "quantity": quantity}
        
        if config["model"] == "tier_based":
            cost = config["tiers"][0]["standard_cost"] if quality == "standard" else config["tiers"][0]["hd_cost"]
            estimate["cost_per_unit"] = cost
            estimate["total_cost"] = cost * quantity
            estimate["tier_fee"] = config["tiers"][0]["monthly_fee"]
            
        elif config["model"] == "credit_based":
            credits_per_op = config["operations"].get(operation, 5)
            estimate["credits_per_operation"] = credits_per_op
            estimate["total_credits"] = credits_per_op * quantity
            estimate["estimated_cost"] = (credits_per_op * quantity) * 0.04  # ~$0.04 per credit average
            
        elif config["model"] == "per_image":
            cost = config.get(f"{quality}_cost", config["standard_cost"])
            estimate["cost_per_unit"] = cost
            estimate["total_cost"] = cost * quantity
            
        elif config["model"] == "token_based":
            tokens = request.get("estimated_tokens", 1000)
            input_cost = (tokens * config["input_cost_per_1k"]) / 1000
            output_cost = (tokens * 0.5 * config["output_cost_per_1k"]) / 1000  # Assume 50% output ratio
            estimate["input_cost"] = input_cost
            estimate["output_cost"] = output_cost
            estimate["total_cost"] = input_cost + output_cost
            estimate["tokens_estimated"] = tokens
        
        estimate["currency"] = "USD"
        estimate["estimate_time"] = datetime.utcnow().isoformat()
        
        return estimate
    except Exception as e:
        logger.error(f"Error estimating cost: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cost-estimator/dalle-tiers")
async def get_dalle_tiers(auth_data: dict = Depends(get_current_auth)):
    """
    Get DALL-E tier information and pricing
    """
    try:
        if "dalle" not in PROVIDER_PRICING:
            raise HTTPException(status_code=404, detail="DALL-E pricing not configured")
        
        dalle_config = PROVIDER_PRICING["dalle"]
        return {
            "provider": "dalle",
            "pricing_model": dalle_config["model"],
            "tiers": dalle_config["tiers"],
            "currency": "USD",
            "billing_cycle": "monthly"
        }
    except Exception as e:
        logger.error(f"Error getting DALL-E tiers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cost-estimator/meshy-packages")
async def get_meshy_packages(auth_data: dict = Depends(get_current_auth)):
    """
    Get Meshy credit packages and costs
    """
    try:
        if "meshy" not in PROVIDER_PRICING:
            raise HTTPException(status_code=404, detail="Meshy pricing not configured")
        
        meshy_config = PROVIDER_PRICING["meshy"]
        return {
            "provider": "meshy",
            "pricing_model": meshy_config["model"],
            "packages": meshy_config["packages"],
            "operations": meshy_config["operations"],
            "currency": "USD"
        }
    except Exception as e:
        logger.error(f"Error getting Meshy packages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cost-estimator/provider-comparison")
async def compare_provider_costs(
    operation: str = Query(..., description="Operation to compare (image_generation, text_completion, etc.)"),
    quantity: int = Query(1, description="Quantity for comparison"),
    quality: str = Query("standard", description="Quality level"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    Compare costs across providers for the same operation
    """
    try:
        comparisons = []
        
        for provider_name, config in PROVIDER_PRICING.items():
            if config["model"] == "per_image" and operation == "image_generation":
                cost = config.get(f"{quality}_cost", config["standard_cost"])
                comparisons.append({
                    "provider": provider_name,
                    "cost_per_unit": cost,
                    "total_cost": cost * quantity,
                    "model": config["model"]
                })
            elif config["model"] == "token_based" and operation == "text_completion":
                # Estimate based on 1000 tokens
                tokens = 1000
                input_cost = (tokens * config["input_cost_per_1k"]) / 1000
                output_cost = (tokens * 0.5 * config["output_cost_per_1k"]) / 1000
                total_cost = (input_cost + output_cost) * quantity
                comparisons.append({
                    "provider": provider_name,
                    "cost_per_1k_tokens": input_cost + output_cost,
                    "total_cost": total_cost,
                    "model": config["model"]
                })
        
        # Sort by total cost
        comparisons.sort(key=lambda x: x.get("total_cost", 0))
        
        return {
            "operation": operation,
            "quantity": quantity,
            "quality": quality,
            "providers": comparisons,
            "cheapest_provider": comparisons[0]["provider"] if comparisons else None,
            "comparison_time": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error comparing provider costs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))