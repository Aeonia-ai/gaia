import asyncio
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import numpy as np

from app.shared.supabase import get_supabase_client
from app.shared.config import settings
from app.shared.logging import get_logger
from .models.asset import (
    DatabaseAsset,
    ExternalAsset,
    AssetRequest,
    AssetResponse,
    AssetData,
    StorageInfo,
    StorageType,
    AssetSource,
    AssetCategory,
    LicenseType
)
from .redis_service import redis_service

logger = get_logger(__name__)


class AssetSearchService:
    def __init__(self):
        self.settings = settings
        self.supabase = get_supabase_client()
        self.similarity_threshold = self.settings.SEMANTIC_SEARCH_SIMILARITY_THRESHOLD

    async def search_database_assets(
        self,
        category: str,
        description: str,
        style_tags: List[str],
        limit: int = None,
        session_id: Optional[str] = None
    ) -> List[DatabaseAsset]:
        """
        Semantic search with vector similarity in Supabase
        Include quality scoring and license compatibility
        """
        try:
            limit = limit or self.settings.ASSET_SEARCH_LIMIT_DEFAULT
            limit = min(limit, self.settings.ASSET_SEARCH_LIMIT_MAX)
            
            logger.info(f"Searching database assets: {category} - {description[:50]}...")
            
            # Check cache first
            cached_results = await redis_service.get_cached_asset_search(
                search_query=description,
                category=category
            )
            
            if cached_results:
                logger.debug("Using cached search results")
                return [DatabaseAsset(**asset) for asset in cached_results]
            
            # Generate search embedding
            search_embedding = await self._generate_search_embedding(description)
            
            # Perform database search
            results = await self._search_database_with_embedding(
                category=category,
                embedding=search_embedding,
                style_tags=style_tags,
                limit=limit
            )
            
            # Cache results
            if results:
                cache_data = [asset.dict() for asset in results]
                await redis_service.cache_asset_search(
                    search_query=description,
                    category=category,
                    results=cache_data
                )
            
            logger.info(f"Database search completed: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Database asset search failed: {e}")
            return []

    async def search_external_sources(
        self,
        request: AssetRequest
    ) -> List[ExternalAsset]:
        """
        Search external sources (Poly Haven, Freesound, etc.)
        Cache results in Supabase for future use
        """
        try:
            logger.info(f"Searching external sources for: {request.category.value}")
            
            external_results = []
            
            # Search different sources based on category
            if request.category == AssetCategory.TEXTURE:
                poly_haven_results = await self._search_poly_haven(request)
                external_results.extend(poly_haven_results)
            
            elif request.category == AssetCategory.AUDIO:
                freesound_results = await self._search_freesound(request)
                external_results.extend(freesound_results)
            
            elif request.category in [AssetCategory.ENVIRONMENT, AssetCategory.PROP]:
                # Check multiple sources for 3D assets
                poly_haven_results = await self._search_poly_haven(request)
                external_results.extend(poly_haven_results)
            
            # Cache external results for future use
            for asset in external_results:
                await redis_service.cache_external_asset(
                    source_name=asset.source_name,
                    asset_id=asset.external_id,
                    asset_data=asset.dict()
                )
            
            logger.info(f"External search completed: {len(external_results)} results")
            return external_results
            
        except Exception as e:
            logger.error(f"External source search failed: {e}")
            return []

    async def prepare_database_asset_response(
        self,
        asset: DatabaseAsset,
        session_id: str
    ) -> AssetResponse:
        """Convert database asset to response format"""
        try:
            # Increment download count
            await self._increment_asset_download_count(asset.id)
            
            # Track usage
            await self._track_asset_usage(
                asset_id=asset.id,
                session_id=session_id,
                usage_type="download"
            )
            
            asset_data = AssetData(
                download_url=asset.file_url,
                preview_image_url=asset.preview_image_url,
                file_format=asset.file_format,
                file_size_mb=asset.file_size_mb,
                quality_score=asset.quality_score,
                license_type=asset.license_type,
                attribution_required=asset.attribution_required
            )
            
            return AssetResponse(
                asset_id=asset.id,
                source=AssetSource.DATABASE,
                cost=0.0,  # Database hits are free
                response_time_ms=0,  # Will be updated by caller
                asset_data=asset_data,
                storage_info=asset.storage_info,
                metadata=asset.metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to prepare database asset response: {e}")
            raise

    async def _generate_search_embedding(self, text: str) -> List[float]:
        """Generate embedding for search text using sentence transformers"""
        try:
            # TODO: Implement actual embedding generation
            # This would typically use a sentence transformer model
            # For now, return a dummy embedding
            
            # In a real implementation, you might use:
            # from sentence_transformers import SentenceTransformer
            # model = SentenceTransformer('all-MiniLM-L6-v2')
            # embedding = model.encode(text)
            
            # For now, create a dummy 384-dimensional embedding
            dummy_embedding = np.random.random(384).tolist()
            
            logger.debug(f"Generated embedding for text: {text[:50]}...")
            return dummy_embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

    async def _search_database_with_embedding(
        self,
        category: str,
        embedding: List[float],
        style_tags: List[str],
        limit: int
    ) -> List[DatabaseAsset]:
        """Perform vector similarity search in database"""
        try:
            # TODO: Implement actual database search with pgvector
            # This would typically use a SQL query with vector similarity
            
            # Example query would be:
            # SELECT *, embedding <=> %s as similarity 
            # FROM assets 
            # WHERE category = %s 
            # AND style_tags && %s
            # ORDER BY similarity 
            # LIMIT %s
            
            # For now, return empty results
            logger.debug(f"Performing vector search for category: {category}")
            
            return []
            
        except Exception as e:
            logger.error(f"Database vector search failed: {e}")
            return []

    async def _search_poly_haven(self, request: AssetRequest) -> List[ExternalAsset]:
        """Search Poly Haven for free assets"""
        try:
            # TODO: Implement Poly Haven API client
            # This would search their API for relevant assets
            
            logger.debug("Searching Poly Haven...")
            return []
            
        except Exception as e:
            logger.error(f"Poly Haven search failed: {e}")
            return []

    async def _search_freesound(self, request: AssetRequest) -> List[ExternalAsset]:
        """Search Freesound for Creative Commons audio"""
        try:
            # TODO: Implement Freesound API client
            # This would search for CC-licensed audio
            
            logger.debug("Searching Freesound...")
            return []
            
        except Exception as e:
            logger.error(f"Freesound search failed: {e}")
            return []

    async def _increment_asset_download_count(self, asset_id: str):
        """Increment download count for an asset"""
        try:
            # TODO: Update database download count
            logger.debug(f"Incremented download count for asset: {asset_id}")
            
        except Exception as e:
            logger.error(f"Failed to increment download count: {e}")

    async def _track_asset_usage(
        self,
        asset_id: str,
        session_id: str,
        usage_type: str,
        cost: float = 0.0
    ):
        """Track asset usage in analytics table"""
        try:
            # TODO: Insert usage record into database
            logger.debug(f"Tracked asset usage: {asset_id} - {usage_type}")
            
        except Exception as e:
            logger.error(f"Failed to track asset usage: {e}")

    async def get_popular_assets(
        self,
        category: Optional[str] = None,
        limit: int = 10,
        time_period: str = "week"
    ) -> List[DatabaseAsset]:
        """Get popular assets by download count"""
        try:
            # TODO: Query database for popular assets
            # Order by download_count DESC with optional category filter
            
            logger.debug(f"Getting popular assets for category: {category}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get popular assets: {e}")
            return []

    async def get_similar_assets(
        self,
        asset_id: str,
        limit: int = 5
    ) -> List[DatabaseAsset]:
        """Find similar assets using vector similarity"""
        try:
            # TODO: Get asset embedding and find similar ones
            # Use vector similarity search on the embedding column
            
            logger.debug(f"Finding similar assets to: {asset_id}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get similar assets: {e}")
            return []

    async def get_search_suggestions(
        self,
        partial_query: str,
        category: Optional[str] = None
    ) -> List[str]:
        """Get search suggestions based on partial query"""
        try:
            # TODO: Implement search suggestions
            # Could use full-text search on titles/descriptions
            # Or common search patterns from analytics
            
            logger.debug(f"Getting search suggestions for: {partial_query}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []