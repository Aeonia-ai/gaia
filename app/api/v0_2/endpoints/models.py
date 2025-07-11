"""
Model management endpoints for multi-LLM support
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging

from app.shared.security import get_current_auth_legacy as get_current_auth

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
async def list_all_models(
    provider: Optional[str] = Query(None, description="Filter by provider"),
    capability: Optional[str] = Query(None, description="Filter by capability"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    List all available models across all providers
    """
    try:
        # Simple fallback response while provider system is being implemented
        models = [
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "provider": "claude", 
                "capabilities": ["chat", "streaming"],
                "max_tokens": 4096,
                "context_window": 200000
            },
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "provider": "openai",
                "capabilities": ["chat", "streaming", "tool_calling"],
                "max_tokens": 16384,
                "context_window": 128000
            }
        ]
        
        # Apply filters
        if provider:
            models = [m for m in models if m["provider"] == provider]
        if capability:
            models = [m for m in models if capability in m["capabilities"]]
        
        return {
            "models": models,
            "total": len(models),
            "filters": {
                "provider": provider,
                "capability": capability
            }
        }
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{model_id}")
async def get_model_info(
    model_id: str,
    auth_data: dict = Depends(get_current_auth)
):
    """
    Get detailed information about a specific model
    """
    try:
        # Simple model database
        models_db = {
            "claude-3-haiku-20240307": {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "provider": "claude",
                "capabilities": ["chat", "streaming"],
                "max_tokens": 4096,
                "context_window": 200000,
                "cost_per_input_token": 0.00000025,
                "cost_per_output_token": 0.00000125,
                "avg_response_time_ms": 450,
                "quality_score": 0.85,
                "speed_score": 0.95,
                "description": "Fast and efficient model for everyday tasks",
                "is_deprecated": False,
                "supports_system_prompt": True,
                "supports_temperature": True,
                "supports_streaming": True
            },
            "claude-3-sonnet-20240229": {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "provider": "claude",
                "capabilities": ["chat", "streaming", "tool_calling"],
                "max_tokens": 4096,
                "context_window": 200000,
                "cost_per_input_token": 0.000003,
                "cost_per_output_token": 0.000015,
                "avg_response_time_ms": 650,
                "quality_score": 0.95,
                "speed_score": 0.80,
                "description": "Balanced model with excellent reasoning capabilities",
                "is_deprecated": False,
                "supports_system_prompt": True,
                "supports_temperature": True,
                "supports_streaming": True
            },
            "gpt-4o-mini": {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "provider": "openai",
                "capabilities": ["chat", "streaming", "tool_calling"],
                "max_tokens": 16384,
                "context_window": 128000,
                "cost_per_input_token": 0.00000015,
                "cost_per_output_token": 0.0000006,
                "avg_response_time_ms": 380,
                "quality_score": 0.88,
                "speed_score": 0.92,
                "description": "Small, fast, and cost-effective model",
                "is_deprecated": False,
                "supports_system_prompt": True,
                "supports_temperature": True,
                "supports_streaming": True
            },
            "gpt-4o": {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "provider": "openai", 
                "capabilities": ["chat", "streaming", "tool_calling", "vision"],
                "max_tokens": 4096,
                "context_window": 128000,
                "cost_per_input_token": 0.0000025,
                "cost_per_output_token": 0.00001,
                "avg_response_time_ms": 520,
                "quality_score": 0.98,
                "speed_score": 0.75,
                "description": "Most capable model with vision and advanced reasoning",
                "is_deprecated": False,
                "supports_system_prompt": True,
                "supports_temperature": True,
                "supports_streaming": True
            }
        }
        
        if model_id not in models_db:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
            
        return models_db[model_id]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model info for {model_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))