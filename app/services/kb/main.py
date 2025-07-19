"""
KB Service - Knowledge Base Integration Service

Provides MCP tools for Knowledge Base access:
- Direct file system search and reading
- Context loading and management
- Cross-domain synthesis
- Multi-agent task delegation
"""

from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
import logging

from app.shared import (
    settings,
    configure_logging_for_service,
    log_service_startup,
    log_service_shutdown,
    get_current_auth_legacy as get_current_auth,
    ensure_nats_connection,
    NATSSubjects,
    ServiceHealthEvent
)
from app.shared.config import settings as config_settings
from app.shared.redis_client import redis_client
from app.models.chat import ChatRequest
from .kb_service import (
    kb_search_endpoint,
    kb_context_loader_endpoint,
    kb_multi_task_endpoint,
    kb_navigate_index_endpoint,
    kb_synthesize_contexts_endpoint,
    kb_get_threads_endpoint,
    kb_read_file_endpoint,
    kb_list_directory_endpoint
)

# Configure logging
logger = configure_logging_for_service("kb")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    log_service_startup("kb", "1.0", settings.SERVICE_PORT)
    
    # Initialize NATS connection for service coordination
    try:
        nats_client = await ensure_nats_connection()
        logger.info("Connected to NATS for service coordination")
        
        # Publish service startup event
        startup_event = ServiceHealthEvent(
            service_name="kb",
            status="starting",
            timestamp=datetime.now()
        )
        await nats_client.publish(NATSSubjects.SERVICE_HEALTH, startup_event.model_dump_json())
    except Exception as e:
        logger.warning(f"Could not connect to NATS: {e}")
    
    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Connected to Redis for caching")
    except Exception as e:
        logger.warning(f"Redis not available, caching disabled: {e}")
    
    yield
    
    # Shutdown
    log_service_shutdown("kb")
    
    # Publish shutdown event
    try:
        nats_client = await ensure_nats_connection()
        shutdown_event = ServiceHealthEvent(
            service_name="kb",
            status="stopping",
            timestamp=datetime.now()
        )
        await nats_client.publish(NATSSubjects.SERVICE_HEALTH, shutdown_event.model_dump_json())
        await nats_client.disconnect()
    except Exception as e:
        logger.warning(f"Could not publish shutdown event: {e}")

# Create FastAPI app
app = FastAPI(
    title="KB Service",
    description="Knowledge Base integration service for Gaia Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "service": "kb",
        "status": "healthy",
        "version": "1.0.0",
        "kb_path": getattr(config_settings, 'KB_PATH', '/kb'),
        "kb_enabled": getattr(config_settings, 'KB_MCP_ENABLED', True)
    }

# KB Endpoints
@app.post("/search")
async def kb_search(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Search KB using ripgrep for fast full-text search.
    
    The message field contains the search query.
    """
    return await kb_search_endpoint(request, auth)

@app.post("/context")
async def kb_load_context(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Load a KOS context by name.
    
    The message field contains the context name (e.g., 'gaia', 'mmoirl').
    """
    return await kb_context_loader_endpoint(request, auth)

@app.post("/multitask")
async def kb_multitask(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Execute multiple KB tasks in parallel.
    
    The message field contains task descriptions.
    """
    return await kb_multi_task_endpoint(request, auth)

@app.post("/navigate")
async def kb_navigate_index(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Navigate KB using the manual index system.
    
    The message field contains the starting path (default: '/').
    """
    return await kb_navigate_index_endpoint(request, auth)

@app.post("/synthesize")
async def kb_synthesize(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Synthesize insights across multiple contexts.
    
    The message field contains comma-separated context names.
    """
    return await kb_synthesize_contexts_endpoint(request, auth)

@app.post("/threads")
async def kb_get_threads(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Get active KOS threads.
    
    The message field can contain filter criteria.
    """
    return await kb_get_threads_endpoint(request, auth)

@app.post("/read")
async def kb_read_file(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Read a specific KB file.
    
    The message field contains the file path.
    """
    return await kb_read_file_endpoint(request, auth)

@app.post("/list")
async def kb_list_directory(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    List files in a KB directory.
    
    The message field contains the directory path.
    """
    return await kb_list_directory_endpoint(request, auth)

# Add v0.2 API compatibility router if needed
from .v0_2_api import router as v0_2_router
app.include_router(v0_2_router, prefix="/api/v0.2")
logger.info("✅ v0.2 API router included for KB service")

from datetime import datetime

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.services.kb.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )