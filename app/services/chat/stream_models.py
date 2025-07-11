"""
Streaming Model Selection Endpoints

Advanced model selection specifically optimized for streaming performance,
VR/AR applications, and real-time responses.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.shared.security import get_current_auth_legacy as get_current_auth
from app.services.llm import LLMProvider, ModelCapability
from app.services.llm.multi_provider_selector import ContextType, ModelPriority

router = APIRouter()
logger = logging.getLogger(__name__)

class StreamingModelRecommendationRequest(BaseModel):
    """Request for streaming-optimized model recommendation"""
    message: str
    activity: Optional[str] = "generic"
    priority: Optional[str] = "balanced"
    max_response_time_ms: Optional[int] = None
    vr_optimized: Optional[bool] = False
    required_capabilities: Optional[List[str]] = None

# Model performance data optimized for streaming
STREAMING_MODELS = [
    {
        "id": "gpt-4o-mini",
        "name": "GPT-4o Mini",
        "provider": "openai",
        "capabilities": ["text", "vision", "coding", "tool_calling"],
        "streaming_performance": {
            "ttft_ms": 180,  # Time to first token
            "tokens_per_second": 85,
            "max_concurrent": 100,
            "vr_optimized": True
        },
        "priority_scores": {"speed": 10, "quality": 8, "cost": 9, "vr": 10},
        "context_length": 128000
    },
    {
        "id": "claude-3-haiku-20240307",
        "name": "Claude 3 Haiku",
        "provider": "claude",
        "capabilities": ["text", "reasoning", "coding"],
        "streaming_performance": {
            "ttft_ms": 220,
            "tokens_per_second": 75,
            "max_concurrent": 80,
            "vr_optimized": True
        },
        "priority_scores": {"speed": 9, "quality": 7, "cost": 10, "vr": 9},
        "context_length": 200000
    },
    {
        "id": "gpt-3.5-turbo",
        "name": "GPT-3.5 Turbo",
        "provider": "openai",
        "capabilities": ["text", "coding"],
        "streaming_performance": {
            "ttft_ms": 150,
            "tokens_per_second": 90,
            "max_concurrent": 120,
            "vr_optimized": True
        },
        "priority_scores": {"speed": 10, "quality": 6, "cost": 10, "vr": 8},
        "context_length": 16385
    },
    {
        "id": "claude-3-sonnet-20240229",
        "name": "Claude 3 Sonnet",
        "provider": "claude",
        "capabilities": ["text", "reasoning", "coding", "analysis"],
        "streaming_performance": {
            "ttft_ms": 280,
            "tokens_per_second": 65,
            "max_concurrent": 60,
            "vr_optimized": False
        },
        "priority_scores": {"speed": 8, "quality": 9, "cost": 6, "vr": 6},
        "context_length": 200000
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "openai",
        "capabilities": ["text", "vision", "coding", "tool_calling", "analysis"],
        "streaming_performance": {
            "ttft_ms": 320,
            "tokens_per_second": 55,
            "max_concurrent": 40,
            "vr_optimized": False
        },
        "priority_scores": {"speed": 7, "quality": 10, "cost": 4, "vr": 5},
        "context_length": 128000
    },
    {
        "id": "claude-3-opus-20240229",
        "name": "Claude 3 Opus",
        "provider": "claude",
        "capabilities": ["text", "reasoning", "coding", "analysis"],
        "streaming_performance": {
            "ttft_ms": 400,
            "tokens_per_second": 45,
            "max_concurrent": 20,
            "vr_optimized": False
        },
        "priority_scores": {"speed": 6, "quality": 10, "cost": 3, "vr": 3},
        "context_length": 200000
    }
]

@router.get("/stream/models")
async def list_streaming_models(
    vr_only: bool = Query(False, description="Show only VR-optimized models"),
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    List all models with streaming performance characteristics.
    
    Returns models sorted by streaming performance with TTFT, throughput,
    and VR optimization indicators.
    """
    try:
        models = STREAMING_MODELS.copy()
        
        if vr_only:
            models = [m for m in models if m["streaming_performance"]["vr_optimized"]]
        
        # Sort by streaming performance (TTFT + tokens/sec)
        models.sort(key=lambda x: x["streaming_performance"]["ttft_ms"])
        
        return {
            "models": models,
            "total": len(models),
            "vr_filtered": vr_only,
            "performance_metrics": {
                "avg_ttft_ms": sum(m["streaming_performance"]["ttft_ms"] for m in models) // len(models),
                "fastest_ttft": min(m["streaming_performance"]["ttft_ms"] for m in models),
                "vr_optimized_count": sum(1 for m in models if m["streaming_performance"]["vr_optimized"])
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing streaming models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream/models/recommend")
async def recommend_streaming_model(
    message: str = Query(..., description="Message to analyze for model selection"),
    activity: str = Query("generic", description="Activity context"),
    priority: str = Query("balanced", description="Selection priority"),
    max_response_time_ms: Optional[int] = Query(None, description="Max acceptable response time"),
    vr_optimized: bool = Query(False, description="Require VR optimization"),
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Get model recommendation optimized for streaming performance.
    
    Analyzes message content and performance requirements to select
    the optimal model for streaming responses.
    """
    try:
        models = STREAMING_MODELS.copy()
        
        # Filter by VR requirement
        if vr_optimized:
            models = [m for m in models if m["streaming_performance"]["vr_optimized"]]
        
        # Filter by max response time
        if max_response_time_ms:
            models = [m for m in models if m["streaming_performance"]["ttft_ms"] <= max_response_time_ms]
        
        if not models:
            raise HTTPException(status_code=400, detail="No models meet the specified requirements")
        
        # Select based on priority
        if priority == "speed" or priority == "vr":
            # Sort by TTFT + tokens per second
            models.sort(key=lambda x: x["streaming_performance"]["ttft_ms"] - x["streaming_performance"]["tokens_per_second"])
            recommended = models[0]
            reasoning = f"Selected {recommended['name']} for maximum streaming speed (TTFT: {recommended['streaming_performance']['ttft_ms']}ms)"
        
        elif priority == "quality":
            # Sort by quality score
            models.sort(key=lambda x: x["priority_scores"]["quality"], reverse=True)
            recommended = models[0]
            reasoning = f"Selected {recommended['name']} for highest quality output while maintaining streaming capability"
        
        elif priority == "cost":
            # Sort by cost efficiency
            models.sort(key=lambda x: x["priority_scores"]["cost"], reverse=True)
            recommended = models[0]
            reasoning = f"Selected {recommended['name']} for cost efficiency with good streaming performance"
        
        else:  # balanced
            # Composite score: speed + quality - cost consideration
            for model in models:
                perf = model["streaming_performance"]
                scores = model["priority_scores"]
                # Lower TTFT is better, higher tokens/sec is better
                speed_score = (300 - perf["ttft_ms"]) + perf["tokens_per_second"]
                model["composite_score"] = speed_score + (scores["quality"] * 10) + (scores["cost"] * 5)
            
            models.sort(key=lambda x: x["composite_score"], reverse=True)
            recommended = models[0]
            reasoning = f"Selected {recommended['name']} for optimal balance of speed, quality, and cost in streaming"
        
        # Generate alternatives
        alternatives = models[1:4]  # Top 3 alternatives
        
        return {
            "recommended_model": recommended["id"],
            "provider": recommended["provider"],
            "confidence": 0.9,
            "reasoning": reasoning,
            "streaming_performance": recommended["streaming_performance"],
            "alternatives": [
                {
                    "model_id": alt["id"],
                    "provider": alt["provider"],
                    "ttft_ms": alt["streaming_performance"]["ttft_ms"],
                    "tokens_per_second": alt["streaming_performance"]["tokens_per_second"],
                    "reason": f"Alternative with {alt['streaming_performance']['ttft_ms']}ms TTFT"
                }
                for alt in alternatives
            ],
            "estimated_cost": 0.03,
            "estimated_ttft_ms": recommended["streaming_performance"]["ttft_ms"],
            "model_info": recommended,
            "selection_criteria": {
                "priority": priority,
                "vr_optimized": vr_optimized,
                "max_response_time_ms": max_response_time_ms,
                "activity": activity
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recommending streaming model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream/models/vr-recommendation")
async def get_vr_optimized_model(
    message: str = Query(..., description="Message for VR context analysis"),
    max_latency_ms: int = Query(200, description="Maximum acceptable latency"),
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Get VR/AR optimized model recommendation with ultra-low latency.
    
    Specifically designed for VR applications requiring sub-200ms responses.
    """
    try:
        # Filter for VR-optimized models under latency threshold
        vr_models = [
            m for m in STREAMING_MODELS 
            if m["streaming_performance"]["vr_optimized"] and 
               m["streaming_performance"]["ttft_ms"] <= max_latency_ms
        ]
        
        if not vr_models:
            raise HTTPException(
                status_code=400, 
                detail=f"No VR-optimized models available under {max_latency_ms}ms latency"
            )
        
        # Sort by VR score and TTFT
        vr_models.sort(key=lambda x: (x["priority_scores"]["vr"], -x["streaming_performance"]["ttft_ms"]), reverse=True)
        best_vr_model = vr_models[0]
        
        return {
            "recommended_model": best_vr_model["id"],
            "provider": best_vr_model["provider"],
            "vr_score": best_vr_model["priority_scores"]["vr"],
            "ttft_ms": best_vr_model["streaming_performance"]["ttft_ms"],
            "tokens_per_second": best_vr_model["streaming_performance"]["tokens_per_second"],
            "reasoning": f"Optimized for VR with {best_vr_model['streaming_performance']['ttft_ms']}ms TTFT",
            "vr_features": {
                "ultra_low_latency": True,
                "high_throughput": best_vr_model["streaming_performance"]["tokens_per_second"] > 70,
                "concurrent_users": best_vr_model["streaming_performance"]["max_concurrent"]
            },
            "alternatives": [
                {
                    "model_id": alt["id"],
                    "ttft_ms": alt["streaming_performance"]["ttft_ms"],
                    "vr_score": alt["priority_scores"]["vr"]
                }
                for alt in vr_models[1:3]
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting VR model recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream/models/performance")
async def get_model_performance_comparison(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Get detailed performance comparison of all streaming models.
    
    Returns comprehensive performance metrics for model selection.
    """
    try:
        performance_data = []
        
        for model in STREAMING_MODELS:
            perf = model["streaming_performance"]
            scores = model["priority_scores"]
            
            performance_data.append({
                "model_id": model["id"],
                "name": model["name"],
                "provider": model["provider"],
                "performance": {
                    "ttft_ms": perf["ttft_ms"],
                    "tokens_per_second": perf["tokens_per_second"],
                    "max_concurrent": perf["max_concurrent"],
                    "vr_optimized": perf["vr_optimized"]
                },
                "rankings": {
                    "speed_rank": None,  # Will be filled below
                    "quality_rank": None,
                    "cost_rank": None,
                    "vr_rank": None
                },
                "scores": scores,
                "capabilities": model["capabilities"]
            })
        
        # Calculate rankings
        for metric in ["speed", "quality", "cost", "vr"]:
            sorted_models = sorted(performance_data, key=lambda x: x["scores"][metric], reverse=True)
            for i, model in enumerate(sorted_models):
                model["rankings"][f"{metric}_rank"] = i + 1
        
        # Overall statistics
        stats = {
            "total_models": len(performance_data),
            "vr_optimized_count": sum(1 for m in performance_data if m["performance"]["vr_optimized"]),
            "avg_ttft_ms": sum(m["performance"]["ttft_ms"] for m in performance_data) // len(performance_data),
            "fastest_model": min(performance_data, key=lambda x: x["performance"]["ttft_ms"])["model_id"],
            "highest_throughput": max(performance_data, key=lambda x: x["performance"]["tokens_per_second"])["model_id"]
        }
        
        return {
            "models": performance_data,
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting model performance comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# User preference storage (in-memory for now)
user_streaming_preferences = {}

@router.post("/stream/models/user-preference")
async def set_user_streaming_preference(
    model_id: str = Query(..., description="Preferred model ID"),
    priority: str = Query("balanced", description="Default priority"),
    vr_mode: bool = Query(False, description="Enable VR mode by default"),
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Set user's streaming model preference."""
    try:
        auth_key = auth_principal.get("user_id") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Could not determine user ID")
        
        # Validate model exists
        valid_models = [m["id"] for m in STREAMING_MODELS]
        if model_id not in valid_models:
            raise HTTPException(status_code=400, detail=f"Invalid model ID: {model_id}")
        
        user_streaming_preferences[auth_key] = {
            "model_id": model_id,
            "priority": priority,
            "vr_mode": vr_mode,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        return {
            "status": "success",
            "message": "Streaming preference saved",
            "preference": user_streaming_preferences[auth_key]
        }
        
    except Exception as e:
        logger.error(f"Error setting user streaming preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream/models/user-preference")
async def get_user_streaming_preference(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Get user's streaming model preference."""
    try:
        auth_key = auth_principal.get("user_id") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Could not determine user ID")
        
        preference = user_streaming_preferences.get(auth_key)
        if not preference:
            return {
                "has_preference": False,
                "default": {
                    "model_id": "gpt-4o-mini",
                    "priority": "balanced",
                    "vr_mode": False
                }
            }
        
        return {
            "has_preference": True,
            "preference": preference
        }
        
    except Exception as e:
        logger.error(f"Error getting user streaming preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/stream/models/user-preference")
async def clear_user_streaming_preference(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Clear user's streaming model preference."""
    try:
        auth_key = auth_principal.get("user_id") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Could not determine user ID")
        
        removed = user_streaming_preferences.pop(auth_key, None)
        
        return {
            "status": "success",
            "message": "Streaming preference cleared",
            "had_preference": removed is not None
        }
        
    except Exception as e:
        logger.error(f"Error clearing user streaming preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))