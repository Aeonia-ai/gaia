"""
v0.2 API Router

This version includes:
- Unified streaming/non-streaming chat endpoint
- OpenAI/Anthropic compatible streaming format
- Multi-provider support with intelligent selection
- Clean, professional API structure
"""
from fastapi import APIRouter

from app.api.v0_2.endpoints import chat, models, asset_pricing, usage_tracking, personas, performance
from app.api.v0_2.endpoints import providers_simple as providers
from app.services.chat import chat_stream

api_router = APIRouter(prefix="/api/v0.2")

# Core endpoints
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(chat_stream.router, prefix="/chat", tags=["streaming"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(models.router, prefix="/models", tags=["models"])

# Asset pricing and usage tracking
api_router.include_router(asset_pricing.router, prefix="/assets/pricing", tags=["asset_pricing"])
api_router.include_router(usage_tracking.router, prefix="/usage", tags=["usage_tracking"])

# Persona management
api_router.include_router(personas.router, prefix="/personas", tags=["personas"])

# Performance monitoring
api_router.include_router(performance.router, prefix="/performance", tags=["performance"])

# API info
@api_router.get("/")
async def api_info():
    """Get API version information"""
    return {
        "version": "0.2",
        "status": "stable",
        "description": "Unified LLM API with streaming support",
        "features": [
            "OpenAI/Anthropic compatible streaming",
            "Multi-provider support",
            "Intelligent model selection",
            "Unified chat endpoint"
        ],
        "endpoints": {
            "chat": "/api/v0.2/chat",
            "chat_stream": "/api/v0.2/chat/stream",
            "providers": "/api/v0.2/providers",
            "models": "/api/v0.2/models",
            "asset_pricing": "/api/v0.2/assets/pricing",
            "usage_tracking": "/api/v0.2/usage",
            "personas": "/api/v0.2/personas",
            "performance": "/api/v0.2/performance"
        }
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.2"}