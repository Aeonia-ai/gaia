from typing import Optional, Dict, Any, List
from decimal import Decimal
import httpx
from datetime import datetime
from app.core.config import get_settings
from app.core import logger
from app.core.supabase_client import SupabaseWrapper
from app.models.assets import AssetCategory


class PricingService:
    """Dynamic pricing service that fetches costs from database."""
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase = SupabaseWrapper()
        self._pricing_cache = {}
        self._cache_ttl = 3600  # 1 hour cache
        self._last_cache_update = None
    
    async def get_generation_cost(
        self,
        provider: str,
        category: AssetCategory,
        quality: str = "standard",
        size: Optional[Dict[str, int]] = None
    ) -> float:
        """Get current generation cost from database."""
        try:
            # Check cache first
            cache_key = f"{provider}:{category.value}:{quality}:{size}"
            if self._is_cache_valid(cache_key):
                return self._pricing_cache[cache_key]
            
            # Fetch from database
            if self.supabase:
                result = self.supabase.rpc(
                    'get_api_pricing',
                    {
                        'p_provider_name': provider,
                        'p_asset_category': category.value,
                        'p_quality': quality,
                        'p_size_params': size
                    }
                ).execute()
                
                if result.data:
                    cost = float(result.data)
                    self._update_cache(cache_key, cost)
                    return cost
            
            # Fallback to defaults if database unavailable
            return self._get_fallback_cost(provider, category, quality)
            
        except Exception as e:
            logger.error(f"Failed to get pricing from database: {e}")
            return self._get_fallback_cost(provider, category, quality)
    
    async def log_usage_cost(
        self,
        provider: str,
        asset_id: str,
        request_id: str,
        units: float,
        unit_cost: float,
        total_cost: float,
        api_response_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log actual API usage cost for tracking and reconciliation."""
        try:
            if self.supabase:
                self.supabase.rpc(
                    'log_api_usage_cost',
                    {
                        'p_provider_name': provider,
                        'p_asset_id': asset_id,
                        'p_request_id': request_id,
                        'p_units': units,
                        'p_unit_cost': unit_cost,
                        'p_total_cost': total_cost,
                        'p_api_response_id': api_response_id,
                        'p_metadata': metadata
                    }
                ).execute()
                
                logger.info(f"Logged API usage: {provider} - ${total_cost:.4f} for asset {asset_id}")
                
        except Exception as e:
            logger.error(f"Failed to log API usage cost: {e}")
    
    async def update_pricing_from_provider(self, provider: str):
        """
        Fetch latest pricing from provider's API (if available).
        This would be called by a scheduled job or manual update.
        """
        try:
            if provider == "OpenAI":
                # OpenAI doesn't have a pricing API, so this would be manual
                logger.info("OpenAI pricing must be updated manually")
                
            elif provider == "Stability AI":
                # Example of fetching from provider API (if they had one)
                async with httpx.AsyncClient() as client:
                    # This is hypothetical - most providers don't expose pricing APIs
                    response = await client.get(
                        "https://api.stability.ai/v1/pricing",
                        headers={"Authorization": f"Bearer {self.settings.STABILITY_API_KEY}"}
                    )
                    if response.status_code == 200:
                        pricing_data = response.json()
                        await self._update_provider_pricing("Stability AI", pricing_data)
                        
        except Exception as e:
            logger.error(f"Failed to update pricing for {provider}: {e}")
    
    async def get_cost_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get cost analytics for the specified period."""
        try:
            if self.supabase:
                # Get usage costs for analytics
                result = self.supabase.table('api_usage_costs')\
                    .select('*')\
                    .gte('created_at', datetime.now().isoformat())\
                    .execute()
                
                if result.data:
                    total_cost = sum(item['total_cost'] for item in result.data)
                    by_provider = {}
                    
                    for item in result.data:
                        provider_id = item['provider_id']
                        if provider_id not in by_provider:
                            by_provider[provider_id] = 0
                        by_provider[provider_id] += item['total_cost']
                    
                    return {
                        'total_cost': total_cost,
                        'by_provider': by_provider,
                        'record_count': len(result.data),
                        'period_days': days
                    }
            
            return {'error': 'Analytics unavailable'}
            
        except Exception as e:
            logger.error(f"Failed to get cost analytics: {e}")
            return {'error': str(e)}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached pricing is still valid."""
        if cache_key not in self._pricing_cache:
            return False
        
        if not self._last_cache_update:
            return False
        
        elapsed = (datetime.now() - self._last_cache_update).total_seconds()
        return elapsed < self._cache_ttl
    
    def _update_cache(self, cache_key: str, cost: float):
        """Update pricing cache."""
        self._pricing_cache[cache_key] = cost
        self._last_cache_update = datetime.now()
    
    def _get_fallback_cost(self, provider: str, category: AssetCategory, quality: str) -> float:
        """Fallback costs when database is unavailable."""
        # These should match the database defaults
        fallback_costs = {
            "OpenAI": {
                "image": {"standard": 0.020, "hd": 0.040},
                "texture": {"standard": 0.015, "hd": 0.030}
            },
            "Stability AI": {
                "image": {"standard": 0.018, "hd": 0.025}
            },
            "ElevenLabs": {
                "audio": {"standard": 0.100, "hd": 0.150}
            },
            "Meshy AI": {
                "prop": {"standard": 0.150, "hd": 0.250},
                "character": {"standard": 0.200, "hd": 0.350},
                "environment": {"standard": 0.250, "hd": 0.400}
            }
        }
        
        provider_costs = fallback_costs.get(provider, {})
        category_costs = provider_costs.get(category.value, {})
        return category_costs.get(quality, 0.020)
    
    async def _update_provider_pricing(self, provider: str, pricing_data: Dict[str, Any]):
        """Update provider pricing in database."""
        try:
            if self.supabase:
                # Update pricing tiers based on provider data
                for tier in pricing_data.get('tiers', []):
                    self.supabase.table('api_pricing_tiers').upsert({
                        'provider_id': self.supabase.table('api_providers')
                            .select('id')
                            .eq('provider_name', provider)
                            .single()
                            .execute()
                            .data['id'],
                        'tier_name': tier['name'],
                        'asset_category': tier['category'],
                        'base_cost': tier['cost'],
                        'cost_unit': tier['unit'],
                        'updated_at': datetime.now().isoformat()
                    }).execute()
                    
                logger.info(f"Updated pricing for {provider}")
                
        except Exception as e:
            logger.error(f"Failed to update provider pricing: {e}")