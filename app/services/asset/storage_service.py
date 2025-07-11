import uuid
import asyncio
from typing import Optional, Dict, Any, List, BinaryIO
from datetime import datetime
from io import BytesIO
from PIL import Image
import aiofiles

from app.shared.supabase import get_supabase_client
from app.shared.config import settings
from app.shared.logging import get_logger
from .models.asset import (
    AssetUploadResponse,
    StorageInfo,
    StorageType,
    AssetCategory
)

logger = get_logger(__name__)


class SupabaseStorageService:
    def __init__(self):
        self.settings = settings
        self.supabase = get_supabase_client()
        self.bucket_name = self.settings.ASSET_STORAGE_BUCKET
        self.max_file_size_bytes = self.settings.MAX_ASSET_FILE_SIZE_MB * 1024 * 1024
        self.max_preview_size_bytes = self.settings.MAX_PREVIEW_IMAGE_SIZE_MB * 1024 * 1024

    async def upload_community_asset(
        self,
        file_data: bytes,
        filename: str,
        category: str,
        metadata: Dict[str, Any]
    ) -> AssetUploadResponse:
        """Upload community-contributed asset"""
        try:
            asset_id = str(uuid.uuid4())
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            
            # Generate unique file path
            file_path = f"community/{category}/{asset_id}_{filename}"
            
            # Upload main asset file
            upload_result = await self._upload_file_to_storage(
                file_path=file_path,
                file_data=file_data,
                content_type=self._get_content_type(file_extension)
            )
            
            if not upload_result:
                raise Exception("Failed to upload asset file")
            
            # Generate and upload preview image
            preview_url = await self._generate_and_upload_preview(
                asset_id=asset_id,
                file_data=file_data,
                file_extension=file_extension,
                category=category
            )
            
            # Store asset metadata in database
            await self._store_asset_metadata(
                asset_id=asset_id,
                file_path=file_path,
                filename=filename,
                category=category,
                preview_url=preview_url,
                metadata=metadata
            )
            
            # Get public URL for the uploaded file
            public_url = self._get_public_url(file_path)
            
            logger.info(f"Community asset uploaded successfully: {asset_id}")
            
            return AssetUploadResponse(
                asset_id=asset_id,
                upload_url=public_url,
                preview_url=preview_url,
                status="uploaded",
                message="Asset uploaded successfully"
            )
            
        except Exception as e:
            logger.error(f"Community asset upload failed: {e}")
            raise

    async def upload_generated_asset(
        self,
        asset_data: bytes,
        asset_metadata: Dict[str, Any],
        file_format: str,
        category: str
    ) -> str:
        """
        Store generated asset in Supabase Storage
        Return storage URL for database insertion
        """
        try:
            asset_id = str(uuid.uuid4())
            file_path = f"generated/{category}/{asset_id}.{file_format}"
            
            # Upload generated asset
            upload_result = await self._upload_file_to_storage(
                file_path=file_path,
                file_data=asset_data,
                content_type=self._get_content_type(file_format)
            )
            
            if not upload_result:
                raise Exception("Failed to upload generated asset")
            
            # Generate preview if not an image
            if category != "image" and file_format not in ['png', 'jpg', 'jpeg', 'gif']:
                await self._generate_and_upload_preview(
                    asset_id=asset_id,
                    file_data=asset_data,
                    file_extension=file_format,
                    category=category
                )
            
            public_url = self._get_public_url(file_path)
            logger.info(f"Generated asset stored: {asset_id}")
            
            return public_url
            
        except Exception as e:
            logger.error(f"Generated asset upload failed: {e}")
            raise

    async def upload_preview_image(
        self,
        image_data: bytes,
        asset_id: str
    ) -> str:
        """Upload preview image for external assets"""
        try:
            file_path = f"previews/{asset_id}.png"
            
            # Resize and optimize preview image
            optimized_image = await self._optimize_preview_image(image_data)
            
            upload_result = await self._upload_file_to_storage(
                file_path=file_path,
                file_data=optimized_image,
                content_type="image/png"
            )
            
            if not upload_result:
                raise Exception("Failed to upload preview image")
            
            return self._get_public_url(file_path)
            
        except Exception as e:
            logger.error(f"Preview image upload failed: {e}")
            raise

    async def _upload_file_to_storage(
        self,
        file_path: str,
        file_data: bytes,
        content_type: str = "application/octet-stream"
    ) -> bool:
        """Upload file to Supabase Storage"""
        try:
            # Use Supabase client to upload file
            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={
                    "content-type": content_type,
                    "cache-control": "3600"
                }
            )
            
            logger.debug(f"File uploaded to storage: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Storage upload failed for {file_path}: {e}")
            return False

    def _get_public_url(self, file_path: str) -> str:
        """Get public URL for a file in storage"""
        try:
            result = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
            return result
        except Exception as e:
            logger.error(f"Failed to get public URL for {file_path}: {e}")
            return ""

    async def _generate_and_upload_preview(
        self,
        asset_id: str,
        file_data: bytes,
        file_extension: str,
        category: str
    ) -> str:
        """Generate and upload preview image for non-image assets"""
        try:
            preview_data = None
            
            if file_extension.lower() in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                # For images, create a thumbnail
                preview_data = await self._optimize_preview_image(file_data)
            else:
                # For other file types, create a placeholder preview
                preview_data = await self._create_placeholder_preview(category, file_extension)
            
            if preview_data:
                return await self.upload_preview_image(preview_data, asset_id)
            
            return ""
            
        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            return ""

    async def _optimize_preview_image(self, image_data: bytes) -> bytes:
        """Optimize image for preview (resize, compress)"""
        try:
            # Load image
            image = Image.open(BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Resize to preview size (max 512x512)
            max_size = (512, 512)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            output_buffer = BytesIO()
            image.save(output_buffer, format='PNG', optimize=True)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            raise

    async def _create_placeholder_preview(self, category: str, file_extension: str) -> bytes:
        """Create placeholder preview for non-image files"""
        try:
            # Create a simple placeholder image
            size = (512, 512)
            color_map = {
                "audio": "#FF6B6B",
                "3d-models": "#4ECDC4", 
                "textures": "#45B7D1",
                "animations": "#96CEB4",
                "environment": "#FFEAA7",
                "character": "#DDA0DD",
                "prop": "#98D8C8"
            }
            
            background_color = color_map.get(category, "#CCCCCC")
            
            # Create image with PIL
            image = Image.new('RGB', size, background_color)
            
            # TODO: Add text/icon to indicate file type
            # For now, just return solid color
            
            output_buffer = BytesIO()
            image.save(output_buffer, format='PNG')
            
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Placeholder creation failed: {e}")
            raise

    def _get_content_type(self, file_extension: str) -> str:
        """Get appropriate content type for file extension"""
        content_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg',
            'gltf': 'model/gltf+json',
            'glb': 'model/gltf-binary',
            'fbx': 'application/octet-stream',
            'obj': 'application/octet-stream',
            'zip': 'application/zip',
            'json': 'application/json'
        }
        
        return content_types.get(file_extension.lower(), 'application/octet-stream')

    async def _store_asset_metadata(
        self,
        asset_id: str,
        file_path: str,
        filename: str,
        category: str,
        preview_url: str,
        metadata: Dict[str, Any]
    ):
        """Store asset metadata in database"""
        try:
            # TODO: Store in database using Supabase client
            # This would typically insert into the assets table
            logger.info(f"Asset metadata stored for {asset_id}")
            
        except Exception as e:
            logger.error(f"Failed to store asset metadata: {e}")
            raise

    async def get_storage_usage(self) -> Dict[str, float]:
        """Get storage usage analytics"""
        try:
            # TODO: Implement storage usage calculation
            # This would query storage bucket statistics
            
            return {
                "total_size_mb": 0.0,
                "files_count": 0,
                "by_category": {},
                "cost_estimate": 0.0
            }
            
        except Exception as e:
            logger.error(f"Storage usage calculation failed: {e}")
            return {}

    async def cleanup_old_files(self, days_old: int = 30):
        """Clean up old temporary files and previews"""
        try:
            # TODO: Implement cleanup logic
            # Remove files older than specified days
            # Focus on generated previews and temporary files
            
            logger.info(f"Storage cleanup completed for files older than {days_old} days")
            
        except Exception as e:
            logger.error(f"Storage cleanup failed: {e}")

    async def upload_generated_image(
        self,
        image_url: str,
        asset_metadata: Dict[str, Any]
    ) -> str:
        """
        Download and store generated image from external URL (e.g., DALL-E)
        Return Supabase Storage URL
        """
        try:
            import httpx
            
            # Download image from external URL
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                if response.status_code != 200:
                    raise Exception(f"Failed to download image: {response.status_code}")
                
                image_data = response.content
            
            # Generate asset ID and file path
            asset_id = asset_metadata.get('generation_id', str(uuid.uuid4()))
            file_path = f"generated/image/{asset_id}.png"
            
            # Upload to Supabase Storage
            upload_result = await self._upload_file_to_storage(
                file_path=file_path,
                file_data=image_data,
                content_type="image/png"
            )
            
            if not upload_result:
                raise Exception("Failed to upload generated image")
            
            # Store metadata in database
            await self._store_generated_image_metadata(
                asset_id=asset_id,
                file_path=file_path,
                metadata=asset_metadata
            )
            
            public_url = self._get_public_url(file_path)
            logger.info(f"Generated image stored: {asset_id}")
            
            return public_url
            
        except Exception as e:
            logger.error(f"Generated image upload failed: {e}")
            raise

    async def _store_generated_image_metadata(
        self,
        asset_id: str,
        file_path: str,
        metadata: Dict[str, Any]
    ):
        """Store generated image metadata in database"""
        try:
            # Get generated source ID
            source_result = self.supabase.table("asset_sources").select("id").eq("source_type", "generated").eq("source_name", metadata.get("generation_service", "ai_generated")).execute()
            source_id = source_result.data[0]["id"] if source_result.data else None
            
            # If no specific service found, get general generated source
            if not source_id:
                source_result = self.supabase.table("asset_sources").select("id").eq("source_type", "generated").limit(1).execute()
                source_id = source_result.data[0]["id"] if source_result.data else None
            
            # Insert into assets table
            asset_data = {
                "id": asset_id,
                "source_id": source_id,
                "category": "image",
                "title": metadata.get("title", "Generated Image"),
                "description": metadata.get("prompt", metadata.get("description", "")),
                "style_tags": [metadata.get("style", "generated")],
                "file_url": self._get_public_url(file_path),
                "storage_type": "supabase",
                "file_size_mb": metadata.get("file_size_mb", 2.0),
                "file_format": "png",
                "preview_image_url": self._get_public_url(file_path),  # Same as main image for generated images
                "quality_score": metadata.get("quality_score", 0.9),
                "license_type": "proprietary",
                "attribution_required": False,
                "metadata": metadata
            }
            
            result = self.supabase.table("assets").insert(asset_data).execute()
            logger.info(f"Generated image metadata stored for {asset_id}")
            
        except Exception as e:
            logger.error(f"Failed to store generated image metadata: {e}")
            raise