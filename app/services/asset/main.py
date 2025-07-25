"""
Asset Service - Universal Asset Server
Handles asset generation, search, storage, and optimization
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from app.shared.config import settings
from app.shared.logging import get_logger
from app.shared.nats_client import NATSClient
from app.shared.database import engine as database_engine, test_database_connection
from app.shared.service_discovery import create_service_health_endpoint
from .router_minimal import assets_router

logger = get_logger(__name__)

# NATS client for service coordination
nats_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global nats_client
    
    # Startup
    logger.info("Starting Asset Service...")
    
    try:
        # Initialize NATS client
        nats_client = NATSClient()
        await nats_client.connect()
        logger.info("Connected to NATS")
        
        # Test database connection
        if test_database_connection():
            logger.info("Database connection verified")
        else:
            logger.warning("Database connection test failed")
        
        # Publish service ready event
        await nats_client.publish(
            "gaia.service.ready",
            {
                "service": "asset-service",
                "status": "ready",
                "capabilities": [
                    "asset_generation",
                    "asset_search", 
                    "asset_upload",
                    "cost_optimization"
                ]
            }
        )
        
        logger.info("Asset Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Asset Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Asset Service...")
    
    try:
        if nats_client:
            await nats_client.disconnect()
            logger.info("NATS connection closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("Asset Service shutdown complete")

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title="Gaia Asset Service",
        description="Universal Asset Server - Generation, Search, and Optimization",
        version="0.2",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(assets_router)
    
    # Create enhanced health endpoint with route discovery
    create_service_health_endpoint(app, "asset", "0.2")
    
    @app.get("/")
    async def root():
        """Service info"""
        return {
            "service": "Gaia Asset Service",
            "version": "0.2",
            "description": "Universal Asset Server for AI-generated and community assets",
            "endpoints": {
                "assets": "/api/v1/assets",
                "health": "/health",
                "docs": "/docs"
            }
        }
    
    return app

# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )