"""
Provider management endpoints for multi-LLM support
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging

from app.shared.security import get_current_auth_legacy as get_current_auth
from app.models.chat import ModelSelectionRequest, ModelRecommendationResponse
from app.services.llm import (
    get_registry,
    LLMProvider,
    ModelCapability,
    ContextType,
    ModelPriority
)
from app.services.llm.multi_provider_selector import MultiProviderModelSelector, multi_provider_selector

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/providers")
async def list_providers(auth_data: dict = Depends(get_current_auth)):
    """
    List all available LLM providers and their status
    """
    try:
        registry = await get_registry()
        registry_info = await registry.get_registry_info()
        
        return {
            "providers": registry_info["available_providers"],
            "total_providers": registry_info["total_providers"],
            "health_status": registry_info["health_status"],
            "stats": registry_info["stats"],
            "timestamp": registry_info["timestamp"]
        }
    except Exception as e:
        logger.error(f"Error listing providers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers/{provider}/models")
async def list_provider_models(
    provider: str,
    auth_data: dict = Depends(get_current_auth)
):
    """
    List all models available from a specific provider
    """
    try:
        # Convert string to enum
        try:
            provider_enum = LLMProvider(provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
        
        registry = await get_registry()
        provider_instance = await registry.get_provider(provider_enum)
        models = provider_instance.available_models
        
        return {
            "provider": provider,
            "models": [
                {
                    "id": model.id,
                    "name": model.name,
                    "provider": model.provider.value,
                    "capabilities": [cap.value for cap in model.capabilities],
                    "max_tokens": model.max_tokens,
                    "context_window": model.context_window,
                    "cost_per_input_token": model.cost_per_input_token,
                    "cost_per_output_token": model.cost_per_output_token,
                    "avg_response_time_ms": model.avg_response_time_ms,
                    "quality_score": model.quality_score,
                    "speed_score": model.speed_score,
                    "description": model.description,
                    "is_deprecated": model.is_deprecated,
                    "supports_system_prompt": model.supports_system_prompt,
                    "supports_temperature": model.supports_temperature,
                    "supports_streaming": model.supports_streaming
                }
                for model in models
            ],
            "total_models": len(models)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing models for provider {provider}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_all_models(
    capability: Optional[str] = Query(None, description="Filter by capability"),
    max_response_time_ms: Optional[int] = Query(None, description="Filter by max response time"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    List all available models from all providers with optional filtering
    """
    try:
        registry = await get_registry()
        all_models = await registry.get_all_models()
        
        # Flatten models from all providers
        models = []
        for provider_models in all_models.values():
            models.extend(provider_models)
        
        # Apply filters
        if capability:
            try:
                cap_enum = ModelCapability(capability)
                models = [m for m in models if cap_enum in m.capabilities]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid capability: {capability}")
        
        if max_response_time_ms:
            models = [m for m in models if m.avg_response_time_ms <= max_response_time_ms]
        
        if provider:
            try:
                provider_enum = LLMProvider(provider)
                models = [m for m in models if m.provider == provider_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
        
        return {
            "models": [
                {
                    "id": model.id,
                    "name": model.name,
                    "provider": model.provider.value,
                    "capabilities": [cap.value for cap in model.capabilities],
                    "max_tokens": model.max_tokens,
                    "context_window": model.context_window,
                    "cost_per_input_token": model.cost_per_input_token,
                    "cost_per_output_token": model.cost_per_output_token,
                    "avg_response_time_ms": model.avg_response_time_ms,
                    "quality_score": model.quality_score,
                    "speed_score": model.speed_score,
                    "description": model.description,
                    "is_deprecated": model.is_deprecated
                }
                for model in models
            ],
            "total_models": len(models),
            "filters_applied": {
                "capability": capability,
                "max_response_time_ms": max_response_time_ms,
                "provider": provider
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing all models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models/{model_id}")
async def get_model_info(
    model_id: str,
    auth_data: dict = Depends(get_current_auth)
):
    """
    Get detailed information about a specific model
    """
    try:
        registry = await get_registry()
        model = await registry.get_model_info(model_id)
        
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
        
        return {
            "id": model.id,
            "name": model.name,
            "provider": model.provider.value,
            "capabilities": [cap.value for cap in model.capabilities],
            "max_tokens": model.max_tokens,
            "context_window": model.context_window,
            "cost_per_input_token": model.cost_per_input_token,
            "cost_per_output_token": model.cost_per_output_token,
            "avg_response_time_ms": model.avg_response_time_ms,
            "quality_score": model.quality_score,
            "speed_score": model.speed_score,
            "description": model.description,
            "is_deprecated": model.is_deprecated,
            "supports_system_prompt": model.supports_system_prompt,
            "supports_temperature": model.supports_temperature,
            "supports_streaming": model.supports_streaming
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model info for {model_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/models/recommend", response_model=ModelRecommendationResponse)
async def recommend_model(
    request: ModelSelectionRequest,
    auth_data: dict = Depends(get_current_auth)
):
    """
    Get model recommendation based on requirements
    """
    try:
        # Convert string enums
        context_type = None
        if request.context_type:
            try:
                context_type = ContextType(request.context_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid context_type: {request.context_type}")
        
        priority = None
        if request.priority:
            try:
                priority = ModelPriority(request.priority)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid priority: {request.priority}")
        
        preferred_provider = None
        if request.provider:
            try:
                preferred_provider = LLMProvider(request.provider)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {request.provider}")
        
        # Convert capability strings to enums
        required_capabilities = []
        if request.required_capabilities:
            for cap in request.required_capabilities:
                try:
                    required_capabilities.append(ModelCapability(cap))
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid capability: {cap}")
        
        # Get recommendation
        await multi_provider_selector.initialize()
        recommendation = await multi_provider_selector.select_model(
            message=request.message,
            context_type=context_type,
            priority=priority,
            max_response_time_ms=request.max_response_time_ms,
            preferred_provider=preferred_provider,
            required_capabilities=required_capabilities
        )
        
        # Get alternatives
        alternatives = []
        if len(recommendation.fallback_models) > 0:
            registry = await get_registry()
            for model_id in recommendation.fallback_models[:3]:  # Top 3 alternatives
                model_info = await registry.get_model_info(model_id)
                if model_info:
                    alternatives.append({
                        "model_id": model_info.id,
                        "provider": model_info.provider.value,
                        "quality_score": model_info.quality_score,
                        "avg_response_time_ms": model_info.avg_response_time_ms,
                        "cost_per_input_token": model_info.cost_per_input_token
                    })
        
        return ModelRecommendationResponse(
            recommended_model=recommendation.model_id,
            provider=recommendation.provider.value,
            confidence=recommendation.confidence,
            reasoning=recommendation.reasoning,
            alternatives=alternatives,
            estimated_cost=recommendation.estimated_cost,
            estimated_response_time_ms=recommendation.estimated_response_time_ms,
            model_info={
                "name": recommendation.model_info.name,
                "capabilities": [cap.value for cap in recommendation.model_info.capabilities],
                "max_tokens": recommendation.model_info.max_tokens,
                "context_window": recommendation.model_info.context_window,
                "quality_score": recommendation.model_info.quality_score,
                "speed_score": recommendation.model_info.speed_score
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recommending model: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models/compare")
async def compare_models(
    model_ids: str = Query(..., description="Comma-separated list of model IDs to compare"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    Compare multiple models across different criteria
    """
    try:
        model_id_list = [mid.strip() for mid in model_ids.split(",")]
        
        if len(model_id_list) < 2:
            raise HTTPException(status_code=400, detail="At least 2 models required for comparison")
        
        if len(model_id_list) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 models allowed for comparison")
        
        await multi_provider_selector.initialize()
        comparison = await multi_provider_selector.get_model_comparison(model_id_list)
        
        if "error" in comparison:
            raise HTTPException(status_code=400, detail=comparison["error"])
        
        return comparison
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers/health")
async def get_provider_health(auth_data: dict = Depends(get_current_auth)):
    """
    Get health status of all providers
    """
    try:
        registry = await get_registry()
        health_status = await registry.health_check_all()
        
        return {
            "health_checks": {
                provider.value: {
                    "status": health.status,
                    "response_time_ms": health.response_time_ms,
                    "error": health.error,
                    "last_checked": health.last_checked.isoformat() if health.last_checked else None,
                    "available_models": health.available_models
                }
                for provider, health in health_status.items()
            },
            "summary": {
                "healthy_providers": len([h for h in health_status.values() if h.status == "healthy"]),
                "total_providers": len(health_status),
                "unhealthy_providers": [
                    p.value for p, h in health_status.items() if h.status == "unhealthy"
                ]
            }
        }
    except Exception as e:
        logger.error(f"Error getting provider health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/providers/health/check")
async def trigger_health_check(auth_data: dict = Depends(get_current_auth)):
    """
    Trigger a health check for all providers
    """
    try:
        registry = await get_registry()
        health_status = await registry.health_check_all()
        
        return {
            "message": "Health check completed",
            "results": {
                provider.value: health.status
                for provider, health in health_status.items()
            }
        }
    except Exception as e:
        logger.error(f"Error triggering health check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers/stats")
async def get_provider_stats(auth_data: dict = Depends(get_current_auth)):
    """
    Get usage statistics for all providers
    """
    try:
        registry = await get_registry()
        stats = registry.get_stats()
        
        return {
            "provider_stats": {
                provider.value: {
                    "requests_count": stat.requests_count,
                    "total_tokens": stat.total_tokens,
                    "total_cost": stat.total_cost,
                    "avg_response_time_ms": stat.avg_response_time_ms,
                    "error_count": stat.error_count,
                    "error_rate": stat.error_count / stat.requests_count if stat.requests_count > 0 else 0,
                    "last_request": stat.last_request.isoformat() if stat.last_request else None
                }
                for provider, stat in stats.items()
            },
            "summary": {
                "total_requests": sum(s.requests_count for s in stats.values()),
                "total_tokens": sum(s.total_tokens for s in stats.values()),
                "total_cost": sum(s.total_cost for s in stats.values()),
                "total_errors": sum(s.error_count for s in stats.values())
            }
        }
    except Exception as e:
        logger.error(f"Error getting provider stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))