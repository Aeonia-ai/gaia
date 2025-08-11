"""
Gaia Chat Service - Multi-Provider LLM Orchestration
Handles chat completions, streaming, personas, and MCP tool integration.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.shared.config import settings
from app.shared.logging import configure_logging_for_service, logger
from app.shared.database import engine, Base
from app.shared.nats_client import NATSClient
from app.shared.service_discovery import create_service_health_endpoint

# Setup logging
configure_logging_for_service("chat")

# NATS client for service coordination
nats_client = NATSClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting Chat Service...")
    
    # Initialize database
    Base.metadata.create_all(bind=engine)
    
    # Connect to NATS
    await nats_client.connect()
    
    # Initialize multiagent orchestrator with hot loading
    try:
        from .multiagent_orchestrator import multiagent_orchestrator
        await multiagent_orchestrator.initialize()
        logger.info("✅ Multiagent orchestrator initialized with hot loading")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize multiagent orchestrator: {e}")
    
    # Initialize hot chat service if available
    try:
        from .lightweight_chat_hot import hot_chat_service
        await hot_chat_service.initialize()
        logger.info("✅ Hot chat service initialized")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize hot chat service: {e}")
    
    # Publish service ready event
    await nats_client.publish(
        "gaia.service.ready",
        {
            "service": "chat",
            "status": "ready",
            "timestamp": "2025-01-01T00:00:00Z"
        }
    )
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Chat Service...")
    
    # Cleanup multiagent orchestrator
    try:
        from .multiagent_orchestrator import multiagent_orchestrator
        await multiagent_orchestrator.cleanup()
    except Exception as e:
        logger.warning(f"⚠️ Error cleaning up multiagent orchestrator: {e}")
    
    # Cleanup hot chat service
    try:
        from .lightweight_chat_hot import hot_chat_service
        await hot_chat_service.cleanup()
    except Exception as e:
        logger.warning(f"⚠️ Error cleaning up hot chat service: {e}")
    
    await nats_client.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Gaia Chat Service",
    description="Multi-provider LLM orchestration with MCP tool integration",
    version="0.2",
    lifespan=lifespan
)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
try:
    from .chat import router as chat_router
    app.include_router(chat_router, prefix="/chat")  # Chat endpoints under /chat prefix
    logger.info("✅ Chat router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import chat router: {e}")

# Include v0.2 chat-specific routes only
try:
    from app.api.v0_2.endpoints import chat as v0_2_chat
    app.include_router(v0_2_chat.router, prefix="/api/v0.2")
    logger.info("✅ v0.2 chat routes included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import v0.2 chat routes: {e}")

# Include conversation management router
try:
    from .conversations import router as conversations_router
    app.include_router(conversations_router, prefix="")  # No prefix for direct /conversations endpoints
    logger.info("✅ Conversations router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import conversations router: {e}")

# Include personas router
try:
    from .personas import router as personas_router
    app.include_router(personas_router, prefix="/personas")
    logger.info("✅ Personas router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import personas router: {e}")

# Create enhanced health endpoint with route discovery AFTER all routers are included
create_service_health_endpoint(app, "chat", "0.2")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
