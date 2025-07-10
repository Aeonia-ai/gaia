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
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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

# Configure logging for gateway service
logger = configure_logging_for_service("gateway")

# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address)

# FastAPI application
app = FastAPI(
    title="LLM Platform", 
    description="AI-powered language model API with multi-provider support",
    version="0.2.0"
)

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
    
    overall_status = "healthy"
    if any(s["status"] != "healthy" for s in service_health.values()):
        overall_status = "degraded"
    if db_health["status"] != "healthy":
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": "0.2.0"
    }

# Root endpoint (same as LLM Platform)
@app.get("/")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}")
async def root(request: Request):
    """Root endpoint handler with rate limiting."""
    logger.input("Received request to root endpoint")
    return {
        "message": "LLM Platform is running",
        "versions": {
            "v0.2": "Stable - Multi-provider chat completions",
            "v1": "Latest - Enhanced features and compatibility"
        },
        "version": "0.2.0",
        "timestamp": datetime.now().isoformat()
    }

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
        path="/chat",  # Route to chat endpoint
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
        path="/chat",  # Route to chat endpoint
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
        path="/status",
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
        path="/history",
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
        path="/reload-prompt",
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
        path="/assets",
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
    
    return await forward_request_to_service(
        service_name="asset",
        path="/assets/generate",
        method="POST",
        json_data=body,
        headers=dict(request.headers)
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
# SERVICE COORDINATION AND LIFECYCLE
# ========================================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize gateway service and connections."""
    log_service_startup("gateway", "1.0.0", settings.SERVICE_PORT)
    
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
