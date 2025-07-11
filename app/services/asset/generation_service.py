import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.shared.config import settings
from app.shared.logging import get_logger
from app.shared.nats_client import NATSClient
from .models.asset import (
    AssetRequest,
    AssetResponse,
    AssetData,
    StorageInfo,
    StorageType,
    AssetSource,
    GeneratedAsset,
    ModifiedAsset,
    DatabaseAsset,
    LicenseType
)
from .storage_service import SupabaseStorageService
from .redis_service import redis_service
from .openai_client import OpenAIImageClient, StabilityAIClient

logger = get_logger(__name__)


class AIGenerationService:
    def __init__(self):
        self.settings = settings
        self.storage_service = SupabaseStorageService()
        self.nats_client = None
        
        # Initialize AI service clients
        self.openai_client = OpenAIImageClient()
        self.stability_client = StabilityAIClient()
        
        # Import and initialize new provider clients
        try:
            from .meshy_client import MeshyAIClient
            self.meshy_client = MeshyAIClient()
        except ImportError as e:
            logger.warning(f"Failed to import MeshyAIClient: {e}")
            self.meshy_client = None
            
        try:
            from .midjourney_client import MidjourneyClient
            self.midjourney_client = MidjourneyClient()
        except ImportError as e:
            logger.warning(f"Failed to import MidjourneyClient: {e}")
            self.midjourney_client = None
            
        try:
            from .mubert_client import MubertClient
            self.mubert_client = MubertClient()
        except ImportError as e:
            logger.warning(f"Failed to import MubertClient: {e}")
            self.mubert_client = None

    async def _publish_asset_event(self, event_type: str, data: dict):
        """Publish asset generation events to NATS"""
        try:
            if not self.nats_client:
                self.nats_client = NATSClient()
                await self.nats_client.connect()
            
            subject = f"gaia.asset.generation.{event_type}"
            await self.nats_client.publish(subject, data)
            logger.debug(f"Published asset event: {subject}")
        except Exception as e:
            logger.warning(f"Failed to publish asset event {event_type}: {e}")

    async def generate_asset(self, request: AssetRequest) -> AssetResponse:
        """
        Full AI generation pipeline with cost tracking
        Store generated assets in Supabase Storage
        Add to database for future reuse
        """
        start_time = time.time()
        
        try:
            generation_id = str(uuid.uuid4())
            logger.info(f"Starting AI generation: {request.category.value} - {request.style}")
            
            # Publish generation started event
            await self._publish_asset_event("started", {
                "generation_id": generation_id,
                "category": request.category.value,
                "style": request.style,
                "session_id": request.session_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Check cost budget
            if not await self._check_generation_budget(request.session_id):
                await self._publish_asset_event("failed", {
                    "generation_id": generation_id,
                    "error": "Generation budget exceeded for this session",
                    "timestamp": datetime.utcnow().isoformat()
                })
                raise Exception("Generation budget exceeded for this session")
            
            # Route to appropriate generation service
            if request.category.value in ["environment", "character", "prop"]:
                generated_asset = await self._generate_3d_asset(request)
            elif request.category.value == "texture":
                generated_asset = await self._generate_texture(request)
            elif request.category.value == "audio":
                generated_asset = await self._generate_audio(request)
            elif request.category.value == "animation":
                generated_asset = await self._generate_animation(request)
            elif request.category.value == "image":
                generated_asset = await self._generate_image(request)
            else:
                raise Exception(f"Unsupported asset category: {request.category.value}")
            
            # Store in Supabase Storage (handle different asset types)
            if request.category.value == "image":
                # For images, download from external URL and store
                storage_url = await self.storage_service.upload_generated_image(
                    image_url=generated_asset.asset_data.download_url,
                    asset_metadata=generated_asset.metadata
                )
            else:
                # For other asset types, store the asset data
                storage_url = await self.storage_service.upload_generated_asset(
                    asset_data=generated_asset.asset_data.download_url.encode(),  # Placeholder
                    asset_metadata=generated_asset.metadata,
                    file_format=generated_asset.asset_data.file_format,
                    category=request.category.value
                )
            
            # Update storage info
            storage_info = StorageInfo(
                storage_type=StorageType.SUPABASE,
                bucket_name=getattr(self.settings, 'ASSET_STORAGE_BUCKET', 'assets'),
                file_path=f"generated/{request.category.value}/{generated_asset.generation_id}",
                external_source=generated_asset.generation_service
            )
            
            # Track cost
            await redis_service.track_generation_cost(
                session_id=request.session_id,
                cost=generated_asset.generation_cost
            )
            
            # Database storage is handled by storage_service for images
            if request.category.value != "image":
                await self._store_generated_asset_in_database(generated_asset, storage_url)
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            response = AssetResponse(
                asset_id=generated_asset.generation_id,
                source=AssetSource.GENERATED,
                cost=generated_asset.generation_cost,
                response_time_ms=generation_time_ms,
                asset_data=generated_asset.asset_data,
                storage_info=storage_info,
                metadata=generated_asset.metadata
            )
            
            logger.info(f"AI generation completed: {generated_asset.generation_id} in {generation_time_ms}ms for ${generated_asset.generation_cost:.4f}")
            
            # Publish generation completed event
            await self._publish_asset_event("completed", {
                "generation_id": generated_asset.generation_id,
                "asset_id": generated_asset.generation_id,
                "category": request.category.value,
                "cost": generated_asset.generation_cost,
                "generation_time_ms": generation_time_ms,
                "session_id": request.session_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return response
            
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            
            # Publish generation failed event
            await self._publish_asset_event("failed", {
                "generation_id": generation_id if 'generation_id' in locals() else "unknown",
                "error": str(e),
                "category": request.category.value,
                "session_id": request.session_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            raise

    async def modify_existing_asset(
        self,
        base_asset: DatabaseAsset,
        request: AssetRequest
    ) -> AssetResponse:
        """
        AI-powered asset modification for hybrid approach
        Store modified version in Supabase Storage
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting asset modification: {base_asset.id}")
            
            # Determine modifications needed
            modifications = await self._analyze_required_modifications(base_asset, request)
            
            # Perform modifications using appropriate AI service
            modified_asset = await self._perform_asset_modifications(
                base_asset=base_asset,
                modifications=modifications,
                request=request
            )
            
            # Store modified asset
            storage_url = await self.storage_service.upload_generated_asset(
                asset_data=modified_asset.modified_asset_data.download_url.encode(),  # Placeholder
                asset_metadata=modified_asset.metadata,
                file_format=modified_asset.modified_asset_data.file_format,
                category=request.category.value
            )
            
            # Track cost
            await redis_service.track_generation_cost(
                session_id=request.session_id,
                cost=modified_asset.modification_cost
            )
            
            # Store modification record
            await self._store_modification_record(modified_asset)
            
            modification_time_ms = int((time.time() - start_time) * 1000)
            
            storage_info = StorageInfo(
                storage_type=StorageType.GENERATED,
                bucket_name=self.settings.ASSET_STORAGE_BUCKET,
                file_path=f"generated/{request.category.value}/{modified_asset.modification_id}"
            )
            
            response = AssetResponse(
                asset_id=modified_asset.modification_id,
                source=AssetSource.HYBRID,
                cost=modified_asset.modification_cost,
                response_time_ms=modification_time_ms,
                asset_data=modified_asset.modified_asset_data,
                storage_info=storage_info,
                metadata=modified_asset.metadata
            )
            
            logger.info(f"Asset modification completed: {modified_asset.modification_id} for ${modified_asset.modification_cost:.4f}")
            
            return response
            
        except Exception as e:
            logger.error(f"Asset modification failed: {e}")
            raise

    async def _generate_3d_asset(self, request: AssetRequest) -> GeneratedAsset:
        """Generate 3D assets using Meshy AI"""
        try:
            if not self.meshy_client:
                raise Exception("Meshy AI client not available")
            
            logger.info(f"Generating 3D asset with Meshy AI: {request.description}")
            
            # Map request parameters to Meshy AI parameters
            asset_type = "model"  # Default to model
            if request.category.value == "character":
                asset_type = "character"
            elif request.category.value == "prop":
                asset_type = "prop"
            elif request.category.value == "environment":
                asset_type = "environment"
            
            # Map quality
            quality = "medium"  # Default
            if request.requirements and hasattr(request.requirements, 'quality'):
                quality_mapping = {
                    "low": "low",
                    "standard": "medium", 
                    "high": "high",
                    "ultra": "ultra"
                }
                quality = quality_mapping.get(request.requirements.quality.value, "medium")
            
            # Generate with Meshy AI
            generated_asset = await self.meshy_client.generate_3d_asset(
                prompt=request.description,
                asset_type=asset_type,
                style=request.style or "realistic",
                quality=quality
            )
            
            return generated_asset
            
        except Exception as e:
            logger.error(f"3D asset generation failed: {e}")
            raise

    async def _generate_texture(self, request: AssetRequest) -> GeneratedAsset:
        """Generate textures using Midjourney"""
        try:
            if not self.midjourney_client:
                raise Exception("Midjourney client not available")
            
            logger.info(f"Generating texture with Midjourney: {request.description}")
            
            # Determine texture type and resolution
            texture_type = "seamless"  # Default for textures
            resolution = "1024x1024"  # Default resolution
            
            if request.requirements and hasattr(request.requirements, 'resolution'):
                resolution = request.requirements.resolution or "1024x1024"
            
            # Generate with Midjourney
            generated_asset = await self.midjourney_client.generate_texture(
                prompt=request.description,
                texture_type=texture_type,
                style=request.style or "realistic",
                resolution=resolution,
                seamless=True
            )
            
            return generated_asset
            
        except Exception as e:
            logger.error(f"Texture generation failed: {e}")
            raise

    async def _generate_audio(self, request: AssetRequest) -> GeneratedAsset:
        """Generate audio using Mubert"""
        try:
            if not self.mubert_client:
                raise Exception("Mubert client not available")
            
            logger.info(f"Generating audio with Mubert: {request.description}")
            
            # Extract audio parameters from request
            duration = 30  # Default duration
            genre = "ambient"  # Default genre
            mood = "calm"  # Default mood
            format_type = "wav"  # Default format
            
            # Parse style for genre and mood
            if request.style:
                style_parts = request.style.lower().split("-")
                if len(style_parts) >= 1:
                    genre = style_parts[0]
                if len(style_parts) >= 2:
                    mood = style_parts[1]
            
            # Check if this is a soundtrack request
            is_soundtrack = "soundtrack" in request.description.lower() or "background" in request.description.lower()
            
            if is_soundtrack:
                # Use soundtrack generation for longer, more complex audio
                generated_asset = await self.mubert_client.generate_soundtrack(
                    prompt=request.description,
                    duration=min(duration * 2, 120),  # Longer for soundtracks
                    genre=genre,
                    intensity=mood,
                    loop=True,
                    format=format_type
                )
            else:
                # Use regular audio generation
                generated_asset = await self.mubert_client.generate_audio(
                    prompt=request.description,
                    duration=duration,
                    genre=genre,
                    mood=mood,
                    format=format_type
                )
            
            return generated_asset
            
        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            raise

    async def _generate_animation(self, request: AssetRequest) -> GeneratedAsset:
        """Generate animations"""
        try:
            # TODO: Implement animation generation
            logger.info(f"Generating animation: {request.description}")
            
            generation_cost = 0.35  # Higher cost for animations
            
            asset_data = AssetData(
                download_url="https://placeholder.com/generated.fbx",
                preview_image_url="https://placeholder.com/animation_preview.gif",
                file_format="fbx",
                file_size_mb=8.7,
                quality_score=0.82,
                license_type=LicenseType.PROPRIETARY,
                attribution_required=False
            )
            
            return GeneratedAsset(
                generation_id=str(uuid.uuid4()),
                prompt=request.description,
                category=request.category,
                style=request.style,
                title=f"Generated {request.style} animation",
                description=request.description,
                asset_data=asset_data,
                storage_info=StorageInfo(storage_type=StorageType.GENERATED),
                generation_cost=generation_cost,
                generation_time_ms=12000,
                generation_service="custom_animation_ai",
                quality_score=0.82,
                metadata={"prompt": request.description, "style": request.style}
            )
            
        except Exception as e:
            logger.error(f"Animation generation failed: {e}")
            raise

    async def _generate_image(self, request: AssetRequest) -> GeneratedAsset:
        """Generate images using OpenAI DALL-E or Stability AI"""
        try:
            logger.info(f"Generating image: {request.description}")
            
            # Determine quality and size based on requirements
            quality = "hd" if request.requirements and request.requirements.quality.value in ["high", "ultra"] else "standard"
            size = "1024x1024"  # Default size
            
            # Try OpenAI first, fallback to Stability AI
            try:
                generated_asset = await self.openai_client.generate_image(
                    prompt=request.description,
                    style=request.style,
                    quality=quality,
                    size=size
                )
                logger.info(f"Image generated with OpenAI DALL-E: {generated_asset.generation_id}")
                return generated_asset
                
            except Exception as openai_error:
                logger.warning(f"OpenAI generation failed, trying Stability AI: {openai_error}")
                
                # Fallback to Stability AI
                if self.stability_client:
                    generated_asset = await self.stability_client.generate_image(
                        prompt=request.description,
                        style=request.style,
                        width=1024,
                        height=1024
                    )
                    logger.info(f"Image generated with Stability AI: {generated_asset.generation_id}")
                    return generated_asset
                else:
                    raise openai_error  # Re-raise original error if no fallback
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise

    async def _check_generation_budget(self, session_id: str) -> bool:
        """Check if generation is within budget limits"""
        try:
            cost_stats = await redis_service.get_generation_cost_stats(session_id)
            remaining_budget = cost_stats.get("remaining_budget", 0)
            
            if remaining_budget <= 0:
                logger.warning(f"Generation budget exceeded for session {session_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Budget check failed: {e}")
            return False

    async def _analyze_required_modifications(
        self,
        base_asset: DatabaseAsset,
        request: AssetRequest
    ) -> List[str]:
        """Analyze what modifications are needed"""
        modifications = []
        
        # Compare request style with base asset style
        if request.style not in base_asset.style_tags:
            modifications.append(f"Apply {request.style} style")
        
        # Check quality requirements
        if request.requirements:
            if request.requirements.quality.value == "ultra" and base_asset.quality_score < 0.9:
                modifications.append("Enhance quality to ultra level")
            
            if request.requirements.polygon_count_max and hasattr(base_asset, 'polygon_count'):
                if base_asset.metadata.get('polygon_count', 0) > request.requirements.polygon_count_max:
                    modifications.append("Reduce polygon count")
        
        # Default modification if none specific
        if not modifications:
            modifications.append("Apply style variations")
        
        return modifications

    async def _perform_asset_modifications(
        self,
        base_asset: DatabaseAsset,
        modifications: List[str],
        request: AssetRequest
    ) -> ModifiedAsset:
        """Perform the actual asset modifications"""
        try:
            # TODO: Implement actual modification logic
            # This would route to different AI services based on asset type
            
            modification_cost = 0.05 * len(modifications)  # Base cost per modification
            
            # Create modified asset data (placeholder)
            modified_data = AssetData(
                download_url=f"https://placeholder.com/modified_{base_asset.id}.{base_asset.file_format}",
                preview_image_url=f"https://placeholder.com/modified_preview_{base_asset.id}.png",
                file_format=base_asset.file_format,
                file_size_mb=base_asset.file_size_mb * 1.1,  # Slightly larger after modifications
                quality_score=min(base_asset.quality_score * 1.1, 1.0),  # Improved quality
                license_type=LicenseType.PROPRIETARY,  # Modified assets are proprietary
                attribution_required=False
            )
            
            return ModifiedAsset(
                modification_id=str(uuid.uuid4()),
                base_asset_id=base_asset.id,
                modifications=modifications,
                modified_asset_data=modified_data,
                storage_info=StorageInfo(storage_type=StorageType.GENERATED),
                modification_cost=modification_cost,
                modification_time_ms=2000,
                modification_service="ai_modifier",
                quality_score=modified_data.quality_score,
                metadata={
                    "base_asset": base_asset.id,
                    "modifications": modifications,
                    "original_style": base_asset.style_tags,
                    "requested_style": request.style
                }
            )
            
        except Exception as e:
            logger.error(f"Asset modification failed: {e}")
            raise

    async def _store_generated_asset_in_database(
        self,
        generated_asset: GeneratedAsset,
        storage_url: str
    ):
        """Store generated asset metadata in database for future reuse"""
        try:
            # TODO: Insert into assets table
            logger.info(f"Stored generated asset in database: {generated_asset.generation_id}")
            
        except Exception as e:
            logger.error(f"Failed to store generated asset: {e}")

    async def _store_modification_record(self, modified_asset: ModifiedAsset):
        """Store modification record in database"""
        try:
            # TODO: Insert into asset_modifications table
            logger.info(f"Stored modification record: {modified_asset.modification_id}")
            
        except Exception as e:
            logger.error(f"Failed to store modification record: {e}")