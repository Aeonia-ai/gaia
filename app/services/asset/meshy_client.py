import asyncio
import httpx
import base64
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import json
import sys
import os

from app.core.config import get_settings
from app.core import logger
from app.services.assets.advanced_pricing_service import AdvancedPricingService, UsageMetrics
from app.models.assets import (
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


class MeshyAIClient:
    """Meshy AI 3D asset generation client."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = getattr(self.settings, 'MESHY_API_KEY', None)
        self.base_url = "https://api.meshy.ai/v2"
        self.pricing_service = AdvancedPricingService()
        
        # Test mode configuration
        self.test_mode_key = "msy_dummy_api_key_for_test_mode_12345678"
        self.use_test_mode = '--meshy-test-mode' in sys.argv or \
                           os.getenv('MESHY_TEST_MODE', 'false').lower() == 'true'
        
        if self.use_test_mode:
            logger.info("Meshy AI running in TEST MODE - using dummy API key")
            self.api_key = self.test_mode_key
        elif not self.api_key:
            logger.warning("Meshy AI API key not found. 3D asset generation will be unavailable.")
    
    async def generate_3d_asset(
        self,
        prompt: str,
        asset_type: str = "model",
        style: str = "realistic",
        topology: str = "quad",
        quality: str = "medium"
    ) -> GeneratedAsset:
        """
        Generate a 3D asset using Meshy AI.
        
        Args:
            prompt: Text description of the 3D asset to generate
            asset_type: Type of 3D asset (model, character, prop, environment)
            style: Style preference (realistic, cartoon, low_poly, stylized)
            topology: Mesh topology (quad, triangle)
            quality: Asset quality (low, medium, high, ultra)
        """
        if not self.api_key:
            raise Exception("Meshy AI API key not configured")
        
        try:
            logger.info(f"Generating 3D asset with Meshy AI: {prompt[:100]}...")
            
            # Create text-to-3D generation task
            task_response = await self._create_generation_task(prompt, asset_type, style, topology, quality)
            task_id = task_response["result"]
            
            # Poll for completion
            asset_data = await self._poll_task_completion(task_id)
            
            # Calculate cost based on asset type and quality
            usage = UsageMetrics(
                credits_used=self._calculate_credits_used(asset_type, quality),
                requests_per_minute=1
            )
            
            # Determine operation type for pricing
            operation = f"text_to_3d_{asset_type}"
            if quality in ["high", "ultra"]:
                operation += "_with_texture"
            
            cost_calc = await self.pricing_service.calculate_meshy_cost(
                operation=operation,
                user_package="professional",  # Default package, could be from user settings
                usage=usage
            )
            
            generation_cost = cost_calc.total_cost
            
            # Create asset data
            asset_data_obj = AssetData(
                download_url=asset_data.get("model_urls", {}).get("glb", ""),
                preview_image_url=asset_data.get("thumbnail_url", ""),
                file_format="glb",
                file_size_mb=self._estimate_file_size(quality),
                quality_score=self._get_quality_score(quality),
                license_type=LicenseType.PROPRIETARY,
                attribution_required=False
            )
            
            # Create generated asset
            generated_asset = GeneratedAsset(
                generation_id=str(uuid.uuid4()),
                prompt=prompt,
                category=AssetCategory.THREE_D,
                style=style,
                title=f"Generated {asset_type} - {style}",
                description=prompt,
                asset_data=asset_data_obj,
                storage_info=StorageInfo(storage_type=StorageType.EXTERNAL),
                generation_cost=generation_cost,
                generation_time_ms=asset_data.get("generation_time_ms", 120000),
                generation_service="meshy_ai",
                quality_score=asset_data_obj.quality_score,
                metadata={
                    "prompt": prompt,
                    "asset_type": asset_type,
                    "style": style,
                    "topology": topology,
                    "quality": quality,
                    "task_id": task_id,
                    "model_urls": asset_data.get("model_urls", {}),
                    "generated_at": datetime.utcnow().isoformat(),
                    "credits_used": usage.credits_used
                }
            )
            
            # Track usage for billing
            await self.pricing_service.track_usage_realtime(
                provider="MeshyAI",
                operation="3d_generation",
                asset_id=generated_asset.generation_id,
                usage=usage,
                cost_calculation=cost_calc
            )
            
            logger.info(f"3D asset generated successfully: {generated_asset.generation_id} (cost: ${generation_cost:.4f}, credits: {usage.credits_used})")
            
            return generated_asset
            
        except Exception as e:
            logger.error(f"Meshy AI 3D generation failed: {e}")
            raise
    
    async def _create_generation_task(
        self,
        prompt: str,
        asset_type: str,
        style: str,
        topology: str,
        quality: str
    ) -> Dict[str, Any]:
        """Create a text-to-3D generation task."""
        
        # Map quality to Meshy AI parameters
        quality_settings = {
            "low": {"resolution": 128, "detail_level": "low"},
            "medium": {"resolution": 256, "detail_level": "medium"},
            "high": {"resolution": 512, "detail_level": "high"},
            "ultra": {"resolution": 1024, "detail_level": "ultra"}
        }
        
        settings = quality_settings.get(quality, quality_settings["medium"])
        
        payload = {
            "mode": "text_to_3d",
            "prompt": self._enhance_prompt_with_style(prompt, style, asset_type),
            "art_style": self._map_style_to_meshy(style),
            "negative_prompt": "low quality, blurry, distorted, broken",
            "ai_model": "meshy-4",
            "topology": topology,
            "target_polycount": self._get_target_polycount(quality),
            **settings
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/text-to-3d",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Meshy AI task creation error: {response.status_code} - {error_text}")
                raise Exception(f"Meshy AI task creation failed: {response.status_code}")
            
            return response.json()
    
    async def _poll_task_completion(self, task_id: str, max_wait_minutes: int = 10) -> Dict[str, Any]:
        """Poll task until completion or timeout."""
        
        start_time = datetime.utcnow()
        max_wait_seconds = max_wait_minutes * 60
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                # Check if we've exceeded max wait time
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > max_wait_seconds:
                    raise Exception(f"Task {task_id} timed out after {max_wait_minutes} minutes")
                
                # Get task status
                response = await client.get(
                    f"{self.base_url}/text-to-3d/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to check task status: {response.status_code}")
                
                task_data = response.json()
                status = task_data.get("status")
                
                if status == "SUCCEEDED":
                    # Add generation time to response
                    task_data["generation_time_ms"] = int(elapsed * 1000)
                    return task_data
                elif status == "FAILED":
                    error_msg = task_data.get("error", "Unknown error")
                    raise Exception(f"Task failed: {error_msg}")
                elif status in ["PENDING", "IN_PROGRESS"]:
                    logger.info(f"Task {task_id} status: {status}, waiting...")
                    await asyncio.sleep(10)  # Wait 10 seconds before next check
                else:
                    raise Exception(f"Unknown task status: {status}")
    
    def _enhance_prompt_with_style(self, prompt: str, style: str, asset_type: str) -> str:
        """Enhance the prompt with style and asset type guidance."""
        style_modifiers = {
            "realistic": "photorealistic, highly detailed, professional quality",
            "cartoon": "cartoon style, stylized, colorful, playful",
            "low_poly": "low poly, geometric, minimalist, game-ready",
            "stylized": "artistic, stylized, creative, unique design"
        }
        
        asset_modifiers = {
            "model": "3D model, clean geometry, well-proportioned",
            "character": "character model, rigged, game-ready, detailed",
            "prop": "prop, object, detailed, usable",
            "environment": "environment, scene, atmospheric, detailed"
        }
        
        style_mod = style_modifiers.get(style.lower(), "")
        asset_mod = asset_modifiers.get(asset_type.lower(), "")
        
        enhanced = prompt
        if asset_mod:
            enhanced = f"{asset_mod}, {enhanced}"
        if style_mod:
            enhanced = f"{enhanced}, {style_mod}"
        
        return enhanced
    
    def _map_style_to_meshy(self, style: str) -> str:
        """Map our style names to Meshy AI style names."""
        style_mapping = {
            "realistic": "realistic",
            "cartoon": "cartoon",
            "low_poly": "low-poly",
            "stylized": "stylized"
        }
        return style_mapping.get(style.lower(), "realistic")
    
    def _get_target_polycount(self, quality: str) -> int:
        """Get target polygon count based on quality."""
        polycount_mapping = {
            "low": 1000,
            "medium": 5000,
            "high": 15000,
            "ultra": 50000
        }
        return polycount_mapping.get(quality.lower(), 5000)
    
    def _calculate_credits_used(self, asset_type: str, quality: str) -> int:
        """Calculate credits used based on asset type and quality."""
        base_credits = {
            "model": 5,
            "character": 10,
            "prop": 5,
            "environment": 15
        }
        
        quality_multiplier = {
            "low": 1.0,
            "medium": 1.5,
            "high": 2.0,
            "ultra": 3.0
        }
        
        base = base_credits.get(asset_type.lower(), 5)
        multiplier = quality_multiplier.get(quality.lower(), 1.5)
        
        return int(base * multiplier)
    
    def _get_quality_score(self, quality: str) -> float:
        """Get quality score based on quality level."""
        quality_scores = {
            "low": 0.65,
            "medium": 0.80,
            "high": 0.90,
            "ultra": 0.95
        }
        return quality_scores.get(quality.lower(), 0.80)
    
    def _estimate_file_size(self, quality: str) -> float:
        """Estimate file size in MB based on quality."""
        size_estimates = {
            "low": 2.0,
            "medium": 8.0,
            "high": 25.0,
            "ultra": 75.0
        }
        return size_estimates.get(quality.lower(), 8.0)