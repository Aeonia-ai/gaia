from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import httpx
import asyncio

from app.shared.config import settings
from app.shared.logging import get_logger
from app.shared.supabase import get_supabase_client
from .models.asset import AssetCategory

logger = get_logger(__name__)


class PricingModel(str, Enum):
    """Different pricing models used by AI providers."""
    PER_IMAGE = "per_image"
    CREDIT_BASED = "credit_based"
    TOKEN_BASED = "token_based"
    TIER_BASED = "tier_based"
    COMPUTE_TIME = "compute_time"


@dataclass
class UsageMetrics:
    """Track usage metrics for different pricing models."""
    input_tokens: int = 0
    output_tokens: int = 0
    character_count: int = 0
    image_count: int = 0
    credits_consumed: int = 0
    compute_seconds: float = 0.0
    requests_per_minute: int = 0
    

@dataclass
class TierLimits:
    """Rate limits and tier thresholds."""
    tier_name: str
    monthly_fee: float
    max_requests_per_minute: int
    max_monthly_usage: Optional[int] = None


@dataclass
class CostCalculation:
    """Detailed cost breakdown for a generation request."""
    base_cost: float
    tier_fee: float = 0.0
    ancillary_costs: float = 0.0
    total_cost: float = 0.0
    credits_used: int = 0
    tokens_consumed: int = 0
    provider_response_id: Optional[str] = None
    cost_factors: Dict[str, Any] = None


class AdvancedPricingService:
    """
    Advanced pricing service implementing provider-specific billing models.
    
    Supports:
    - DALL-E tiered rate limits + per-image costs
    - Meshy credit-based pricing
    - Token-based pricing (GPT, etc.)
    - Real-time usage tracking
    - Dynamic tier upgrades
    """
    
    def __init__(self):
        self.settings = settings
        self.supabase = get_supabase_client()
        self._usage_cache = {}
        self._tier_cache = {}
        self._pricing_cache = {}
        
        # Initialize provider-specific configurations
        self._init_provider_configs()
    
    def _init_provider_configs(self):
        """Initialize provider-specific pricing configurations."""
        
        # DALL-E Tier Configuration (from OpenAI API docs)
        self.dalle_tiers = [
            TierLimits("tier_1", 5.00, 5, 15000),      # $5/month, 5 img/min, 15K/month
            TierLimits("tier_2", 50.00, 50, 150000),   # $50/month, 50 img/min, 150K/month  
            TierLimits("tier_3", 500.00, 500, 1500000) # $500/month, 500 img/min, 1.5M/month
        ]
        
        # Meshy Credit Packages (from Meshy pricing)
        self.meshy_packages = {
            "starter": {"credits": 200, "cost": 6.00},    # $6 for 200 credits
            "professional": {"credits": 1000, "cost": 20.00}, # $20 for 1000 credits  
            "enterprise": {"credits": 5000, "cost": 80.00}    # $80 for 5000 credits
        }
        
        # Operation credit costs for Meshy
        self.meshy_operations = {
            "text_to_3d": 5,
            "text_to_3d_with_texture": 15,
            "image_to_3d": 10,
            "mesh_refining": 8,
            "texture_generation": 3
        }
    
    async def calculate_dalle_cost(
        self,
        usage: UsageMetrics,
        quality: str = "standard",
        resolution: str = "1024x1024",
        user_id: Optional[str] = None
    ) -> CostCalculation:
        """
        Calculate DALL-E cost with tiered pricing model.
        
        Formula: total_cost = (image_count × per_image_rate) + tier_fee
        """
        try:
            # Get per-image rate based on quality/resolution
            per_image_rates = {
                ("standard", "1024x1024"): 0.040,
                ("hd", "1024x1024"): 0.080,
                ("standard", "1792x1024"): 0.080,
                ("hd", "1792x1024"): 0.120,
                ("standard", "1024x1792"): 0.080,
                ("hd", "1024x1792"): 0.120,
            }
            
            per_image_cost = per_image_rates.get((quality, resolution), 0.040)
            base_cost = usage.image_count * per_image_cost
            
            # Determine current tier and fee
            current_tier, tier_fee = await self._get_dalle_tier(user_id, usage.requests_per_minute)
            
            # Check if tier upgrade needed
            if usage.requests_per_minute > current_tier.max_requests_per_minute:
                new_tier, new_tier_fee = await self._upgrade_dalle_tier(user_id, usage.requests_per_minute)
                tier_fee = new_tier_fee
                logger.info(f"DALL-E tier upgraded to {new_tier.tier_name} for user {user_id}")
            
            total_cost = base_cost + tier_fee
            
            return CostCalculation(
                base_cost=base_cost,
                tier_fee=tier_fee,
                total_cost=total_cost,
                cost_factors={
                    "per_image_cost": per_image_cost,
                    "image_count": usage.image_count,
                    "quality": quality,
                    "resolution": resolution,
                    "tier": current_tier.tier_name,
                    "requests_per_minute": usage.requests_per_minute
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate DALL-E cost: {e}")
            raise
    
    async def calculate_meshy_cost(
        self,
        operation: str,
        user_package: str = "professional",
        usage: UsageMetrics = None
    ) -> CostCalculation:
        """
        Calculate Meshy cost using credit-based pricing.
        
        Formula: total_cost = (operation_credits × credit_cost)
        """
        try:
            # Get credits required for operation
            credits_required = self.meshy_operations.get(operation, 5)
            
            # Get credit cost based on user's package
            package_info = self.meshy_packages.get(user_package, self.meshy_packages["professional"])
            credit_cost = package_info["cost"] / package_info["credits"]  # Cost per credit
            
            base_cost = credits_required * credit_cost
            
            # Check if user needs to purchase more credits
            current_credits = await self._get_user_credits("meshy", user_package)
            if current_credits < credits_required:
                # Calculate cost to purchase new credit package
                ancillary_cost = package_info["cost"]
                logger.info(f"User needs new Meshy credit package: {user_package} (${ancillary_cost})")
            else:
                ancillary_cost = 0.0
            
            total_cost = base_cost + ancillary_cost
            
            return CostCalculation(
                base_cost=base_cost,
                ancillary_costs=ancillary_cost,
                total_cost=total_cost,
                credits_used=credits_required,
                cost_factors={
                    "operation": operation,
                    "credits_required": credits_required,
                    "credit_cost": credit_cost,
                    "user_package": user_package,
                    "current_credits": current_credits,
                    "credit_package_cost": package_info["cost"]
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate Meshy cost: {e}")
            raise
    
    async def calculate_token_based_cost(
        self,
        usage: UsageMetrics,
        provider: str = "openai",
        model: str = "gpt-4"
    ) -> CostCalculation:
        """
        Calculate cost for token-based pricing (GPT, Claude, etc.).
        
        Note: 1 token ≈ 4 characters for English text
        """
        try:
            # Token pricing rates (per 1K tokens)
            token_rates = {
                ("openai", "gpt-4"): {"input": 0.03, "output": 0.06},
                ("openai", "gpt-3.5-turbo"): {"input": 0.001, "output": 0.002},
                ("anthropic", "claude-3"): {"input": 0.015, "output": 0.075},
                ("google", "gemini-pro"): {"input": 0.00025, "output": 0.0005},
            }
            
            rates = token_rates.get((provider, model), {"input": 0.001, "output": 0.002})
            
            input_cost = (usage.input_tokens / 1000) * rates["input"]
            output_cost = (usage.output_tokens / 1000) * rates["output"]
            base_cost = input_cost + output_cost
            
            # Add grounding/retrieval costs if applicable
            ancillary_cost = 0.0
            if provider == "google" and usage.character_count > 0:
                # Google Grounded Generation: $2.50/1k requests
                ancillary_cost += 2.50 / 1000
                # Vertex AI Search: $4.00/1k requests  
                ancillary_cost += 4.00 / 1000
            
            total_cost = base_cost + ancillary_cost
            
            return CostCalculation(
                base_cost=base_cost,
                ancillary_costs=ancillary_cost,
                total_cost=total_cost,
                tokens_consumed=usage.input_tokens + usage.output_tokens,
                cost_factors={
                    "provider": provider,
                    "model": model,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "input_cost": input_cost,
                    "output_cost": output_cost,
                    "rates": rates
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate token-based cost: {e}")
            raise
    
    async def calculate_midjourney_cost(
        self,
        usage: UsageMetrics,
        resolution: str,
        is_seamless: bool,
        user_id: Optional[str] = None
    ) -> CostCalculation:
        """
        Calculate Midjourney cost based on subscription + compute usage.
        
        Formula: Base subscription + GPU compute time + seamless/quality modifiers
        """
        try:
            # Midjourney pricing tiers (monthly)
            subscription_tiers = {
                "basic": {"cost": 10.0, "gpu_hours": 3.33},
                "standard": {"cost": 30.0, "gpu_hours": 15.0},
                "pro": {"cost": 60.0, "gpu_hours": 30.0},
                "mega": {"cost": 120.0, "gpu_hours": 60.0}
            }
            
            # Per-minute GPU costs for overages
            gpu_cost_per_minute = 0.50
            
            # Resolution multipliers
            resolution_multipliers = {
                "1024x1024": 1.0,
                "1792x1024": 1.5,
                "1024x1792": 1.5,
                "2048x2048": 2.5,
                "1536x1152": 1.8,
                "1536x1024": 1.6
            }
            
            # Calculate base cost
            resolution_multiplier = resolution_multipliers.get(resolution, 1.0)
            gpu_minutes = usage.gpu_seconds / 60.0 if hasattr(usage, 'gpu_seconds') and usage.gpu_seconds else 1.5
            
            # Apply resolution multiplier to GPU time
            adjusted_gpu_minutes = gpu_minutes * resolution_multiplier
            
            # Seamless texture generation uses more compute
            if is_seamless:
                adjusted_gpu_minutes *= 1.3
            
            # Calculate cost (assume standard tier usage)
            tier_allocation = subscription_tiers["standard"]["gpu_hours"] * 60  # Convert to minutes
            
            if adjusted_gpu_minutes <= tier_allocation:
                # Within tier limits
                base_cost = 0.0  # Covered by subscription
                overage_cost = 0.0
                tier_fee = subscription_tiers["standard"]["cost"] / 100  # Amortized per generation
            else:
                # Overage charges
                overage_minutes = adjusted_gpu_minutes - tier_allocation
                base_cost = 0.0
                overage_cost = overage_minutes * gpu_cost_per_minute
                tier_fee = subscription_tiers["standard"]["cost"] / 100
            
            total_cost = base_cost + overage_cost + tier_fee
            
            return CostCalculation(
                base_cost=base_cost,
                tier_fee=tier_fee,
                ancillary_costs=overage_cost,
                total_cost=total_cost,
                credits_used=0,
                cost_factors={
                    "resolution": resolution,
                    "resolution_multiplier": resolution_multiplier,
                    "gpu_minutes": gpu_minutes,
                    "adjusted_gpu_minutes": adjusted_gpu_minutes,
                    "is_seamless": is_seamless,
                    "tier": "standard",
                    "overage_minutes": adjusted_gpu_minutes - tier_allocation if adjusted_gpu_minutes > tier_allocation else 0,
                    "overage_cost": overage_cost
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate Midjourney cost: {e}")
            raise
    
    async def calculate_mubert_cost(
        self,
        usage: UsageMetrics,
        duration_seconds: int,
        quality: str,
        is_soundtrack: bool = False,
        user_id: Optional[str] = None
    ) -> CostCalculation:
        """
        Calculate Mubert cost based on duration and quality.
        
        Formula: Base rate per second + quality multiplier + soundtrack premium
        """
        try:
            # Mubert pricing (per second of audio)
            base_rates = {
                "standard": 0.005,  # $0.005 per second
                "high": 0.008       # $0.008 per second
            }
            
            # Quality multipliers
            quality_multipliers = {
                "standard": 1.0,
                "high": 1.6
            }
            
            # Soundtrack premium (longer, more complex compositions)
            soundtrack_multiplier = 2.0 if is_soundtrack else 1.0
            
            # Calculate base cost
            base_rate = base_rates.get(quality, base_rates["standard"])
            quality_multiplier = quality_multipliers.get(quality, 1.0)
            
            # Base cost calculation
            base_cost = duration_seconds * base_rate * quality_multiplier
            
            # Apply soundtrack premium
            adjusted_cost = base_cost * soundtrack_multiplier
            
            # Minimum charge (prevent very cheap micro-generations)
            minimum_charge = 0.05  # $0.05 minimum
            total_cost = max(adjusted_cost, minimum_charge)
            
            # No additional fees for Mubert
            tier_fee = 0.0
            ancillary_costs = 0.0
            
            return CostCalculation(
                base_cost=base_cost,
                tier_fee=tier_fee,
                ancillary_costs=ancillary_costs,
                total_cost=total_cost,
                credits_used=0,
                cost_factors={
                    "duration_seconds": duration_seconds,
                    "quality": quality,
                    "quality_multiplier": quality_multiplier,
                    "is_soundtrack": is_soundtrack,
                    "soundtrack_multiplier": soundtrack_multiplier,
                    "base_rate": base_rate,
                    "minimum_charge": minimum_charge,
                    "adjusted_cost": adjusted_cost
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate Mubert cost: {e}")
            raise
    
    async def track_usage_realtime(
        self,
        provider: str,
        operation: str,
        asset_id: str,
        usage: UsageMetrics,
        cost_calculation: CostCalculation
    ):
        """
        Track real-time usage and costs for billing accuracy.
        """
        try:
            if self.supabase.available:
                # Log detailed usage metrics
                usage_record = {
                    "provider_name": provider,
                    "operation": operation,
                    "asset_id": asset_id,
                    "usage_metrics": {
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "character_count": usage.character_count,
                        "image_count": usage.image_count,
                        "credits_consumed": usage.credits_consumed,
                        "compute_seconds": usage.compute_seconds,
                        "requests_per_minute": usage.requests_per_minute
                    },
                    "cost_breakdown": {
                        "base_cost": cost_calculation.base_cost,
                        "tier_fee": cost_calculation.tier_fee,
                        "ancillary_costs": cost_calculation.ancillary_costs,
                        "total_cost": cost_calculation.total_cost,
                        "cost_factors": cost_calculation.cost_factors
                    },
                    "billing_period": datetime.utcnow().strftime("%Y-%m"),
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Store in usage tracking table
                await self.supabase.insert('detailed_usage_tracking', usage_record)
                
                logger.info(f"Tracked usage: {provider} {operation} - ${cost_calculation.total_cost:.4f}")
                
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")
    
    async def _get_dalle_tier(self, user_id: Optional[str], requests_per_minute: int) -> Tuple[TierLimits, float]:
        """Get current DALL-E tier and monthly fee for user."""
        
        # For demo, return appropriate tier based on usage
        for tier in self.dalle_tiers:
            if requests_per_minute <= tier.max_requests_per_minute:
                return tier, tier.monthly_fee
        
        # Default to highest tier
        return self.dalle_tiers[-1], self.dalle_tiers[-1].monthly_fee
    
    async def _upgrade_dalle_tier(self, user_id: Optional[str], requests_per_minute: int) -> Tuple[TierLimits, float]:
        """Upgrade DALL-E tier when rate limits exceeded."""
        
        for tier in self.dalle_tiers:
            if requests_per_minute <= tier.max_requests_per_minute:
                # In real implementation, update user's tier in database
                logger.info(f"Upgrading user {user_id} to DALL-E {tier.tier_name}")
                return tier, tier.monthly_fee
        
        return self.dalle_tiers[-1], self.dalle_tiers[-1].monthly_fee
    
    async def _get_user_credits(self, provider: str, package: str) -> int:
        """Get user's current credit balance."""
        
        # In real implementation, query user's credit balance from database
        # For demo, return random balance
        return 500  # Placeholder
    
    async def get_cost_prediction(
        self,
        provider: str,
        asset_category: AssetCategory,
        estimated_usage: UsageMetrics,
        user_context: Optional[Dict[str, Any]] = None
    ) -> CostCalculation:
        """
        Predict costs before executing generation request.
        """
        try:
            if provider.lower() == "openai" and asset_category == AssetCategory.IMAGE:
                return await self.calculate_dalle_cost(
                    estimated_usage,
                    user_context.get("quality", "standard") if user_context else "standard",
                    user_context.get("resolution", "1024x1024") if user_context else "1024x1024",
                    user_context.get("user_id") if user_context else None
                )
                
            elif provider.lower() == "meshy" and asset_category in [AssetCategory.PROP, AssetCategory.CHARACTER]:
                operation = user_context.get("operation", "text_to_3d") if user_context else "text_to_3d"
                package = user_context.get("package", "professional") if user_context else "professional"
                return await self.calculate_meshy_cost(operation, package, estimated_usage)
                
            else:
                # Default to token-based pricing
                return await self.calculate_token_based_cost(
                    estimated_usage,
                    provider.lower(),
                    user_context.get("model", "gpt-4") if user_context else "gpt-4"
                )
                
        except Exception as e:
            logger.error(f"Failed to predict cost: {e}")
            raise