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
from fastapi.responses import JSONResponse, StreamingResponse, Response
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
    get_current_auth_unified,
    ensure_nats_connection,
    NATSSubjects,
    ServiceHealthEvent,
    database_health_check,
    supabase_health_check
)
from app.shared.redis_client import redis_client, CacheManager
from app.gateway.cache_middleware import CacheMiddleware
from app.services.gateway.routes.locations_endpoints import router as locations_router

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
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
            return f"user:jwt:{token_hash}"
        elif api_key:
            # Use API key hash for service rate limiting
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:32]
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
# TODO: Fix Content-Length issue with CacheMiddleware
# app.add_middleware(CacheMiddleware)

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

# Register modular routers
app.include_router(locations_router)

# Service URL configuration
SERVICE_URLS = {
    "auth": settings.AUTH_SERVICE_URL,
    "asset": settings.ASSET_SERVICE_URL,
    "chat": settings.CHAT_SERVICE_URL,
    "kb": settings.KB_SERVICE_URL
}

# HTTP client for service communication
http_client: Optional[httpx.AsyncClient] = None

async def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client for service communication."""
    global http_client
    if http_client is None:
        # Configure client to handle compressed responses
        # httpx[brotli] handles all compression types including Brotli
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.GATEWAY_REQUEST_TIMEOUT),
            # Let httpx handle all compression types automatically
            headers={
                "User-Agent": "GaiaGateway/1.0"
            }
        )
    return http_client

async def forward_request_to_service(
    service_name: str,
    path: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    stream: bool = False
):
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
        
        # Check if this request expects a streaming response
        is_streaming_request = (
            stream or 
            (json_data and json_data.get("stream") is True) or
            path.endswith("/stream")
        )
        
        if is_streaming_request:
            # For streaming requests, we need to handle the response carefully
            # to avoid closing the stream prematurely
            logger.service(f"Detected streaming request to {service_name}")
            
            # Make the streaming request
            response = await client.request(
                method=method,
                url=full_url,
                headers=headers,
                params=params,
                json=json_data,
                files=files,
                extensions={"stream": True}
            )
            
            # Check status before proceeding
            if response.status_code >= 400:
                # Handle error responses
                error_text = response.text
                logger.error(f"Service {service_name} returned error {response.status_code}: {error_text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Service error: {error_text}"
                )
            
            # Check if it's actually a streaming response
            content_type = response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                logger.service(f"Forwarding SSE stream from {service_name}")
                
                # Stream the response directly without any modification
                async def stream_generator():
                    try:
                        # Use aiter_bytes() for raw pass-through to preserve SSE event boundaries
                        # This ensures tokens are never split and SSE format remains intact
                        async for chunk in response.aiter_bytes():
                            yield chunk
                    except httpx.StreamClosed:
                        logger.warning(f"Stream from {service_name} closed unexpectedly")
                    finally:
                        await response.aclose()
                
                return StreamingResponse(
                    stream_generator(),
                    media_type=content_type,
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no"
                    }
                )
            else:
                # Not actually streaming, read the full response
                logger.service(f"Non-streaming response from {service_name} (content-type: {content_type})")
                content = response.content
                if content_type.startswith("application/json"):
                    return response.json()
                else:
                    return Response(content=content, media_type=content_type)
        else:
            # Non-streaming request
            response = await client.request(
                method=method,
                url=full_url,
                headers=headers,
                params=params,
                json=json_data,
                files=files
            )
            
            # Handle error status codes before raise_for_status()
            if response.status_code == 404:
                # Pass through 404 errors as-is (e.g., conversation not found)
                try:
                    error_data = response.json()
                    raise HTTPException(status_code=404, detail=error_data.get("detail", "Not found"))
                except Exception:
                    raise HTTPException(status_code=404, detail="Not found")
            
            response.raise_for_status()
            
            # Handle 204 No Content responses (no body expected)
            if response.status_code == 204:
                return Response(status_code=204)
            
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
        
        # Pass through 404 errors without wrapping them
        if e.response.status_code == 404:
            try:
                error_data = e.response.json()
                raise HTTPException(status_code=404, detail=error_data.get("detail", "Not found"))
            except Exception:
                raise HTTPException(status_code=404, detail="Not found")
        
        # For other errors, wrap them as service errors
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
    
    # Use a single HTTP client for all service checks
    client = await get_http_client()
    for service_name, service_url in SERVICE_URLS.items():
        try:
            response = await client.get(f"{service_url}/health", timeout=15.0)
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
            "v1": "/api/v1 (original endpoints)",
            "v0.3": "/api/v0.3 (clean API without provider details)"
        },
        "note": "Use v0.3 for the clean, simplified API or v1 for OpenAI compatibility."
    }

# ========================================================================================
# API v0.2 ENDPOINTS REMOVED - Use v1 or v0.3 APIs instead
# ========================================================================================
# 
# The v0.2 API has been deprecated and removed. Please use:
# - v1 API: /api/v1/* - Original LLM Platform compatible API
# - v0.3 API: /api/v0.3/* - Clean simplified API without provider details
#
# Both v1 and v0.3 APIs route through the unified intelligent chat system.
# ========================================================================================

# ========================================================================================
# REMOVED ENDPOINT CATEGORIES:
# ========================================================================================
# The following v0.2 endpoint categories have been removed:
# - Asset Pricing & Cost Management 
# - Usage Tracking & Billing
# - Persona Management
# - Performance Monitoring
# - Knowledge Base Management
#
# These features may be available through v1 or v0.3 APIs where applicable.
# ========================================================================================

# ========================================================================================
# API v1 ENDPOINTS - Maintain LLM Platform compatibility
# ========================================================================================

# Chat endpoints - forward to chat service
@app.post("/api/v1/chat", tags=["Chat"])
async def chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """
    Main chat endpoint used by all clients - now with unified intelligent routing.
    
    Accepts:
    - message: The chat message (string)
    - messages: Array of message objects (OpenAI format)
    - conversation_id: Optional conversation ID for context continuity
    - stream: Whether to stream the response
    """
    body = await request.json()
    
    # Convert OpenAI format to unified format if needed
    if "messages" in body and isinstance(body["messages"], list):
        # Extract the last user message
        last_message = ""
        for msg in reversed(body["messages"]):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break
        body["message"] = last_message
        # Keep messages for context but unified chat expects 'message'
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/unified",  # Route to unified intelligent chat endpoint
        method="POST",
        json_data=body,
        headers=headers,
        stream=body.get("stream", False)  # Support streaming
    )


@app.delete("/api/v1/conversations/{conversation_id}", tags=["Chat"])
async def delete_conversation(
    conversation_id: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """
    Delete a specific conversation.
    
    Useful for testing personas and starting fresh conversations during development.
    """
    # For DELETE requests, we need to ensure auth is passed through headers
    headers = dict(request.headers)
    
    # The chat service will extract auth from the headers
    return await forward_request_to_service(
        service_name="chat",
        path=f"/conversations/{conversation_id}",
        method="DELETE",
        headers=headers
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

# ========================================================================================
# v1 Conversation Management
# ========================================================================================

@app.post("/api/v1/conversations", tags=["Conversations"], status_code=201)
async def create_conversation_v1(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Create a new conversation."""
    body = await request.json() if request.body else {}
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    # Proxy to chat service conversation endpoint
    return await forward_request_to_service(
        service_name="chat",
        path="/conversations",
        method="POST",
        json_data=body,
        headers=headers
    )

@app.get("/api/v1/conversations/{conversation_id}", tags=["Conversations"])
async def get_conversation_v1(
    conversation_id: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get a specific conversation."""
    # Proxy to chat service conversation endpoint
    return await forward_request_to_service(
        service_name="chat",
        path=f"/conversations/{conversation_id}",
        method="GET",
        headers=dict(request.headers)
    )

@app.get("/api/v1/conversations", tags=["Conversations"])
async def list_conversations_v1(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """List user's conversations."""
    # Proxy to chat service conversation endpoint
    return await forward_request_to_service(
        service_name="chat",
        path="/conversations",
        method="GET",
        headers=dict(request.headers)
    )

@app.get("/api/v1/conversations/{conversation_id}/messages", tags=["Conversations"])
async def get_messages_v1(
    conversation_id: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get messages for a conversation."""
    # Proxy to chat service conversation endpoint
    return await forward_request_to_service(
        service_name="chat",
        path=f"/conversations/{conversation_id}/messages",
        method="GET",
        headers=dict(request.headers)
    )

@app.delete("/api/v1/conversations/{conversation_id}", tags=["Conversations"])
async def delete_conversation_v1(
    conversation_id: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Delete a conversation."""
    # Proxy to chat service conversation endpoint
    return await forward_request_to_service(
        service_name="chat",
        path=f"/conversations/{conversation_id}",
        method="DELETE",
        headers=dict(request.headers)
    )

# ========================================================================================
# v0.3 API - Clean Gaia Interface (No Provider Details Exposed)
# 
# Design principles:
# - Simple request/response format
# - No provider/model selection exposed to clients  
# - Server-side intelligence is completely hidden
# - Consistent streaming and non-streaming formats
# ========================================================================================

@app.post("/api/v0.3/chat", tags=["v0.3 Clean API"])
async def v03_chat(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """
    Clean v0.3 chat endpoint with no exposed provider details.
    
    Request format:
    {
        "message": "Your question here",
        "conversation_id": "optional-conversation-id",
        "stream": false  // optional, defaults to false
    }
    
    Response format (non-streaming):
    {
        "response": "AI response here"
    }
    
    Response format (streaming):
    Server-Sent Events with:
    {"type": "content", "content": "chunk"}
    {"type": "done"}
    """
    body = await request.json()
    
    # Validate required fields
    if "message" not in body:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required field: message"}
        )
    
    # Add authentication info to request
    body["_auth"] = auth
    
    # Mark this as v0.3 request for directive-enhanced responses
    body["response_format"] = "v0.3"
    
    # Remove content-length header since we modified the body
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    # Forward to chat service and get response
    chat_response = await forward_request_to_service(
        service_name="chat",
        path="/chat/unified",  # Use intelligent routing
        method="POST", 
        json_data=body,
        headers=headers,
        stream=body.get("stream", False)
    )
    
    # If streaming, return as-is but with clean format conversion
    if body.get("stream", False):
        return await _convert_to_clean_streaming_format(chat_response)
    
    # For non-streaming, convert to clean format
    if hasattr(chat_response, 'json'):
        response_data = await chat_response.json()
    else:
        response_data = chat_response
    
    # Convert to clean v0.3 format (remove provider details)
    clean_response = _convert_to_clean_format(response_data)
    
    return JSONResponse(content=clean_response)

@app.get("/api/v0.3/conversations", tags=["v0.3 Clean API"])
async def v03_list_conversations(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """
    List conversations with clean format.
    
    Response format:
    {
        "conversations": [
            {
                "conversation_id": "uuid",
                "title": "Conversation title",
                "created_at": "ISO timestamp"
            }
        ]
    }
    """
    # Forward to chat service conversations endpoint
    chat_response = await forward_request_to_service(
        service_name="chat",
        path="/conversations",
        method="GET",
        headers=dict(request.headers)
    )
    
    # Get response data
    if hasattr(chat_response, 'json'):
        response_data = await chat_response.json()
    else:
        response_data = chat_response
    
    # Convert to clean v0.3 format
    conversations = response_data.get("conversations", [])
    clean_conversations = []
    
    for conv in conversations:
        clean_conversations.append({
            "conversation_id": conv.get("id"),
            "title": conv.get("title", "New Conversation"),
            "created_at": conv.get("created_at")
        })
    
    clean_data = {
        "conversations": clean_conversations
    }
    
    return JSONResponse(content=clean_data)

@app.post("/api/v0.3/conversations", tags=["v0.3 Clean API"])
async def v03_create_conversation(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """
    Create a new conversation with clean format.
    
    Request format:
    {
        "title": "Optional conversation title"
    }
    
    Response format:
    {
        "conversation_id": "generated-uuid",
        "title": "Conversation title"
    }
    """
    body = await request.json()
    
    # Forward to chat service conversation creation endpoint
    chat_response = await forward_request_to_service(
        service_name="chat",
        path="/conversations",
        method="POST",
        json_data=body,
        headers=dict(request.headers)
    )
    
    # Get response data
    if hasattr(chat_response, 'json'):
        response_data = await chat_response.json()
    else:
        response_data = chat_response
    
    # Convert to clean v0.3 format
    clean_data = {
        "conversation_id": response_data.get("id"),
        "title": response_data.get("title", "New Conversation")
    }
    
    return JSONResponse(status_code=201, content=clean_data)


# v0.3 Authentication endpoints - same as v1, different paths
@app.post("/api/v0.3/auth/login", tags=["v0.3 Authentication"])
async def v03_auth_login(request: Request):
    """v0.3 auth login - same as v1, different path for API consistency."""
    return await v1_login(request)

@app.post("/api/v0.3/auth/register", tags=["v0.3 Authentication"])  
async def v03_auth_register(request: Request):
    """v0.3 auth register - same as v1, different path for API consistency."""
    return await v1_register(request)

@app.post("/api/v0.3/auth/logout", tags=["v0.3 Authentication"])
async def v03_auth_logout(request: Request):
    """v0.3 auth logout - same as v1, different path for API consistency."""
    return await v1_logout(request)

@app.post("/api/v0.3/auth/validate", tags=["v0.3 Authentication"])
async def v03_auth_validate(request: Request):
    """v0.3 auth validate - same as v1, different path for API consistency."""
    return await validate_auth(request)

@app.post("/api/v0.3/auth/refresh", tags=["v0.3 Authentication"])
async def v03_auth_refresh(request: Request):
    """v0.3 auth refresh - same as v1, different path for API consistency."""
    return await refresh_auth(request)

@app.post("/api/v0.3/auth/confirm", tags=["v0.3 Authentication"])
async def v03_auth_confirm(request: Request):
    """v0.3 auth confirm - same as v1, different path for API consistency."""
    return await v1_confirm(request)

@app.post("/api/v0.3/auth/resend-verification", tags=["v0.3 Authentication"])
async def v03_auth_resend_verification(request: Request):
    """v0.3 auth resend verification - same as v1, different path for API consistency."""
    return await v1_resend_verification(request)
def _convert_to_clean_format(response_data):
    """
    Convert any chat response to clean v0.3 format.
    Removes provider, model, reasoning, timing, and other internal details.
    Preserves conversation_id for conversation continuity.
    """
    if isinstance(response_data, dict):
        clean_response = {}
        
        # Extract response content based on format
        if "response" in response_data:
            # Already in simple format
            clean_response["response"] = response_data["response"]
        elif "choices" in response_data:
            # OpenAI format - extract content
            choices = response_data.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                content = message.get("content", "")
                clean_response["response"] = content
        elif "message" in response_data:
            # Direct message format
            clean_response["response"] = response_data["message"]
        else:
            # Fallback
            clean_response["response"] = str(response_data)
        
        # Preserve conversation_id if present
        if "_metadata" in response_data and "conversation_id" in response_data["_metadata"]:
            clean_response["conversation_id"] = response_data["_metadata"]["conversation_id"]
        elif "conversation_id" in response_data:
            clean_response["conversation_id"] = response_data["conversation_id"]
        
        return clean_response
    
    # Fallback - return as string
    return {"response": str(response_data)}

async def _convert_to_clean_streaming_format(streaming_response):
    """
    Convert streaming response to clean v0.3 format while preserving SSE boundaries.
    """
    from fastapi.responses import StreamingResponse
    import json
    
    async def clean_stream_generator():
        """Generate clean v0.3 streaming format with proper SSE handling."""
        if hasattr(streaming_response, 'body_iterator'):
            # Handle StreamingResponse - accumulate until we have complete SSE events
            buffer = ""
            
            async for chunk in streaming_response.body_iterator:
                if isinstance(chunk, bytes):
                    chunk = chunk.decode('utf-8')
                
                buffer += chunk
                
                # Process complete SSE events (separated by double newlines)
                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)
                    
                    if not event.strip():
                        continue
                    
                    # Parse the SSE event
                    if event.startswith("data: "):
                        data_str = event[6:].strip()
                        
                        if data_str == "[DONE]":
                            # Send clean done message
                            yield f"data: {json.dumps({'type': 'done'})}\n\n"
                            break
                        
                        try:
                            # Parse the chunk
                            chunk_data = json.loads(data_str)
                            
                            # Convert to clean format based on content type
                            if chunk_data.get("type") == "content":
                                # Already in our format, pass through
                                clean_chunk = {"type": "content", "content": chunk_data.get("content", "")}
                                yield f"data: {json.dumps(clean_chunk)}\n\n"
                            elif chunk_data.get("object") == "chat.completion.chunk":
                                # OpenAI format - extract content
                                choices = chunk_data.get("choices", [])
                                if choices and len(choices) > 0:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        clean_chunk = {"type": "content", "content": content}
                                        yield f"data: {json.dumps(clean_chunk)}\n\n"
                            elif "content" in chunk_data:
                                # Generic format with content field
                                clean_chunk = {"type": "content", "content": chunk_data["content"]}
                                yield f"data: {json.dumps(clean_chunk)}\n\n"
                            elif chunk_data.get("type") in ["model_selection", "metadata", "error"]:
                                # Pass through other event types
                                yield f"data: {json.dumps(chunk_data)}\n\n"
                        except json.JSONDecodeError:
                            # Skip malformed chunks
                            logger.warning(f"Malformed SSE data: {data_str[:100]}")
                            continue
                    else:
                        # Non-data event (like comments), pass through
                        yield f"{event}\n\n"
            
            # Process any remaining buffer content
            if buffer.strip() and buffer.startswith("data: "):
                data_str = buffer[6:].strip()
                if data_str == "[DONE]":
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
        else:
            # Fallback - return error message
            error_chunk = {"type": "content", "content": "Streaming not available"}
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        clean_stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
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

# Removed duplicate /api/v1/auth/login endpoint - see v1_login below

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

@app.post("/api/v1/auth/register", tags=["v1 Authentication"])
async def v1_register(request: Request):
    """User registration via Supabase - for web interface"""
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

@app.post("/api/v1/auth/refresh", tags=["v1 Authentication"])
async def v1_refresh(request: Request):
    """Refresh JWT token"""
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

@app.post("/api/v1/auth/logout", tags=["v1 Authentication"])
async def v1_logout(request: Request):
    """User logout"""
    # Forward to auth service
    headers = dict(request.headers)
    
    return await forward_request_to_service(
        service_name="auth",
        path="/auth/logout",
        method="POST",
        headers=headers
    )

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
            response = await client.get(f"{service_url}/health", timeout=15.0)
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
