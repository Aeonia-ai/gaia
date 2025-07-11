from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import time
from datetime import datetime

from .models.asset import (
    AssetRequest,
    AssetResponse, 
    AssetMetadata,
    AssetUploadResponse,
    AssetSearchResult
)
# Temporarily comment out service imports to get basic service running
# from .asset_search_service import AssetSearchService
# from .storage_service import SupabaseStorageService  
# from .generation_service import AIGenerationService
# from .cost_optimizer import CostOptimizer
from app.shared.security import get_current_auth_legacy
from app.shared.logging import get_logger
# from .pricing_router import pricing_router
# from .cost_estimator import cost_estimator_router

logger = get_logger(__name__)
assets_router = APIRouter(prefix="/assets", tags=["Assets"])

# Include sub-routers (temporarily disabled)
# assets_router.include_router(pricing_router)
# assets_router.include_router(cost_estimator_router)


@assets_router.get("/test")
async def test_endpoint():
    """Test endpoint to verify service is running"""
    return {
        "status": "ok",
        "service": "asset-service",
        "message": "Asset service is running",
        "timestamp": datetime.utcnow().isoformat()
    }


@assets_router.post("/request")
async def request_asset(
    request: AssetRequest,
    current_auth = Depends(get_current_auth_legacy)
):
    """
    Main asset request endpoint (temporarily simplified)
    TODO: Implement full asset generation pipeline once services are fixed
    """
    start_time = time.time()
    
    try:
        logger.info(f"Asset request received: {request.category.value} - {request.style} - {request.description[:100]}...")
        
        # Temporary response for testing
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": "placeholder", 
            "message": "Asset service endpoint working - implementation in progress",
            "request_category": request.category.value,
            "request_style": request.style,
            "response_time_ms": response_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Asset request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Asset request failed: {str(e)}")


# Temporarily disabled complex endpoints
# TODO: Re-enable once all service dependencies are fixed

# @assets_router.post("/upload", response_model=AssetUploadResponse)
async def upload_community_asset(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    style_tags: str = Form(""),  # Comma-separated tags
    current_auth = Depends(get_current_auth_legacy)
):
    """
    Community asset contribution endpoint:
    1. Validate file type and size
    2. Upload to Supabase Storage (community/ folder)
    3. Generate embeddings for semantic search
    4. Store metadata in database
    5. Make available for future requests
    """
    try:
        logger.info(f"Community asset upload: {title} ({category})")
        
        # Initialize storage service
        storage_service = SupabaseStorageService()
        
        # Validate file
        if file.size > storage_service.max_file_size_bytes:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {storage_service.max_file_size_bytes // (1024*1024)}MB"
            )
        
        # Parse style tags
        parsed_tags = [tag.strip() for tag in style_tags.split(",") if tag.strip()]
        
        # Upload file
        upload_result = await storage_service.upload_community_asset(
            file_data=await file.read(),
            filename=file.filename,
            category=category,
            metadata={
                "title": title,
                "description": description,
                "style_tags": parsed_tags,
                "uploader": str(current_auth),  # User identifier
                "uploaded_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Community asset uploaded successfully: {upload_result.asset_id}")
        
        return upload_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Asset upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@assets_router.get("/search", response_model=List[AssetMetadata])
async def search_assets(
    category: str,
    query: str,
    style_tags: Optional[str] = None,
    limit: int = 20,
    current_auth = Depends(get_current_auth_legacy)
):
    """
    Direct asset database search with semantic similarity
    """
    try:
        logger.info(f"Asset search: {category} - {query}")
        
        # Initialize search service
        search_service = AssetSearchService()
        
        # Parse style tags
        parsed_tags = []
        if style_tags:
            parsed_tags = [tag.strip() for tag in style_tags.split(",") if tag.strip()]
        
        # Perform search
        results = await search_service.search_database_assets(
            category=category,
            description=query,
            style_tags=parsed_tags,
            limit=limit
        )
        
        # Convert to metadata format
        metadata_results = [
            AssetMetadata(
                id=asset.id,
                category=asset.category,
                title=asset.title,
                description=asset.description,
                style_tags=asset.style_tags,
                quality_score=asset.quality_score,
                download_count=asset.download_count,
                license_type=asset.license_type,
                attribution_required=asset.attribution_required,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
                metadata=asset.metadata
            )
            for asset in results
        ]
        
        logger.info(f"Asset search completed: {len(metadata_results)} results")
        
        return metadata_results
        
    except Exception as e:
        logger.error(f"Asset search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@assets_router.get("/health")
async def asset_server_health():
    """Asset server health check"""
    try:
        # TODO: Add health checks for:
        # - Database connectivity
        # - Redis connectivity  
        # - External API availability
        # - Storage service status
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "connected",  # TODO: Actual health check
                "redis": "connected",     # TODO: Actual health check
                "storage": "connected",   # TODO: Actual health check
                "external_apis": "available"  # TODO: Actual health check
            }
        }
        
    except Exception as e:
        logger.error(f"Asset server health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@assets_router.get("/metrics")
async def get_asset_metrics(current_auth = Depends(get_current_auth)):
    """Performance metrics and cost analytics"""
    try:
        # TODO: Implement metrics collection
        # - Request counts by category
        # - Average response times
        # - Cost breakdown by strategy
        # - Cache hit rates
        # - Storage usage
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "requests": {
                "total": 0,
                "by_category": {},
                "by_strategy": {}
            },
            "performance": {
                "avg_response_time_ms": 0,
                "cache_hit_rate": 0.0
            },
            "costs": {
                "total_daily": 0.0,
                "by_strategy": {}
            },
            "storage": {
                "total_assets": 0,
                "total_size_mb": 0.0
            }
        }
        
    except Exception as e:
        logger.error(f"Asset metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics collection failed: {str(e)}")