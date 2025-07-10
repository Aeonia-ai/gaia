"""
Gaia Chat Service - Multi-Provider LLM Orchestration
Handles chat completions, streaming, personas, and MCP tool integration.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.shared.config import settings
from app.shared.logging import configure_logging_for_service, logger
from app.shared.database import engine, Base
from app.shared.nats_client import NATSClient

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
    await nats_client.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Gaia Chat Service",
    description="Multi-provider LLM orchestration with MCP tool integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "chat",
        "status": "healthy",
        "version": "1.0.0",
        "database": {"status": "connected"},
        "nats": {"status": "connected" if nats_client.is_connected else "disconnected"}
    }

# Import and include routers
try:
    from .chat import router as chat_router
    app.include_router(chat_router, prefix="")  # No prefix since we're calling /chat directly
    logger.info("✅ Chat router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import chat router: {e}")

# Include personas router
try:
    from .personas import router as personas_router
    app.include_router(personas_router, prefix="/personas")
    logger.info("✅ Personas router included")
except ImportError as e:
    logger.warning(f"⚠️ Could not import personas router: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
