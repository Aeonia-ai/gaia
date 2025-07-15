import asyncio
import httpx
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import json

from app.shared.config import settings
from app.shared.logging import get_logger
from .advanced_pricing_service import AdvancedPricingService, UsageMetrics
from .models.asset import (
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    AssetData,
    LicenseType,
    AssetCategory,
    StorageInfo,
    StorageType
)
from .models.source import GeneratedAsset

logger = get_logger(__name__)


class MidjourneyClient:
    """Midjourney texture and artistic image generation client."""
    
    def __init__(self):
        self.settings = settings
        self.api_key = getattr(self.settings, 'MIDJOURNEY_API_KEY', None)
        self.base_url = "https://api.midjourney.com/v1"
        self.pricing_service = AdvancedPricingService()
        
        if not self.api_key:
            logger.warning("Midjourney API key not found. Texture generation will be unavailable.")
    
    async def generate_texture(
        self,
        prompt: str,
        texture_type: str = "seamless",
        style: str = "realistic",
        resolution: str = "1024x1024",
        seamless: bool = True
    ) -> GeneratedAsset:
        """
        Generate a texture using Midjourney.
        
        Args:
            prompt: Text description of the texture to generate
            texture_type: Type of texture (seamless, material, pattern, surface)
            style: Style preference (realistic, artistic, stylized, abstract)
            resolution: Image resolution (1024x1024, 2048x2048)
            seamless: Whether to make the texture seamless/tileable
        """
        if not self.api_key:
            raise Exception("Midjourney API key not configured")
        
        try:
            logger.info(f"Generating texture with Midjourney: {prompt[:100]}...")
            
            # Create generation task
            task_response = await self._create_texture_task(prompt, texture_type, style, resolution, seamless)
            task_id = task_response["id"]
            
            # Poll for completion
            result_data = await self._poll_task_completion(task_id)
            
            # Calculate cost
            usage = UsageMetrics(
                image_count=1,
                requests_per_minute=1,
                gpu_seconds=self._estimate_gpu_seconds(resolution)
            )
            
            cost_calc = await self.pricing_service.calculate_midjourney_cost(
                usage=usage,
                resolution=resolution,
                is_seamless=seamless,
                user_id=None
            )
            
            generation_cost = cost_calc.total_cost
            
            # Create asset data
            asset_data = AssetData(
                download_url=result_data.get("image_url", ""),
                preview_image_url=result_data.get("thumbnail_url", result_data.get("image_url", "")),
                file_format="png",
                file_size_mb=self._estimate_file_size(resolution),
                quality_score=0.95,  # Midjourney is known for high quality
                license_type=LicenseType.PROPRIETARY,
                attribution_required=False
            )
            
            # Create generated asset
            generated_asset = GeneratedAsset(
                generation_id=str(uuid.uuid4()),
                prompt=prompt,
                category=AssetCategory.TEXTURE,
                style=style,
                title=f"Generated {texture_type} texture - {style}",
                description=prompt,
                asset_data=asset_data,
                storage_info=StorageInfo(storage_type=StorageType.EXTERNAL),
                generation_cost=generation_cost,
                generation_time_ms=result_data.get("generation_time_ms", 90000),
                generation_service="midjourney",
                quality_score=asset_data.quality_score,
                metadata={
                    "prompt": prompt,
                    "enhanced_prompt": result_data.get("enhanced_prompt", prompt),
                    "texture_type": texture_type,
                    "style": style,
                    "resolution": resolution,
                    "seamless": seamless,
                    "task_id": task_id,
                    "midjourney_job_id": result_data.get("job_id"),
                    "generated_at": datetime.utcnow().isoformat(),
                    "gpu_seconds": usage.gpu_seconds
                }
            )
            
            # Track usage for billing
            await self.pricing_service.track_usage_realtime(
                provider="Midjourney",
                operation="texture_generation",
                asset_id=generated_asset.generation_id,
                usage=usage,
                cost_calculation=cost_calc
            )
            
            logger.info(f"Texture generated successfully: {generated_asset.generation_id} (cost: ${generation_cost:.4f})")
            
            return generated_asset
            
        except Exception as e:
            logger.error(f"Midjourney texture generation failed: {e}")
            raise
    
    async def generate_artistic_image(
        self,
        prompt: str,
        style: str = "artistic",
        aspect_ratio: str = "1:1",
        quality: str = "standard",
        chaos: int = 0,
        stylization: int = 100
    ) -> GeneratedAsset:
        """
        Generate an artistic image using Midjourney's advanced capabilities.
        
        Args:
            prompt: Text description of the image to generate
            style: Style preference (artistic, photorealistic, anime, abstract)
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:2)
            quality: Generation quality (standard, high)
            chaos: Chaos level (0-100) for variation
            stylization: Stylization level (0-1000)
        """
        if not self.api_key:
            raise Exception("Midjourney API key not configured")
        
        try:
            logger.info(f"Generating artistic image with Midjourney: {prompt[:100]}...")
            
            # Create generation task
            task_response = await self._create_artistic_task(
                prompt, style, aspect_ratio, quality, chaos, stylization
            )
            task_id = task_response["id"]
            
            # Poll for completion
            result_data = await self._poll_task_completion(task_id)
            
            # Calculate cost
            usage = UsageMetrics(
                image_count=1,
                requests_per_minute=1,
                gpu_seconds=self._estimate_gpu_seconds_artistic(quality, stylization)
            )
            
            cost_calc = await self.pricing_service.calculate_midjourney_cost(
                usage=usage,
                resolution=self._aspect_ratio_to_resolution(aspect_ratio),
                is_seamless=False,
                user_id=None
            )
            
            generation_cost = cost_calc.total_cost
            
            # Create asset data
            asset_data = AssetData(
                download_url=result_data.get("image_url", ""),
                preview_image_url=result_data.get("thumbnail_url", result_data.get("image_url", "")),
                file_format="png",
                file_size_mb=self._estimate_file_size_artistic(aspect_ratio, quality),
                quality_score=0.95,
                license_type=LicenseType.PROPRIETARY,
                attribution_required=False
            )
            
            # Create generated asset
            generated_asset = GeneratedAsset(
                generation_id=str(uuid.uuid4()),
                prompt=prompt,
                category=AssetCategory.IMAGE,
                style=style,
                title=f"Generated artistic image - {style}",
                description=prompt,
                asset_data=asset_data,
                storage_info=StorageInfo(storage_type=StorageType.EXTERNAL),
                generation_cost=generation_cost,
                generation_time_ms=result_data.get("generation_time_ms", 90000),
                generation_service="midjourney",
                quality_score=asset_data.quality_score,
                metadata={
                    "prompt": prompt,
                    "enhanced_prompt": result_data.get("enhanced_prompt", prompt),
                    "style": style,
                    "aspect_ratio": aspect_ratio,
                    "quality": quality,
                    "chaos": chaos,
                    "stylization": stylization,
                    "task_id": task_id,
                    "midjourney_job_id": result_data.get("job_id"),
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            # Track usage for billing
            await self.pricing_service.track_usage_realtime(
                provider="Midjourney",
                operation="artistic_generation",
                asset_id=generated_asset.generation_id,
                usage=usage,
                cost_calculation=cost_calc
            )
            
            logger.info(f"Artistic image generated successfully: {generated_asset.generation_id} (cost: ${generation_cost:.4f})")
            
            return generated_asset
            
        except Exception as e:
            logger.error(f"Midjourney artistic generation failed: {e}")
            raise
    
    async def _create_texture_task(
        self,
        prompt: str,
        texture_type: str,
        style: str,
        resolution: str,
        seamless: bool
    ) -> Dict[str, Any]:
        """Create a texture generation task."""
        
        # Enhance prompt for texture generation
        enhanced_prompt = self._enhance_texture_prompt(prompt, texture_type, style)
        
        # Add seamless/tileable parameters if needed
        if seamless:
            enhanced_prompt += " --tile"
        
        # Add resolution parameters
        if resolution == "2048x2048":
            enhanced_prompt += " --q 2"  # Higher quality for larger resolution
        
        payload = {
            "prompt": enhanced_prompt,
            "aspect_ratio": "1:1",  # Textures are typically square
            "model": "midjourney-6",  # Latest model
            "quality": "high" if resolution == "2048x2048" else "standard",
            "chaos": 0,  # Low chaos for consistent textures
            "stylization": 50,  # Moderate stylization for textures
            "seed": None,  # Random seed
            "webhook_url": None  # Would use webhook in production
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/imagine",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Midjourney task creation error: {response.status_code} - {error_text}")
                raise Exception(f"Midjourney task creation failed: {response.status_code}")
            
            return response.json()
    
    async def _create_artistic_task(
        self,
        prompt: str,
        style: str,
        aspect_ratio: str,
        quality: str,
        chaos: int,
        stylization: int
    ) -> Dict[str, Any]:
        """Create an artistic image generation task."""
        
        # Enhance prompt for artistic generation
        enhanced_prompt = self._enhance_artistic_prompt(prompt, style)
        
        payload = {
            "prompt": enhanced_prompt,
            "aspect_ratio": aspect_ratio,
            "model": "midjourney-6",
            "quality": quality,
            "chaos": max(0, min(100, chaos)),  # Clamp to valid range
            "stylization": max(0, min(1000, stylization)),  # Clamp to valid range
            "seed": None,
            "webhook_url": None
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/imagine",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Midjourney artistic task creation error: {response.status_code} - {error_text}")
                raise Exception(f"Midjourney artistic task creation failed: {response.status_code}")
            
            return response.json()
    
    async def _poll_task_completion(self, task_id: str, max_wait_minutes: int = 5) -> Dict[str, Any]:
        """Poll task until completion or timeout."""
        
        start_time = datetime.utcnow()
        max_wait_seconds = max_wait_minutes * 60
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > max_wait_seconds:
                    raise Exception(f"Task {task_id} timed out after {max_wait_minutes} minutes")
                
                # Get task status
                response = await client.get(
                    f"{self.base_url}/jobs/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to check task status: {response.status_code}")
                
                task_data = response.json()
                status = task_data.get("status")
                
                if status == "completed":
                    task_data["generation_time_ms"] = int(elapsed * 1000)
                    return task_data
                elif status == "failed":
                    error_msg = task_data.get("error", "Unknown error")
                    raise Exception(f"Task failed: {error_msg}")
                elif status in ["pending", "running"]:
                    logger.info(f"Task {task_id} status: {status}, waiting...")
                    await asyncio.sleep(5)  # Wait 5 seconds before next check
                else:
                    raise Exception(f"Unknown task status: {status}")
    
    def _enhance_texture_prompt(self, prompt: str, texture_type: str, style: str) -> str:
        """Enhance prompt for texture generation."""
        
        texture_modifiers = {
            "seamless": "seamless texture, tileable, repeating pattern",
            "material": "material texture, surface detail, high resolution",
            "pattern": "pattern, geometric, repeating design",
            "surface": "surface texture, realistic detail, material property"
        }
        
        style_modifiers = {
            "realistic": "photorealistic, highly detailed, accurate material properties",
            "artistic": "artistic interpretation, stylized, creative",
            "stylized": "stylized, game-ready, optimized",
            "abstract": "abstract pattern, artistic, unique design"
        }
        
        texture_mod = texture_modifiers.get(texture_type.lower(), "")
        style_mod = style_modifiers.get(style.lower(), "")
        
        enhanced = prompt
        if texture_mod:
            enhanced = f"{texture_mod}, {enhanced}"
        if style_mod:
            enhanced = f"{enhanced}, {style_mod}"
        
        # Add common texture requirements
        enhanced += ", high quality, clean, professional"
        
        return enhanced
    
    def _enhance_artistic_prompt(self, prompt: str, style: str) -> str:
        """Enhance prompt for artistic generation."""
        
        style_modifiers = {
            "artistic": "artistic masterpiece, creative, expressive",
            "photorealistic": "photorealistic, ultra-detailed, professional photography",
            "anime": "anime style, manga, Japanese art style",
            "abstract": "abstract art, conceptual, artistic interpretation"
        }
        
        style_mod = style_modifiers.get(style.lower(), "")
        
        if style_mod:
            return f"{prompt}, {style_mod}"
        else:
            return prompt
    
    def _aspect_ratio_to_resolution(self, aspect_ratio: str) -> str:
        """Convert aspect ratio to resolution string."""
        ratio_mapping = {
            "1:1": "1024x1024",
            "16:9": "1792x1024",
            "9:16": "1024x1792",
            "4:3": "1536x1152",
            "3:2": "1536x1024"
        }
        return ratio_mapping.get(aspect_ratio, "1024x1024")
    
    def _estimate_gpu_seconds(self, resolution: str) -> float:
        """Estimate GPU seconds used based on resolution."""
        gpu_mapping = {
            "1024x1024": 15.0,
            "2048x2048": 45.0
        }
        return gpu_mapping.get(resolution, 15.0)
    
    def _estimate_gpu_seconds_artistic(self, quality: str, stylization: int) -> float:
        """Estimate GPU seconds for artistic generation."""
        base_seconds = 20.0  # Base generation time
        
        if quality == "high":
            base_seconds *= 1.5
        
        # Higher stylization takes more compute
        stylization_multiplier = 1.0 + (stylization / 1000) * 0.5
        
        return base_seconds * stylization_multiplier
    
    def _estimate_file_size(self, resolution: str) -> float:
        """Estimate file size in MB."""
        size_mapping = {
            "1024x1024": 3.5,
            "2048x2048": 12.0
        }
        return size_mapping.get(resolution, 3.5)
    
    def _estimate_file_size_artistic(self, aspect_ratio: str, quality: str) -> float:
        """Estimate file size for artistic images."""
        base_sizes = {
            "1:1": 3.5,
            "16:9": 4.5,
            "9:16": 4.5,
            "4:3": 4.0,
            "3:2": 4.0
        }
        
        base_size = base_sizes.get(aspect_ratio, 3.5)
        
        if quality == "high":
            base_size *= 1.8
        
        return base_size