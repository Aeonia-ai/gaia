"""
Gaia Platform Gateway Service

Main entry point for all client requests. Routes requests to appropriate services
while maintaining backward compatibility with LLM Platform API patterns.

This service:
1. Accepts all client requests on port 8666 (same as LLM Platform)
2. Handles authentication via JWT or API key
3. Routes requests to appropriate backend services
4. Maintains identical API endpoints for client compatibility
5. Coordinates responses from multiple services when needed
"""

import os
import asyncio
import httpx
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import shared Gaia utilities
from app.shared import (
    settings,
    get_logger,
    configure_logging_for_service,
    log_service_startup,
    log_service_shutdown,
    get_current_auth_legacy,
    ensure_nats_connection,
    NATSSubjects,
    ServiceHealthEvent,
    database_health_check,
    supabase_health_check
)
from app.shared.redis_client import redis_client, CacheManager
from app.gateway.cache_middleware import CacheMiddleware

# Configure logging for gateway service
logger = configure_logging_for_service("gateway")

# Redis-based rate limiter configuration
def redis_rate_limit_key_func(request: Request):
    """Generate rate limit key using user authentication or IP."""
    try:
        # Try to get user ID from auth header for user-specific limits
        auth_header = request.headers.get("authorization")
        api_key = request.headers.get("x-api-key")
        
        if auth_header and auth_header.startswith("Bearer "):
            # Use JWT token hash for user rate limiting
            token = auth_header[7:]
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
            return f"user:jwt:{token_hash}"
        elif api_key:
            # Use API key hash for service rate limiting
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"user:api:{key_hash}"
        else:
            # Fall back to IP-based rate limiting
            return f"ip:{get_remote_address(request)}"
    except Exception:
        # Fallback to IP if anything fails
        return f"ip:{get_remote_address(request)}"

# Configure limiter - will use Redis if available
limiter = Limiter(key_func=redis_rate_limit_key_func)

# FastAPI application
app = FastAPI(
    title="LLM Platform", 
    description="AI-powered language model API with multi-provider support",
    version="0.2"
)

# Add response caching middleware for static endpoints
app.add_middleware(CacheMiddleware)

# Add GZip compression middleware (30-50% smaller responses)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add CORS middleware (identical to LLM Platform)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Service URL configuration
SERVICE_URLS = {
    "auth": settings.AUTH_SERVICE_URL,
    "asset": settings.ASSET_SERVICE_URL,
    "chat": settings.CHAT_SERVICE_URL
}

# HTTP client for service communication
http_client: Optional[httpx.AsyncClient] = None

async def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client for service communication."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.GATEWAY_REQUEST_TIMEOUT)
        )
    return http_client

async def forward_request_to_service(
    service_name: str,
    path: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Forward a request to a specific service and return the response."""
    
    if service_name not in SERVICE_URLS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {service_name} not available"
        )
    
    service_url = SERVICE_URLS[service_name]
    full_url = f"{service_url}{path}"
    
    client = await get_http_client()
    
    try:
        logger.service(f"Forwarding {method} request to {service_name}: {path}")
        
        response = await client.request(
            method=method,
            url=full_url,
            headers=headers,
            params=params,
            json=json_data,
            files=files
        )
        
        response.raise_for_status()
        
        # Handle different response types
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                return response.json()
            except Exception as json_error:
                # Log the raw response that's causing JSON parsing issues
                logger.error(f"JSON parsing failed for {service_name} response")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Raw response text: {repr(response.text)}")
                logger.error(f"JSON error: {json_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid JSON response from {service_name} service"
                )
        else:
            return {"content": response.content, "content_type": response.headers.get("content-type")}
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Service {service_name} returned error {e.response.status_code}: {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Service error: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to service {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {service_name} unavailable"
        )

# Health check endpoint (no authentication required, same as LLM Platform)
@app.get("/health", include_in_schema=True, tags=["Health"])
async def health_check():
    """Health check endpoint that bypasses authentication for deployment platforms."""
    # Check health of all services
    service_health = {}
    
    for service_name, service_url in SERVICE_URLS.items():
        try:
            client = await get_http_client()
            response = await client.get(f"{service_url}/health", timeout=5.0)
            service_health[service_name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else None
            }
        except Exception as e:
            service_health[service_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # Check database and supabase
    db_health = await database_health_check()
    supabase_health = await supabase_health_check()
    
    # Check Redis health
    redis_health = {
        "status": "healthy" if redis_client.is_connected() else "unhealthy",
        "connected": redis_client.is_connected()
    }
    
    overall_status = "healthy"
    if any(s["status"] != "healthy" for s in service_health.values()):
        overall_status = "degraded"
    if db_health["status"] != "healthy":
        overall_status = "unhealthy"
    if redis_health["status"] != "healthy":
        overall_status = "degraded"  # Redis failure doesn't make system unhealthy
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": "0.2.0",
        "services": service_health,
        "database": db_health,
        "redis": redis_health,
        "supabase": supabase_health
    }

# Root endpoint (same as LLM Platform)
@app.get("/")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}")
async def root(request: Request):
    """Root endpoint handler with rate limiting."""
    logger.input("Received request to root endpoint")
    return {
        "message": "LLM Platform API is running",
        "versions": {
            "v0.2": "/api/v0.2 (recommended - unified streaming API)",
            "v1": "/api/v1 (original endpoints)",
            "legacy": "/ (will be deprecated)"
        },
        "note": "Use v0.2 for the latest OpenAI/Anthropic compatible streaming API."
    }

# ========================================================================================
# API v0.2 ENDPOINTS - Unified streaming API (recommended)
# ========================================================================================

# v0.2 API root endpoint
@app.get("/api/v0.2/", tags=["v0.2 API"])
async def v0_2_api_info():
    """Get v0.2 API information"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/",
        method="GET"
    )

@app.get("/api/v0.2/health", tags=["v0.2 API"])
async def v0_2_health():
    """v0.2 API health check"""
    return await forward_request_to_service(
        service_name="chat", 
        path="/api/v0.2/health",
        method="GET"
    )

# v0.2 Chat endpoints
@app.post("/api/v0.2/chat", tags=["v0.2 Chat"])
async def v0_2_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """v0.2 unified chat endpoint (streaming and non-streaming)"""
    # Simple implementation using Anthropic directly
    import anthropic
    
    body = await request.json()
    message = body.get("message", "")
    model = body.get("model", "claude-3-5-sonnet-20241022")
    
    try:
        # Use Anthropic directly for now
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": message}]
        )
        
        return {
            "response": response.content[0].text,
            "model": model,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to process chat request", "detail": str(e)}
        )

@app.get("/api/v0.2/chat/status", tags=["v0.2 Chat"])
async def v0_2_chat_status(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get v0.2 chat status"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/chat/status",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.delete("/api/v0.2/chat/history", tags=["v0.2 Chat"])
async def v0_2_clear_chat_history(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Clear v0.2 chat history"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/chat/history",
        method="DELETE",
        headers=dict(request.headers)
    )

@app.post("/api/v0.2/chat/reload-prompt", tags=["v0.2 Chat"])
async def v0_2_reload_prompt(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Reload v0.2 system prompt"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/chat/reload-prompt",
        method="POST",
        headers=dict(request.headers)
    )

# v0.2 Streaming Chat endpoints  
@app.post("/api/v0.2/chat/stream", tags=["v0.2 Streaming"])
async def v0_2_stream_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """v0.2 streaming chat endpoint with SSE support"""
    from fastapi.responses import StreamingResponse
    import anthropic
    
    body = await request.json()
    message = body.get("message", "")
    model = body.get("model", "claude-3-5-sonnet-20241022")
    
    async def stream_generator():
        """Generate SSE stream from Anthropic response"""
        try:
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            stream = await client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": message}],
                stream=True
            )
            
            async for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.text:
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': event.delta.text}}]})}\n\n"
                
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive", 
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/v0.2/chat/stream/cache/invalidate", tags=["v0.2 Streaming"])
async def v0_2_invalidate_streaming_cache(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Invalidate v0.2 streaming cache"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/chat/stream/cache/invalidate",
        method="POST",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/chat/stream/cache/status", tags=["v0.2 Streaming"])
async def v0_2_get_streaming_cache_status(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get v0.2 streaming cache status"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/chat/stream/cache/status",
        method="GET",
        headers=dict(request.headers)
    )

@app.get("/api/v0.2/chat/stream/status", tags=["v0.2 Streaming"])
async def v0_2_get_streaming_status(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get v0.2 streaming status"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/chat/stream/status",
        method="GET",
        headers=dict(request.headers)
    )

@app.delete("/api/v0.2/chat/stream/history", tags=["v0.2 Streaming"])
async def v0_2_clear_streaming_history(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Clear v0.2 streaming history"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/chat/stream/history",
        method="DELETE",
        headers=dict(request.headers)
    )

@app.get("/api/v0.2/chat/stream/models", tags=["v0.2 Streaming"])
async def v0_2_list_streaming_models(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """List v0.2 streaming models"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/chat/stream/models",
        method="GET",
        headers=dict(request.headers)
    )


@app.get("/api/v0.2/chat/stream/models/performance", tags=["v0.2 Streaming"])
async def v0_2_get_streaming_model_performance(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get v0.2 streaming model performance comparison"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/chat/stream/models/performance",
        method="GET",
        headers=dict(request.headers)
    )

# v0.2 Provider endpoints
@app.get("/api/v0.2/providers", tags=["v0.2 Providers"])
async def v0_2_list_providers(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """List all providers"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/providers/",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/providers/{provider}", tags=["v0.2 Providers"])
async def v0_2_get_provider(
    provider: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get provider details"""
    return await forward_request_to_service(
        service_name="chat",
        path=f"/api/v0.2/providers/{provider}",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/providers/{provider}/models", tags=["v0.2 Providers"])
async def v0_2_get_provider_models(
    provider: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get provider models"""
    return await forward_request_to_service(
        service_name="chat",
        path=f"/api/v0.2/providers/{provider}/models",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/providers/{provider}/health", tags=["v0.2 Providers"])
async def v0_2_get_provider_health(
    provider: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get provider health"""
    return await forward_request_to_service(
        service_name="chat",
        path=f"/api/v0.2/providers/{provider}/health",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/providers/stats", tags=["v0.2 Providers"])
async def v0_2_get_all_provider_stats(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get stats for all providers"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/providers/stats",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/providers/{provider}/stats", tags=["v0.2 Providers"])
async def v0_2_get_provider_stats(
    provider: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get provider stats"""
    return await forward_request_to_service(
        service_name="chat",
        path=f"/api/v0.2/providers/{provider}/stats",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

# v0.2 Model endpoints
@app.get("/api/v0.2/models", tags=["v0.2 Models"])
async def v0_2_list_models(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """List all models"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/models/",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/models/{model_id}", tags=["v0.2 Models"])
async def v0_2_get_model(
    model_id: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get model details"""
    return await forward_request_to_service(
        service_name="chat",
        path=f"/api/v0.2/models/{model_id}",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )


@app.get("/api/v0.2/models/capabilities", tags=["v0.2 Models"])
async def v0_2_get_capabilities(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get model capabilities"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/models/capabilities",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/models/priorities", tags=["v0.2 Models"])
async def v0_2_get_priorities(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get model priorities"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/models/priorities",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/models/contexts", tags=["v0.2 Models"])
async def v0_2_get_contexts(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get model contexts"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/models/contexts",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

# ========================================================================================
# ASSET PRICING ENDPOINTS - Revenue and cost management
# ========================================================================================

@app.get("/api/v0.2/assets/pricing/current", tags=["v0.2 Asset Pricing"])
async def v0_2_get_current_pricing(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get current pricing for provider/category/quality"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/assets/pricing/current",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/assets/pricing/analytics", tags=["v0.2 Asset Pricing"])
async def v0_2_get_pricing_analytics(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get cost analytics for specified period"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/assets/pricing/analytics",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.post("/api/v0.2/assets/pricing/update", tags=["v0.2 Asset Pricing"])
async def v0_2_update_pricing(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Trigger pricing update for a provider"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/assets/pricing/update",
        method="POST",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/assets/pricing/providers", tags=["v0.2 Asset Pricing"])
async def v0_2_list_pricing_providers(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """List all pricing providers and capabilities"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/assets/pricing/providers",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.post("/api/v0.2/assets/pricing/cost-estimator/estimate", tags=["v0.2 Cost Estimation"])
async def v0_2_estimate_cost(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Estimate cost before generation"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/assets/pricing/cost-estimator/estimate",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.get("/api/v0.2/assets/pricing/cost-estimator/dalle-tiers", tags=["v0.2 Cost Estimation"])
async def v0_2_get_dalle_tiers(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get DALL-E tier information and pricing"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/assets/pricing/cost-estimator/dalle-tiers",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/assets/pricing/cost-estimator/meshy-packages", tags=["v0.2 Cost Estimation"])
async def v0_2_get_meshy_packages(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get Meshy credit packages and costs"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/assets/pricing/cost-estimator/meshy-packages",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/assets/pricing/cost-estimator/provider-comparison", tags=["v0.2 Cost Estimation"])
async def v0_2_compare_provider_costs(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Compare costs across providers"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/assets/pricing/cost-estimator/provider-comparison",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

# Usage tracking endpoints
@app.get("/api/v0.2/usage/current", tags=["v0.2 Usage Tracking"])
async def v0_2_get_current_usage(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get current month usage statistics"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/usage/current",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/usage/history", tags=["v0.2 Usage Tracking"])
async def v0_2_get_usage_history(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get historical usage data"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/usage/history",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.post("/api/v0.2/usage/log", tags=["v0.2 Usage Tracking"])
async def v0_2_log_usage(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Log usage data for cost tracking"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/usage/log",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.get("/api/v0.2/usage/limits", tags=["v0.2 Usage Tracking"])
async def v0_2_get_usage_limits(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get usage limits and remaining quotas"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/usage/limits",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/usage/billing/current", tags=["v0.2 Usage Tracking"])
async def v0_2_get_current_billing(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get current billing period information"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/usage/billing/current",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/usage/reports/monthly", tags=["v0.2 Usage Tracking"])
async def v0_2_get_monthly_report(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Generate monthly usage and cost report"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/usage/reports/monthly",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

# ========================================================================================
# PERSONA MANAGEMENT ENDPOINTS - User experience personalization  
# ========================================================================================

@app.get("/api/v0.2/personas", tags=["v0.2 Personas"])
async def v0_2_list_personas(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """List all available personas"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/personas/",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/personas/current", tags=["v0.2 Personas"])
async def v0_2_get_current_persona(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get user's current active persona"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/personas/current",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/personas/{persona_id}", tags=["v0.2 Personas"])
async def v0_2_get_persona(
    persona_id: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get specific persona by ID"""
    return await forward_request_to_service(
        service_name="chat",
        path=f"/api/v0.2/personas/{persona_id}",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.post("/api/v0.2/personas", tags=["v0.2 Personas"])
async def v0_2_create_persona(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Create new persona"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/personas/",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.put("/api/v0.2/personas/{persona_id}", tags=["v0.2 Personas"])
async def v0_2_update_persona(
    persona_id: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Update existing persona"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path=f"/api/v0.2/personas/{persona_id}",
        method="PUT",
        json_data=body,
        headers=headers
    )

@app.delete("/api/v0.2/personas/{persona_id}", tags=["v0.2 Personas"])
async def v0_2_delete_persona(
    persona_id: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Soft delete persona"""
    return await forward_request_to_service(
        service_name="chat",
        path=f"/api/v0.2/personas/{persona_id}",
        method="DELETE",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.post("/api/v0.2/personas/set", tags=["v0.2 Personas"])
async def v0_2_set_user_persona(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Set user's active persona"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/personas/set",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.post("/api/v0.2/personas/initialize-default", tags=["v0.2 Personas"])
async def v0_2_initialize_default_persona(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Initialize default Mu persona"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/personas/initialize-default",
        method="POST",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

# =============================================================================
# KB-Enhanced Chat Endpoints (KOS Integration)
# =============================================================================

@app.post("/api/v1/chat/kb-enhanced", tags=["KB Chat"])
async def kb_enhanced_multiagent_chat(request: Request, auth: dict = Depends(get_current_auth_legacy)):
    """
    KB-Enhanced multiagent chat with Knowledge Base integration.
    
    Features:
    - Direct KB access via MCP tools
    - Context-aware agent behaviors
    - Knowledge synthesis across domains
    - Adaptive scenario selection
    """
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/kb-enhanced",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.post("/api/v1/chat/kb-research", tags=["KB Chat"])
async def kb_research_chat(request: Request, auth: dict = Depends(get_current_auth_legacy)):
    """KB research with specialized knowledge agents"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/kb-research",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.post("/api/v1/chat/kb-gamemaster", tags=["KB Chat"])
async def kb_gamemaster_chat(request: Request, auth: dict = Depends(get_current_auth_legacy)):
    """Game mastering with KB-powered world knowledge"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/kb-gamemaster",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.post("/api/v1/chat/kb-development", tags=["KB Chat"])
async def kb_development_chat(request: Request, auth: dict = Depends(get_current_auth_legacy)):
    """Development guidance using KB codebase knowledge"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/kb-development",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.post("/api/v1/chat/kb-search", tags=["KB Chat"])
async def kb_search_chat(request: Request, auth: dict = Depends(get_current_auth_legacy)):
    """Direct KB search interface"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/kb-search",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.post("/api/v1/chat/kb-context", tags=["KB Chat"])
async def kb_context_chat(request: Request, auth: dict = Depends(get_current_auth_legacy)):
    """KOS context loading interface"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/kb-context",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.post("/api/v1/chat/kb-multitask", tags=["KB Chat"])
async def kb_multitask_chat(request: Request, auth: dict = Depends(get_current_auth_legacy)):
    """Parallel KB task execution"""
    body = await request.json()
    body["_auth"] = auth
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/kb-multitask",
        method="POST",
        json_data=body,
        headers=headers
    )

# ========================================================================================
# PERFORMANCE MONITORING ENDPOINTS - Operational insights and system health
# ========================================================================================

@app.get("/api/v0.2/performance/summary", tags=["v0.2 Performance"])
async def v0_2_get_performance_summary(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get overall performance summary with request statistics"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/performance/summary",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/performance/providers", tags=["v0.2 Performance"])
async def v0_2_get_provider_performance(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get performance metrics for all LLM providers"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/performance/providers",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/performance/stages", tags=["v0.2 Performance"])
async def v0_2_get_stage_timing_analysis(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get timing analysis for different request processing stages"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/performance/stages",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/performance/live", tags=["v0.2 Performance"])
async def v0_2_get_live_metrics(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get real-time metrics for currently active requests"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/performance/live",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v0.2/performance/health", tags=["v0.2 Performance"])
async def v0_2_get_performance_health(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get performance health indicators and alerts"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/performance/health",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.delete("/api/v0.2/performance/reset", tags=["v0.2 Performance"])
async def v0_2_reset_performance_metrics(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Reset/clear historical performance data"""
    return await forward_request_to_service(
        service_name="chat",
        path="/api/v0.2/performance/reset",
        method="DELETE",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

# ========================================================================================
# API v1 ENDPOINTS - Maintain LLM Platform compatibility
# ========================================================================================

# Chat endpoints - forward to chat service
@app.post("/api/v1/chat", tags=["Chat"])
async def chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Main chat endpoint used by all clients."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/",  # Route to chat endpoint
        method="POST",
        json_data=body,
        headers=headers
    )

@app.post("/api/v1/chat/completions", tags=["Chat"])
async def chat_completions(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """OpenAI-compatible chat completions endpoint."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/",  # Route to chat endpoint
        method="POST",
        json_data=body,
        headers=headers
    )

@app.get("/api/v1/chat/status", tags=["Chat"])
async def chat_status(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get chat history status."""
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/status",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.delete("/api/v1/chat/history", tags=["Chat"])
async def clear_chat_history(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Clear chat history."""
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/history",
        method="DELETE",
        headers=dict(request.headers)
    )

@app.post("/api/v1/chat/reload-prompt", tags=["Chat"])
async def reload_prompt(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Reload system prompt."""
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/reload-prompt",
        method="POST",
        headers=dict(request.headers)
    )

@app.get("/api/v1/chat/personas", tags=["Chat"])
async def get_personas(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward persona requests to chat service."""
    return await forward_request_to_service(
        service_name="chat",
        path="/personas/",  # Add trailing slash to match FastAPI routing
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.post("/api/v1/chat/mcp-agent", tags=["Chat"])
async def mcp_agent_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward MCP-agent chat requests to chat service."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/mcp-agent",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/direct", tags=["Chat"])
async def direct_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward direct chat requests to chat service (no framework overhead)."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/direct",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/mcp-agent-hot", tags=["Chat"])
async def mcp_agent_hot_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward hot-loaded MCP-agent chat requests to chat service."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/mcp-agent-hot",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/direct-db", tags=["Chat"])
async def direct_db_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward direct chat with DB requests to chat service."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/direct-db",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/orchestrated", tags=["Chat"])
async def orchestrated_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward orchestrated chat requests to chat service."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/orchestrated",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/ultrafast", tags=["Chat"])
async def ultrafast_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward ultrafast chat requests to chat service."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/ultrafast",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/ultrafast-redis", tags=["Chat"])
async def ultrafast_redis_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward ultrafast Redis chat requests to chat service."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/ultrafast-redis",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/ultrafast-redis-v2", tags=["Chat"])
async def ultrafast_redis_v2_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward optimized ultrafast Redis chat requests to chat service."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/ultrafast-redis-v2",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/ultrafast-redis-v3", tags=["Chat"])
async def ultrafast_redis_v3_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward parallel ultrafast Redis chat requests to chat service."""
    body = await request.json()
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/ultrafast-redis-v3",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/gamemaster", tags=["Chat"])
async def gamemaster_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Game Master orchestrating multiple NPCs for interactive scenes."""
    body = await request.json()
    
    # Remove content-length headers to prevent issues
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/gamemaster",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/worldbuilding", tags=["Chat"])
async def worldbuilding_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Collaborative world building with specialist agents."""
    body = await request.json()
    
    # Remove content-length headers to prevent issues
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/worldbuilding",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/storytelling", tags=["Chat"])
async def storytelling_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Multi-perspective storytelling with different narrative viewpoints."""
    body = await request.json()
    
    # Remove content-length headers to prevent issues
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/storytelling",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/problemsolving", tags=["Chat"])
async def problemsolving_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Expert team collaboration for complex problem solving."""
    body = await request.json()
    
    # Remove content-length headers to prevent issues
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/problemsolving",
        method="POST",
        headers=headers,
        json_data=body
    )

@app.post("/api/v1/chat/personas", tags=["Chat"])
async def create_persona(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward persona creation to chat service."""
    body = await request.json()
    body["_auth"] = auth
    
    return await forward_request_to_service(
        service_name="chat",
        path="/personas",
        method="POST",
        json_data=body,
        headers=dict(request.headers)
    )

# Asset endpoints - forward to asset service
@app.get("/api/v1/assets", tags=["Assets"])
async def get_assets(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward asset requests to asset service."""
    return await forward_request_to_service(
        service_name="asset",
        path="/assets/",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.post("/api/v1/assets/generate", tags=["Assets"])
async def generate_asset(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward asset generation to asset service."""
    body = await request.json()
    body["_auth"] = auth
    
    # Remove problematic headers that could cause content-length issues
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="asset",
        path="/assets/request",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.get("/api/v1/assets/test", tags=["Assets"])
async def test_assets(request: Request):
    """Forward asset test endpoint (no auth required)."""
    return await forward_request_to_service(
        service_name="asset",
        path="/assets/test",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v1/assets/{asset_id}", tags=["Assets"])
async def get_asset(
    asset_id: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward asset retrieval to asset service."""
    return await forward_request_to_service(
        service_name="asset",
        path=f"/assets/{asset_id}",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

# Auth endpoints - forward to auth service
@app.post("/api/v1/auth/validate", tags=["Authentication"])
async def validate_auth(request: Request):
    """Forward auth validation to auth service."""
    body = await request.json()
    
    return await forward_request_to_service(
        service_name="auth",
        path="/auth/validate",
        method="POST",
        json_data=body,
        headers=dict(request.headers)
    )

@app.post("/api/v1/auth/refresh", tags=["Authentication"])
async def refresh_auth(request: Request):
    """Forward auth refresh to auth service."""
    body = await request.json()
    
    return await forward_request_to_service(
        service_name="auth",
        path="/auth/refresh",
        method="POST",
        json_data=body,
        headers=dict(request.headers)
    )

@app.post("/api/v1/auth/register", tags=["Authentication"])
async def register_user(request: Request):
    """Forward user registration to auth service."""
    body = await request.json()
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="auth",
        path="/auth/register",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.post("/api/v1/auth/login", tags=["Authentication"])
async def login_user(request: Request):
    """Forward user login to auth service."""
    body = await request.json()
    
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="auth",
        path="/auth/login",
        method="POST",
        json_data=body,
        headers=headers
    )

# Filesystem endpoints - forward to chat service (MCP handles filesystem)
@app.get("/api/v1/filesystem", tags=["Filesystem"])
async def list_files(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward filesystem requests to chat service (MCP)."""
    return await forward_request_to_service(
        service_name="chat",
        path="/filesystem",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.post("/api/v1/filesystem/read", tags=["Filesystem"])
async def read_file(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward file read requests to chat service (MCP)."""
    body = await request.json()
    body["_auth"] = auth
    
    return await forward_request_to_service(
        service_name="chat",
        path="/filesystem/read",
        method="POST",
        json_data=body,
        headers=dict(request.headers)
    )

# ========================================================================================
# LEGACY ENDPOINTS - For backward compatibility
# ========================================================================================

# Legacy calculator endpoint (from original LLM Platform)
@app.post("/calculator/add", tags=["Calculator"])
async def calculator_add(request: Request):
    """Legacy calculator endpoint for backward compatibility."""
    body = await request.json()
    a = body.get("a", 0)
    b = body.get("b", 0)
    return {"result": a + b}

# ========================================================================================
# V1 AUTHENTICATION API
# ========================================================================================

@app.post("/api/v1/auth/login", tags=["v1 Authentication"])
async def v1_login(request: Request):
    """User login via Supabase - for web interface"""
    try:
        body = await request.json()
        
        # Forward to auth service
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("Content-Length", None)
        
        return await forward_request_to_service(
            service_name="auth",
            path="/auth/login",
            method="POST",
            json_data=body,
            headers=headers
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/auth/register", tags=["v1 Authentication"])
async def v1_register(request: Request):
    """User registration via Supabase - for web interface"""
    try:
        body = await request.json()
        
        # Forward to auth service
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("Content-Length", None)
        
        return await forward_request_to_service(
            service_name="auth",
            path="/auth/register",
            method="POST",
            json_data=body,
            headers=headers
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/auth/refresh", tags=["v1 Authentication"])
async def v1_refresh(request: Request):
    """Refresh JWT token"""
    try:
        body = await request.json()
        
        # Forward to auth service
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("Content-Length", None)
        
        return await forward_request_to_service(
            service_name="auth",
            path="/auth/refresh",
            method="POST",
            json_data=body,
            headers=headers
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/auth/logout", tags=["v1 Authentication"])
async def v1_logout(request: Request):
    """User logout"""
    try:
        # Forward to auth service
        headers = dict(request.headers)
        
        return await forward_request_to_service(
            service_name="auth",
            path="/auth/logout",
            method="POST",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/auth/confirm", tags=["v1 Authentication"])
async def v1_confirm_email(request: Request):
    """Email confirmation"""
    try:
        # Forward to auth service
        headers = dict(request.headers)
        body = await request.json()
        
        return await forward_request_to_service(
            service_name="auth",
            path="/auth/confirm",
            method="POST",
            headers=headers,
            json_data=body
        )
    except Exception as e:
        logger.error(f"Email confirmation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/auth/resend-verification", tags=["v1 Authentication"])
async def v1_resend_verification(request: Request):
    """Resend email verification"""
    try:
        # Forward to auth service
        headers = dict(request.headers)
        body = await request.json()
        
        return await forward_request_to_service(
            service_name="auth",
            path="/auth/resend-verification",
            method="POST",
            headers=headers,
            json_data=body
        )
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================================================================================
# SERVICE COORDINATION AND LIFECYCLE
# ========================================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize gateway service and connections."""
    log_service_startup("gateway", "0.2", settings.SERVICE_PORT)
    
    # Initialize NATS connection
    try:
        logger.info("Initializing NATS connection for service coordination with IP address")
        nats_client = await ensure_nats_connection()
        logger.nats("Connected to NATS for service coordination")
        
        # Publish gateway startup event
        startup_event = ServiceHealthEvent(
            service_name="gateway",
            status="starting",
            timestamp=datetime.now()
        )
        await nats_client.publish(NATSSubjects.SERVICE_HEALTH, startup_event.model_dump_json())
        
    except Exception as e:
        logger.error(f"Failed to initialize NATS connection: {e}")
        # Don't fail startup - gateway can work without NATS
    
    # Test connections to all services
    for service_name, service_url in SERVICE_URLS.items():
        try:
            client = await get_http_client()
            response = await client.get(f"{service_url}/health", timeout=5.0)
            if response.status_code == 200:
                logger.lifecycle(f"Connected to {service_name} service")
            else:
                logger.warning(f"{service_name} service health check failed")
        except Exception as e:
            logger.warning(f"Could not connect to {service_name} service: {e}")
    
    # Publish gateway ready event
    try:
        nats_client = await ensure_nats_connection()
        ready_event = ServiceHealthEvent(
            service_name="gateway",
            status="healthy",
            timestamp=datetime.now()
        )
        await nats_client.publish(NATSSubjects.SERVICE_READY, ready_event.model_dump_json())
        logger.lifecycle("Gateway service ready and published to NATS")
        
    except Exception as e:
        logger.warning(f"Could not publish ready event to NATS: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    log_service_shutdown("gateway")
    
    # Close HTTP client
    global http_client
    if http_client:
        await http_client.aclose()
    
    # Publish shutdown event to NATS
    try:
        nats_client = await ensure_nats_connection()
        shutdown_event = ServiceHealthEvent(
            service_name="gateway",
            status="stopping",
            timestamp=datetime.now()
        )
        await nats_client.publish(NATSSubjects.SERVICE_HEALTH, shutdown_event.model_dump_json())
        await nats_client.disconnect()
        
    except Exception as e:
        logger.warning(f"Could not publish shutdown event to NATS: {e}")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming HTTP requests."""
    start_time = datetime.now()
    logger.network(f"{request.method} {request.url.path}")
    
    response = await call_next(request)
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.network(f"Response: {response.status_code} ({duration:.3f}s)")
    
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with error logging."""
    logger.error(f"Unhandled exception in gateway: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.gateway.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )
