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


class MubertClient:
    """Mubert AI audio generation client."""
    
    def __init__(self):
        self.settings = settings
        self.api_key = getattr(self.settings, 'MUBERT_API_KEY', None)
        self.base_url = "https://api-b2b.mubert.com/v2"
        self.pricing_service = AdvancedPricingService()
        
        if not self.api_key:
            logger.warning("Mubert API key not found. Audio generation will be unavailable.")
    
    async def generate_audio(
        self,
        prompt: str,
        duration: int = 30,
        genre: str = "ambient",
        mood: str = "calm",
        format: str = "wav",
        quality: str = "standard"
    ) -> GeneratedAsset:
        """
        Generate audio using Mubert AI.
        
        Args:
            prompt: Text description of the audio to generate
            duration: Duration in seconds (15-300)
            genre: Music genre (ambient, electronic, classical, rock, etc.)
            mood: Mood/emotion (calm, energetic, mysterious, upbeat, etc.)
            format: Audio format (wav, mp3, ogg)
            quality: Audio quality (standard, high)
        """
        if not self.api_key:
            raise Exception("Mubert API key not configured")
        
        # Validate duration
        duration = max(15, min(300, duration))  # Clamp to valid range
        
        try:
            logger.info(f"Generating audio with Mubert: {prompt[:100]}... ({duration}s, {genre})")
            
            # Create generation task
            task_response = await self._create_audio_task(prompt, duration, genre, mood, format, quality)
            task_id = task_response["data"]["id"]
            
            # Poll for completion
            audio_data = await self._poll_task_completion(task_id)
            
            # Calculate cost based on duration and quality
            usage = UsageMetrics(
                audio_seconds=duration,
                requests_per_minute=1
            )
            
            cost_calc = await self.pricing_service.calculate_mubert_cost(
                usage=usage,
                duration_seconds=duration,
                quality=quality,
                user_id=None
            )
            
            generation_cost = cost_calc.total_cost
            
            # Create asset data
            asset_data = AssetData(
                download_url=audio_data.get("download_url", ""),
                preview_image_url=audio_data.get("waveform_url", ""),  # Waveform as preview
                file_format=format.lower(),
                file_size_mb=self._estimate_file_size(duration, format, quality),
                quality_score=self._get_quality_score(quality),
                license_type=LicenseType.ROYALTY_FREE,  # Mubert provides royalty-free music
                attribution_required=False
            )
            
            # Create generated asset
            generated_asset = GeneratedAsset(
                generation_id=str(uuid.uuid4()),
                prompt=prompt,
                category=AssetCategory.AUDIO,
                style=f"{genre}-{mood}",
                title=f"Generated {genre} audio - {mood}",
                description=f"{prompt} ({duration}s {genre} music)",
                asset_data=asset_data,
                storage_info=StorageInfo(storage_type=StorageType.EXTERNAL),
                generation_cost=generation_cost,
                generation_time_ms=audio_data.get("generation_time_ms", 30000),
                generation_service="mubert",
                quality_score=asset_data.quality_score,
                metadata={
                    "prompt": prompt,
                    "enhanced_prompt": audio_data.get("enhanced_prompt", prompt),
                    "duration_seconds": duration,
                    "genre": genre,
                    "mood": mood,
                    "format": format,
                    "quality": quality,
                    "task_id": task_id,
                    "bpm": audio_data.get("bpm"),
                    "key": audio_data.get("key"),
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            # Track usage for billing
            await self.pricing_service.track_usage_realtime(
                provider="Mubert",
                operation="audio_generation",
                asset_id=generated_asset.generation_id,
                usage=usage,
                cost_calculation=cost_calc
            )
            
            logger.info(f"Audio generated successfully: {generated_asset.generation_id} (cost: ${generation_cost:.4f}, duration: {duration}s)")
            
            return generated_asset
            
        except Exception as e:
            logger.error(f"Mubert audio generation failed: {e}")
            raise
    
    async def generate_soundtrack(
        self,
        prompt: str,
        duration: int = 60,
        genre: str = "cinematic",
        intensity: str = "medium",
        loop: bool = True,
        format: str = "wav"
    ) -> GeneratedAsset:
        """
        Generate a soundtrack/background music using Mubert AI.
        
        Args:
            prompt: Description of the soundtrack needed
            duration: Duration in seconds (30-600 for soundtracks)
            genre: Music genre (cinematic, ambient, electronic, orchestral)
            intensity: Intensity level (low, medium, high, epic)
            loop: Whether the audio should loop seamlessly
            format: Audio format (wav, mp3)
        """
        if not self.api_key:
            raise Exception("Mubert API key not configured")
        
        # Validate duration for soundtracks
        duration = max(30, min(600, duration))
        
        try:
            logger.info(f"Generating soundtrack with Mubert: {prompt[:100]}... ({duration}s)")
            
            # Create soundtrack generation task
            task_response = await self._create_soundtrack_task(prompt, duration, genre, intensity, loop, format)
            task_id = task_response["data"]["id"]
            
            # Poll for completion
            audio_data = await self._poll_task_completion(task_id)
            
            # Calculate cost (soundtracks are more expensive)
            usage = UsageMetrics(
                audio_seconds=duration,
                requests_per_minute=1
            )
            
            cost_calc = await self.pricing_service.calculate_mubert_cost(
                usage=usage,
                duration_seconds=duration,
                quality="high",  # Soundtracks are high quality
                is_soundtrack=True,
                user_id=None
            )
            
            generation_cost = cost_calc.total_cost
            
            # Create asset data
            asset_data = AssetData(
                download_url=audio_data.get("download_url", ""),
                preview_image_url=audio_data.get("waveform_url", ""),
                file_format=format.lower(),
                file_size_mb=self._estimate_file_size(duration, format, "high"),
                quality_score=0.90,  # Soundtracks are high quality
                license_type=LicenseType.ROYALTY_FREE,
                attribution_required=False
            )
            
            # Create generated asset
            generated_asset = GeneratedAsset(
                generation_id=str(uuid.uuid4()),
                prompt=prompt,
                category=AssetCategory.AUDIO,
                style=f"{genre}-soundtrack",
                title=f"Generated {genre} soundtrack - {intensity} intensity",
                description=f"{prompt} ({duration}s {genre} soundtrack)",
                asset_data=asset_data,
                storage_info=StorageInfo(storage_type=StorageType.EXTERNAL),
                generation_cost=generation_cost,
                generation_time_ms=audio_data.get("generation_time_ms", 45000),
                generation_service="mubert",
                quality_score=asset_data.quality_score,
                metadata={
                    "prompt": prompt,
                    "duration_seconds": duration,
                    "genre": genre,
                    "intensity": intensity,
                    "loop": loop,
                    "format": format,
                    "is_soundtrack": True,
                    "task_id": task_id,
                    "bpm": audio_data.get("bpm"),
                    "key": audio_data.get("key"),
                    "instruments": audio_data.get("instruments", []),
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            # Track usage for billing
            await self.pricing_service.track_usage_realtime(
                provider="Mubert",
                operation="soundtrack_generation",
                asset_id=generated_asset.generation_id,
                usage=usage,
                cost_calculation=cost_calc
            )
            
            logger.info(f"Soundtrack generated successfully: {generated_asset.generation_id} (cost: ${generation_cost:.4f})")
            
            return generated_asset
            
        except Exception as e:
            logger.error(f"Mubert soundtrack generation failed: {e}")
            raise
    
    async def _create_audio_task(
        self,
        prompt: str,
        duration: int,
        genre: str,
        mood: str,
        format: str,
        quality: str
    ) -> Dict[str, Any]:
        """Create an audio generation task."""
        
        # Enhance prompt with genre and mood
        enhanced_prompt = self._enhance_audio_prompt(prompt, genre, mood)
        
        # Map quality to Mubert parameters
        quality_settings = {
            "standard": {"bitrate": 128, "sample_rate": 44100},
            "high": {"bitrate": 320, "sample_rate": 48000}
        }
        
        settings = quality_settings.get(quality, quality_settings["standard"])
        
        payload = {
            "method": "GenerateTrackByTags",
            "params": {
                "tags": self._generate_tags(enhanced_prompt, genre, mood),
                "duration": duration,
                "format": format.upper(),
                "bitrate": settings["bitrate"],
                "sample_rate": settings["sample_rate"],
                "mode": "track"  # Single track generation
            }
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/generate",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Mubert task creation error: {response.status_code} - {error_text}")
                raise Exception(f"Mubert task creation failed: {response.status_code}")
            
            return response.json()
    
    async def _create_soundtrack_task(
        self,
        prompt: str,
        duration: int,
        genre: str,
        intensity: str,
        loop: bool,
        format: str
    ) -> Dict[str, Any]:
        """Create a soundtrack generation task."""
        
        # Enhance prompt for soundtrack
        enhanced_prompt = self._enhance_soundtrack_prompt(prompt, genre, intensity)
        
        payload = {
            "method": "GenerateTrackByTags",
            "params": {
                "tags": self._generate_soundtrack_tags(enhanced_prompt, genre, intensity),
                "duration": duration,
                "format": format.upper(),
                "bitrate": 320,  # High quality for soundtracks
                "sample_rate": 48000,
                "mode": "soundtrack",
                "loop": loop,
                "fade_in": 2.0,  # 2 second fade in
                "fade_out": 3.0  # 3 second fade out
            }
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:  # Longer timeout for soundtracks
            response = await client.post(
                f"{self.base_url}/generate",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Mubert soundtrack creation error: {response.status_code} - {error_text}")
                raise Exception(f"Mubert soundtrack creation failed: {response.status_code}")
            
            return response.json()
    
    async def _poll_task_completion(self, task_id: str, max_wait_minutes: int = 3) -> Dict[str, Any]:
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
                    f"{self.base_url}/task/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to check task status: {response.status_code}")
                
                task_data = response.json()
                status = task_data.get("data", {}).get("status")
                
                if status == "completed":
                    task_data["generation_time_ms"] = int(elapsed * 1000)
                    return task_data.get("data", {})
                elif status == "failed":
                    error_msg = task_data.get("data", {}).get("error", "Unknown error")
                    raise Exception(f"Task failed: {error_msg}")
                elif status in ["pending", "processing"]:
                    logger.info(f"Task {task_id} status: {status}, waiting...")
                    await asyncio.sleep(3)  # Wait 3 seconds before next check
                else:
                    raise Exception(f"Unknown task status: {status}")
    
    def _enhance_audio_prompt(self, prompt: str, genre: str, mood: str) -> str:
        """Enhance prompt for audio generation."""
        return f"{prompt} in {genre} style with {mood} mood"
    
    def _enhance_soundtrack_prompt(self, prompt: str, genre: str, intensity: str) -> str:
        """Enhance prompt for soundtrack generation."""
        return f"{prompt} - {genre} soundtrack with {intensity} intensity, cinematic quality"
    
    def _generate_tags(self, prompt: str, genre: str, mood: str) -> List[str]:
        """Generate tags for Mubert API based on prompt, genre, and mood."""
        
        # Base tags
        tags = [genre.lower(), mood.lower()]
        
        # Add genre-specific tags
        genre_tags = {
            "ambient": ["ambient", "atmospheric", "ethereal", "peaceful"],
            "electronic": ["electronic", "synthesizer", "digital", "modern"],
            "classical": ["classical", "orchestral", "piano", "strings"],
            "rock": ["rock", "guitar", "drums", "energy"],
            "jazz": ["jazz", "smooth", "sophisticated", "improvisation"],
            "hip_hop": ["hip-hop", "beats", "urban", "rhythm"],
            "pop": ["pop", "catchy", "mainstream", "melodic"]
        }
        
        # Add mood-specific tags
        mood_tags = {
            "calm": ["relaxing", "peaceful", "meditative", "soft"],
            "energetic": ["upbeat", "dynamic", "powerful", "exciting"],
            "mysterious": ["dark", "mysterious", "suspenseful", "intriguing"],
            "upbeat": ["happy", "positive", "cheerful", "optimistic"],
            "dramatic": ["intense", "dramatic", "emotional", "powerful"],
            "romantic": ["romantic", "love", "tender", "intimate"]
        }
        
        # Add relevant tags
        if genre.lower() in genre_tags:
            tags.extend(genre_tags[genre.lower()][:2])  # Add top 2 genre tags
        
        if mood.lower() in mood_tags:
            tags.extend(mood_tags[mood.lower()][:2])  # Add top 2 mood tags
        
        # Extract keywords from prompt
        prompt_words = prompt.lower().split()
        relevant_words = [word for word in prompt_words if len(word) > 3 and word.isalpha()]
        tags.extend(relevant_words[:3])  # Add top 3 relevant words
        
        return list(set(tags))  # Remove duplicates
    
    def _generate_soundtrack_tags(self, prompt: str, genre: str, intensity: str) -> List[str]:
        """Generate tags specifically for soundtrack generation."""
        
        tags = [genre.lower(), "soundtrack", intensity.lower()]
        
        # Soundtrack-specific tags
        soundtrack_tags = {
            "cinematic": ["cinematic", "epic", "orchestral", "film"],
            "ambient": ["ambient", "atmospheric", "background", "subtle"],
            "electronic": ["electronic", "futuristic", "synthesizer", "modern"],
            "orchestral": ["orchestral", "symphony", "classical", "grandiose"]
        }
        
        intensity_tags = {
            "low": ["subtle", "minimal", "quiet", "gentle"],
            "medium": ["moderate", "balanced", "steady", "controlled"],
            "high": ["intense", "powerful", "dramatic", "strong"],
            "epic": ["epic", "grandiose", "majestic", "heroic"]
        }
        
        if genre.lower() in soundtrack_tags:
            tags.extend(soundtrack_tags[genre.lower()])
        
        if intensity.lower() in intensity_tags:
            tags.extend(intensity_tags[intensity.lower()][:2])
        
        return list(set(tags))
    
    def _get_quality_score(self, quality: str) -> float:
        """Get quality score based on quality level."""
        quality_scores = {
            "standard": 0.75,
            "high": 0.90
        }
        return quality_scores.get(quality.lower(), 0.75)
    
    def _estimate_file_size(self, duration: int, format: str, quality: str) -> float:
        """Estimate file size in MB based on duration, format, and quality."""
        
        # Base size per second in MB
        format_base_sizes = {
            "wav": {"standard": 0.17, "high": 0.23},  # Uncompressed
            "mp3": {"standard": 0.016, "high": 0.040},  # Compressed
            "ogg": {"standard": 0.014, "high": 0.035}   # Compressed
        }
        
        format_lower = format.lower()
        if format_lower not in format_base_sizes:
            format_lower = "wav"  # Default to WAV
        
        base_size_per_second = format_base_sizes[format_lower].get(quality, 0.17)
        
        return duration * base_size_per_second