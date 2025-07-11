"""
Usage tracking endpoints for cost monitoring and analytics
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from app.shared.security import get_current_auth_legacy as get_current_auth

router = APIRouter()
logger = logging.getLogger(__name__)

# Mock usage data store
USAGE_DATA = {
    "current_month": {
        "total_cost": 247.82,
        "total_requests": 1523,
        "total_tokens": 892450,
        "total_images": 1247,
        "total_3d_models": 89,
        "providers": {
            "dalle": {"cost": 89.50, "requests": 423, "images": 423},
            "meshy": {"cost": 67.20, "requests": 89, "models": 89},
            "stability": {"cost": 45.12, "requests": 564, "images": 564},
            "claude": {"cost": 31.00, "requests": 234, "tokens": 445225},
            "openai_gpt": {"cost": 15.00, "requests": 213, "tokens": 447225}
        }
    }
}

@router.get("/current")
async def get_current_usage(
    provider: Optional[str] = Query(None, description="Filter by provider"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    Get current month usage statistics
    """
    try:
        usage = USAGE_DATA["current_month"].copy()
        usage["billing_period"] = {
            "start": datetime.now().replace(day=1).strftime("%Y-%m-%d"),
            "end": (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        }
        usage["as_of"] = datetime.utcnow().isoformat()
        
        if provider:
            if provider in usage["providers"]:
                usage["filtered_provider"] = provider
                usage["provider_usage"] = usage["providers"][provider]
            else:
                raise HTTPException(status_code=404, detail=f"No usage data for provider: {provider}")
        
        return usage
    except Exception as e:
        logger.error(f"Error getting current usage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_usage_history(
    days: int = Query(30, description="Number of days to retrieve"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    Get historical usage data
    """
    try:
        # Generate mock historical data
        history = []
        base_date = datetime.utcnow() - timedelta(days=days)
        
        for i in range(days):
            date = base_date + timedelta(days=i)
            daily_usage = {
                "date": date.strftime("%Y-%m-%d"),
                "total_cost": round(8.5 + (i % 10) * 1.5, 2),
                "total_requests": 45 + (i % 20),
                "total_tokens": 25000 + (i % 5000),
                "total_images": 35 + (i % 15),
                "breakdown": {
                    "dalle": {"cost": round(3.2 + (i % 3), 2), "requests": 15 + (i % 8)},
                    "meshy": {"cost": round(2.1 + (i % 2), 2), "requests": 3 + (i % 4)},
                    "stability": {"cost": round(1.8 + (i % 2), 2), "requests": 12 + (i % 6)},
                    "claude": {"cost": round(1.0 + (i % 1), 2), "requests": 8 + (i % 4)},
                    "openai_gpt": {"cost": round(0.4 + (i % 1), 2), "requests": 7 + (i % 3)}
                }
            }
            history.append(daily_usage)
        
        result = {
            "period": {
                "start_date": base_date.strftime("%Y-%m-%d"),
                "end_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "days": days
            },
            "usage_history": history,
            "summary": {
                "total_cost": sum(day["total_cost"] for day in history),
                "total_requests": sum(day["total_requests"] for day in history),
                "average_daily_cost": sum(day["total_cost"] for day in history) / len(history),
                "peak_cost_day": max(history, key=lambda x: x["total_cost"])["date"]
            }
        }
        
        if provider:
            filtered_history = []
            for day in history:
                if provider in day["breakdown"]:
                    filtered_day = {
                        "date": day["date"],
                        "provider": provider,
                        **day["breakdown"][provider]
                    }
                    filtered_history.append(filtered_day)
            result["filtered_provider"] = provider
            result["provider_history"] = filtered_history
        
        return result
    except Exception as e:
        logger.error(f"Error getting usage history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/log")
async def log_usage(
    usage_data: Dict[str, Any],
    auth_data: dict = Depends(get_current_auth)
):
    """
    Log usage data for cost tracking
    """
    try:
        required_fields = ["provider", "operation", "cost"]
        for field in required_fields:
            if field not in usage_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Create usage log entry
        log_entry = {
            "id": f"usage_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": auth_data.get("user_id", "unknown"),
            "provider": usage_data["provider"],
            "operation": usage_data["operation"],
            "cost": float(usage_data["cost"]),
            "metadata": {
                "tokens": usage_data.get("tokens", 0),
                "images": usage_data.get("images", 0),
                "credits": usage_data.get("credits", 0),
                "quality": usage_data.get("quality", "standard"),
                "model": usage_data.get("model"),
                "request_id": usage_data.get("request_id")
            }
        }
        
        # In a real implementation, this would be saved to database
        logger.info(f"Usage logged: {log_entry}")
        
        return {
            "message": "Usage logged successfully",
            "log_id": log_entry["id"],
            "cost_logged": log_entry["cost"],
            "timestamp": log_entry["timestamp"]
        }
    except Exception as e:
        logger.error(f"Error logging usage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/limits")
async def get_usage_limits(
    provider: Optional[str] = Query(None, description="Provider to check limits for"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    Get current usage limits and remaining quotas
    """
    try:
        limits = {
            "dalle": {
                "current_tier": "Tier 1",
                "monthly_limit": 15000,
                "used_this_month": 423,
                "remaining": 14577,
                "rate_limit": 5,  # per minute
                "monthly_fee": 5.00,
                "overage_cost": 0.040
            },
            "meshy": {
                "current_package": "Professional",
                "credit_limit": 1000,
                "credits_used": 445,
                "credits_remaining": 555,
                "auto_renewal": True,
                "package_cost": 20.00
            },
            "stability": {
                "daily_limit": 1000,
                "used_today": 45,
                "remaining_today": 955,
                "cost_per_image": 0.020
            },
            "claude": {
                "token_limit": 1000000,  # monthly
                "tokens_used": 445225,
                "tokens_remaining": 554775,
                "cost_per_1k_tokens": 0.090  # combined input/output average
            },
            "openai_gpt": {
                "token_limit": 1000000,  # monthly
                "tokens_used": 447225,
                "tokens_remaining": 552775,
                "cost_per_1k_tokens": 0.045  # combined input/output average
            }
        }
        
        result = {
            "billing_period": {
                "start": datetime.now().replace(day=1).strftime("%Y-%m-%d"),
                "end": (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            },
            "limits": limits if not provider else {provider: limits.get(provider)},
            "warnings": []
        }
        
        # Add warnings for high usage
        for prov, limit_data in limits.items():
            if provider and provider != prov:
                continue
                
            if "used_this_month" in limit_data and "monthly_limit" in limit_data:
                usage_pct = (limit_data["used_this_month"] / limit_data["monthly_limit"]) * 100
                if usage_pct > 80:
                    result["warnings"].append({
                        "provider": prov,
                        "type": "high_usage",
                        "message": f"{prov} usage at {usage_pct:.1f}% of monthly limit",
                        "usage_percentage": usage_pct
                    })
        
        return result
    except Exception as e:
        logger.error(f"Error getting usage limits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/billing/current")
async def get_current_billing(auth_data: dict = Depends(get_current_auth)):
    """
    Get current billing period information
    """
    try:
        current_date = datetime.now()
        billing_start = current_date.replace(day=1)
        billing_end = (billing_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        billing_info = {
            "billing_period": {
                "start_date": billing_start.strftime("%Y-%m-%d"),
                "end_date": billing_end.strftime("%Y-%m-%d"),
                "days_remaining": (billing_end - current_date).days
            },
            "current_charges": {
                "subscription_fees": 75.00,  # Combined tier fees
                "usage_charges": 172.82,
                "overage_charges": 0.00,
                "total": 247.82
            },
            "payment_method": {
                "type": "credit_card",
                "last_four": "4242",
                "status": "active"
            },
            "next_billing_date": (billing_end + timedelta(days=1)).strftime("%Y-%m-%d"),
            "auto_payment": True,
            "estimated_next_bill": 285.50,
            "billing_alerts": [
                {
                    "type": "approaching_limit",
                    "message": "DALL-E usage at 85% of monthly limit",
                    "severity": "warning"
                }
            ]
        }
        
        return billing_info
    except Exception as e:
        logger.error(f"Error getting current billing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/monthly")
async def get_monthly_report(
    month: Optional[str] = Query(None, description="Month in YYYY-MM format"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    Generate monthly usage and cost report
    """
    try:
        if not month:
            month = datetime.now().strftime("%Y-%m")
        
        # Parse month
        try:
            year, month_num = month.split("-")
            report_date = datetime(int(year), int(month_num), 1)
        except:
            raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
        
        report = {
            "report_period": month,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_cost": 247.82,
                "total_requests": 1523,
                "total_tokens": 892450,
                "total_images": 1247,
                "total_3d_models": 89,
                "unique_operations": 8
            },
            "provider_breakdown": USAGE_DATA["current_month"]["providers"],
            "cost_categories": {
                "subscription_fees": 75.00,
                "per_use_charges": 172.82,
                "overage_charges": 0.00
            },
            "top_operations": [
                {"operation": "image_generation", "cost": 134.62, "count": 987},
                {"operation": "text_to_3d", "cost": 67.20, "count": 89},
                {"operation": "text_completion", "cost": 46.00, "count": 447}
            ],
            "cost_optimization_suggestions": [
                {
                    "suggestion": "Consider upgrading to DALL-E Tier 2 for better per-image rates",
                    "potential_savings": 12.50,
                    "reasoning": "Current high usage would benefit from higher tier"
                },
                {
                    "suggestion": "Switch some text completion tasks to Claude for cost efficiency",
                    "potential_savings": 8.75,
                    "reasoning": "Claude has lower per-token costs for long-form content"
                }
            ]
        }
        
        return report
    except Exception as e:
        logger.error(f"Error generating monthly report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))