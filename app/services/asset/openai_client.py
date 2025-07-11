import asyncio
import httpx
import base64
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from app.shared.config import settings
from app.shared.logging import get_logger
from .advanced_pricing_service import AdvancedPricingService, UsageMetrics
from .models.asset import (
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    AssetData,
    LicenseType,
    GeneratedAsset,
    AssetCategory,
    StorageInfo,
    StorageType
)

logger = get_logger(__name__)


class OpenAIImageClient:
    """OpenAI DALL-E image generation client."""
    
    def __init__(self):
        self.settings = settings
        self.api_key = self.settings.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
        self.model = "dall-e-3"  # Use DALL-E 3 by default
        self.pricing_service = AdvancedPricingService()
        
        if not self.api_key:
            logger.warning("OpenAI API key not found. Image generation will be unavailable.")
    
    async def generate_image(
        self,
        prompt: str,
        style: str = "realistic",
        quality: str = "standard",
        size: str = "1024x1024"
    ) -> GeneratedAsset:
        """
        Generate an image using OpenAI DALL-E.
        
        Args:
            prompt: Text description of the image to generate
            style: Style preference (realistic, cartoon, artistic, etc.)
            quality: Image quality (standard, hd)
            size: Image dimensions (1024x1024, 1792x1024, 1024x1792)
        """
        if not self.api_key:
            raise Exception("OpenAI API key not configured")
        
        try:
            logger.info(f"Generating image with DALL-E: {prompt[:100]}...")
            
            # Prepare the prompt with style guidance
            enhanced_prompt = self._enhance_prompt_with_style(prompt, style)
            
            # Make API request
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "prompt": enhanced_prompt,
                        "n": 1,
                        "size": size,
                        "quality": quality,
                        "response_format": "url"
                    }
                )
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"OpenAI API error: {response.status_code} - {error_text}")
                    raise Exception(f"OpenAI API error: {response.status_code}")
                
                result = response.json()
                
                if not result.get("data") or not result["data"][0].get("url"):
                    raise Exception("No image URL returned from OpenAI API")
                
                image_url = result["data"][0]["url"]
                
                # Create usage metrics for DALL-E billing
                usage = UsageMetrics(
                    image_count=1,
                    requests_per_minute=1  # In real app, track actual RPM
                )
                
                # Calculate cost using advanced pricing (tier-based + per-image)
                cost_calc = await self.pricing_service.calculate_dalle_cost(
                    usage=usage,
                    quality=quality,
                    resolution=size,
                    user_id=None  # Would pass actual user_id in production
                )
                
                generation_cost = cost_calc.total_cost
                
                # Create asset data
                asset_data = AssetData(
                    download_url=image_url,
                    preview_image_url=image_url,  # Same URL for preview
                    file_format="png",
                    file_size_mb=self._estimate_file_size(size, quality),
                    quality_score=0.95 if quality == "hd" else 0.85,
                    license_type=LicenseType.PROPRIETARY,
                    attribution_required=False
                )
                
                # Create generated asset
                generated_asset = GeneratedAsset(
                    generation_id=str(uuid.uuid4()),
                    prompt=prompt,
                    category=AssetCategory.IMAGE,
                    style=style,
                    title=f"Generated {style} image",
                    description=prompt,
                    asset_data=asset_data,
                    storage_info=StorageInfo(storage_type=StorageType.EXTERNAL),
                    generation_cost=generation_cost,
                    generation_time_ms=30000,  # Typical DALL-E generation time
                    generation_service="openai_dalle3",
                    quality_score=asset_data.quality_score,
                    metadata={
                        "prompt": prompt,
                        "enhanced_prompt": enhanced_prompt,
                        "style": style,
                        "quality": quality,
                        "size": size,
                        "model": self.model,
                        "generated_at": datetime.utcnow().isoformat()
                    }
                )
                
                # Track real-time usage for billing accuracy
                await self.pricing_service.track_usage_realtime(
                    provider="OpenAI",
                    operation="dalle3_generation",
                    asset_id=generated_asset.generation_id,
                    usage=usage,
                    cost_calculation=cost_calc
                )
                
                logger.info(f"Image generated successfully: {generated_asset.generation_id} (cost: ${generation_cost:.4f}) [Base: ${cost_calc.base_cost:.4f}, Tier: ${cost_calc.tier_fee:.4f}]")
                
                return generated_asset
                
        except Exception as e:
            logger.error(f"OpenAI image generation failed: {e}")
            raise
    
    def _enhance_prompt_with_style(self, prompt: str, style: str) -> str:
        """Enhance the prompt with style-specific guidance."""
        style_modifiers = {
            "realistic": "photorealistic, highly detailed, professional photography",
            "cartoon": "cartoon style, animated, colorful, playful",
            "artistic": "artistic, painterly, creative, expressive",
            "sci_fi": "science fiction, futuristic, high-tech, cyberpunk",
            "fantasy": "fantasy art, magical, mystical, ethereal",
            "minimalist": "minimalist, clean, simple, modern",
            "vintage": "vintage style, retro, classic, nostalgic"
        }
        
        modifier = style_modifiers.get(style.lower(), "")
        
        if modifier:
            return f"{prompt}, {modifier}"
        else:
            return prompt
    
    def _calculate_cost(self, quality: str, size: str) -> float:
        """Calculate the cost based on quality and size."""
        # DALL-E 3 pricing (as of 2024)
        if quality == "hd":
            if size == "1024x1024":
                return 0.040
            elif size in ["1792x1024", "1024x1792"]:
                return 0.080
        else:  # standard quality
            if size == "1024x1024":
                return 0.020
            elif size in ["1792x1024", "1024x1792"]:
                return 0.040
        
        return 0.020  # Default fallback
    
    def _estimate_file_size(self, size: str, quality: str) -> float:
        """Estimate file size in MB based on dimensions and quality."""
        # Base estimates for PNG format
        size_multipliers = {
            "1024x1024": 2.5,
            "1792x1024": 4.0,
            "1024x1792": 4.0
        }
        
        base_size = size_multipliers.get(size, 2.5)
        
        if quality == "hd":
            base_size *= 1.5  # HD images are typically larger
        
        return base_size


class StabilityAIClient:
    """Stability AI image generation client (alternative to DALL-E)."""
    
    def __init__(self):
        self.settings = settings
        self.api_key = getattr(self.settings, 'STABILITY_API_KEY', None)
        self.base_url = "https://api.stability.ai/v1"
        
        if not self.api_key:
            logger.warning("Stability AI API key not found. Alternative image generation unavailable.")
    
    async def generate_image(
        self,
        prompt: str,
        style: str = "realistic",
        width: int = 1024,
        height: int = 1024
    ) -> GeneratedAsset:
        """
        Generate an image using Stability AI.
        
        Args:
            prompt: Text description of the image to generate
            style: Style preference
            width: Image width
            height: Image height
        """
        if not self.api_key:
            raise Exception("Stability AI API key not configured")
        
        try:
            logger.info(f"Generating image with Stability AI: {prompt[:100]}...")
            
            # Prepare request payload
            payload = {
                "text_prompts": [
                    {
                        "text": prompt,
                        "weight": 1.0
                    }
                ],
                "cfg_scale": 7,
                "height": height,
                "width": width,
                "samples": 1,
                "steps": 30
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Stability AI error: {response.status_code} - {error_text}")
                    raise Exception(f"Stability AI error: {response.status_code}")
                
                result = response.json()
                
                if not result.get("artifacts") or not result["artifacts"][0].get("base64"):
                    raise Exception("No image data returned from Stability AI")
                
                # Decode base64 image (would need to upload to storage)
                image_b64 = result["artifacts"][0]["base64"]
                
                # Calculate cost (Stability AI pricing)
                generation_cost = 0.018  # Approximate cost per image
                
                # Create asset data (placeholder - would need actual storage URL)
                asset_data = AssetData(
                    download_url="https://placeholder.com/stability_generated.png",
                    preview_image_url="https://placeholder.com/stability_preview.png",
                    file_format="png",
                    file_size_mb=3.2,
                    quality_score=0.90,
                    license_type=LicenseType.PROPRIETARY,
                    attribution_required=False
                )
                
                generated_asset = GeneratedAsset(
                    generation_id=str(uuid.uuid4()),
                    prompt=prompt,
                    category=AssetCategory.IMAGE,
                    style=style,
                    title=f"Generated {style} image",
                    description=prompt,
                    asset_data=asset_data,
                    storage_info=StorageInfo(storage_type=StorageType.GENERATED),
                    generation_cost=generation_cost,
                    generation_time_ms=15000,
                    generation_service="stability_ai",
                    quality_score=0.90,
                    metadata={
                        "prompt": prompt,
                        "style": style,
                        "width": width,
                        "height": height,
                        "image_base64": image_b64,  # Store for upload to Supabase
                        "generated_at": datetime.utcnow().isoformat()
                    }
                )
                
                logger.info(f"Image generated with Stability AI: {generated_asset.generation_id}")
                
                return generated_asset
                
        except Exception as e:
            logger.error(f"Stability AI image generation failed: {e}")
            raise