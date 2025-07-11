from typing import List, Optional, Dict, Any
from app.models.assets import (
    AssetRequest, 
    DatabaseAsset, 
    OptimizationStrategy,
    CostBreakdown,
    AssetSource
)
from app.core.config import get_settings
from app.core import logger
from app.services.assets.pricing_service import PricingService


class CostOptimizer:
    def __init__(self):
        self.settings = get_settings()
        self.pricing_service = PricingService()
        
        # Base costs - will be overridden by database pricing
        self.DATABASE_COST = 0.00
        self.SEARCH_COST_PER_QUERY = 0.0001 # Minimal embedding search cost
        self.STORAGE_COST_PER_MB = 0.00     # Supabase storage included in plan

    async def calculate_optimal_strategy(
        self, 
        request: AssetRequest, 
        database_results: List[DatabaseAsset]
    ) -> OptimizationStrategy:
        strategies = []
        
        # Strategy 1: Database hit (if we have good matches)
        if database_results:
            best_match = max(database_results, key=lambda x: x.quality_score)
            if best_match.quality_score >= 0.8:
                strategies.append(OptimizationStrategy(
                    strategy_type="database",
                    estimated_cost=self.DATABASE_COST + self.SEARCH_COST_PER_QUERY,
                    estimated_time_ms=100,
                    confidence_score=best_match.quality_score,
                    reasoning=f"High-quality database match found (score: {best_match.quality_score:.2f})"
                ))
        
        # Strategy 2: Hybrid approach (database + modification)
        if database_results:
            best_match = max(database_results, key=lambda x: x.quality_score)
            if best_match.quality_score >= 0.6:
                modification_cost = await self._estimate_modification_cost(request, best_match)
                strategies.append(OptimizationStrategy(
                    strategy_type="hybrid",
                    estimated_cost=modification_cost + self.SEARCH_COST_PER_QUERY,
                    estimated_time_ms=2000,
                    confidence_score=best_match.quality_score * 0.9,
                    fallback_strategy="generation",
                    reasoning=f"Good database match (score: {best_match.quality_score:.2f}) with modifications"
                ))
        
        # Strategy 3: Full generation
        generation_cost = await self._estimate_generation_cost(request)
        strategies.append(OptimizationStrategy(
            strategy_type="generation",
            estimated_cost=generation_cost,
            estimated_time_ms=8000,
            confidence_score=0.85,
            reasoning="Full AI generation for custom requirements"
        ))
        
        # Choose best strategy based on cost, time, and user preferences
        return self._select_best_strategy(strategies, request)

    async def _estimate_modification_cost(self, request: AssetRequest, base_asset: DatabaseAsset) -> float:
        # For modifications, we typically use cheaper operations
        provider = "OpenAI"  # Default to OpenAI for image variations
        
        if request.category.value in ["image", "texture"]:
            # Use DALL-E 2 variations which are cheaper
            cost = await self.pricing_service.get_generation_cost(
                provider="OpenAI",
                category=request.category,
                quality="variation",
                size={"width": 1024, "height": 1024}
            )
        else:
            # For other types, use the standard generation cost with a modifier
            base_cost = await self.pricing_service.get_generation_cost(
                provider="OpenAI",
                category=request.category,
                quality="standard"
            )
            cost = base_cost * 0.7  # Modifications typically cost 70% of generation
        
        return min(cost, self.settings.MAX_GENERATION_COST_PER_ASSET * 0.5)

    async def _estimate_generation_cost(self, request: AssetRequest) -> float:
        # Determine provider based on category
        provider_map = {
            "image": "OpenAI",
            "texture": "OpenAI",
            "audio": "ElevenLabs",
            "prop": "Meshy AI",
            "character": "Meshy AI",
            "environment": "Meshy AI",
            "animation": "Meshy AI"
        }
        
        provider = provider_map.get(request.category.value, "OpenAI")
        
        # Determine quality
        quality = "standard"
        if request.requirements:
            if request.requirements.quality.value in ["high", "ultra"]:
                quality = "hd"
            elif request.requirements.quality.value == "low":
                quality = "low"
        
        # Get size parameters for image generation
        size = None
        if request.category.value in ["image", "texture"]:
            size = {"width": 1024, "height": 1024}  # Default size
        
        # Fetch current pricing from database
        cost = await self.pricing_service.get_generation_cost(
            provider=provider,
            category=request.category,
            quality=quality,
            size=size
        )
        
        return min(cost, self.settings.MAX_GENERATION_COST_PER_ASSET)

    def _select_best_strategy(self, strategies: List[OptimizationStrategy], request: AssetRequest) -> OptimizationStrategy:
        # Filter by user preferences
        max_cost = request.preferences.max_cost if request.preferences else self.settings.MAX_GENERATION_COST_PER_ASSET
        affordable_strategies = [s for s in strategies if s.estimated_cost <= max_cost]
        
        if not affordable_strategies:
            logger.warning(f"No strategies within budget ${max_cost:.2f}, using cheapest available")
            affordable_strategies = [min(strategies, key=lambda x: x.estimated_cost)]
        
        # Score strategies based on cost, time, and confidence
        for strategy in affordable_strategies:
            cost_score = 1.0 - (strategy.estimated_cost / max_cost)
            time_score = 1.0 - min(strategy.estimated_time_ms / 10000, 1.0)
            
            # Weighted scoring
            strategy.confidence_score = (
                strategy.confidence_score * 0.5 +  # Original confidence
                cost_score * 0.3 +                 # Cost efficiency
                time_score * 0.2                   # Time efficiency
            )
        
        # Return highest scoring strategy
        best_strategy = max(affordable_strategies, key=lambda x: x.confidence_score)
        logger.info(f"Selected strategy: {best_strategy.strategy_type}, cost: ${best_strategy.estimated_cost:.4f}, confidence: {best_strategy.confidence_score:.2f}")
        
        return best_strategy

    def calculate_cost_breakdown(
        self, 
        strategy: OptimizationStrategy, 
        actual_costs: Dict[str, float] = None
    ) -> CostBreakdown:
        if actual_costs is None:
            actual_costs = {}
        
        search_cost = actual_costs.get("search", self.SEARCH_COST_PER_QUERY)
        modification_cost = actual_costs.get("modification", 0.0)
        generation_cost = actual_costs.get("generation", 0.0)
        storage_cost = actual_costs.get("storage", 0.0)
        
        if strategy.strategy_type == "database":
            pass  # Only search cost
        elif strategy.strategy_type == "hybrid":
            if modification_cost == 0.0:
                modification_cost = strategy.estimated_cost - search_cost
        elif strategy.strategy_type == "generation":
            if generation_cost == 0.0:
                generation_cost = strategy.estimated_cost - search_cost
        
        total_cost = search_cost + modification_cost + generation_cost + storage_cost
        
        return CostBreakdown(
            search_cost=search_cost,
            modification_cost=modification_cost,
            generation_cost=generation_cost,
            storage_cost=storage_cost,
            total_cost=total_cost
        )

    def validate_cost_budget(self, estimated_cost: float, session_id: str = None) -> bool:
        if estimated_cost > self.settings.MAX_GENERATION_COST_PER_ASSET:
            logger.warning(f"Estimated cost ${estimated_cost:.4f} exceeds maximum ${self.settings.MAX_GENERATION_COST_PER_ASSET:.4f}")
            return False
        return True

    def get_cost_summary(self, cost_breakdown: CostBreakdown) -> Dict[str, Any]:
        return {
            "total_cost_usd": cost_breakdown.total_cost,
            "breakdown": {
                "search": cost_breakdown.search_cost,
                "modification": cost_breakdown.modification_cost,
                "generation": cost_breakdown.generation_cost,
                "storage": cost_breakdown.storage_cost
            },
            "api_provider": {
                "image_generation": "OpenAI DALL-E 3",
                "actual_api_cost": cost_breakdown.generation_cost,
                "cost_transparent": True
            }
        }