import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .base import (
    LLMProvider,
    ModelInfo,
    LLMProviderInterface,
    LLMProviderFactory,
    LLMProviderError
)

logger = logging.getLogger(__name__)

@dataclass
class ProviderHealth:
    provider: LLMProvider
    status: str  # "healthy", "unhealthy", "unknown"
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    last_checked: Optional[datetime] = None
    available_models: int = 0

@dataclass
class ProviderStats:
    provider: LLMProvider
    requests_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_response_time_ms: float = 0.0
    error_count: int = 0
    last_request: Optional[datetime] = None

class LLMProviderRegistry:
    """Registry for managing multiple LLM providers"""
    
    def __init__(self):
        self._providers: Dict[LLMProvider, LLMProviderInterface] = {}
        self._health_status: Dict[LLMProvider, ProviderHealth] = {}
        self._stats: Dict[LLMProvider, ProviderStats] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize all registered providers"""
        if self._initialized:
            return
        
        logger.info("Initializing LLM provider registry")
        
        # Get all available providers from factory
        available_providers = LLMProviderFactory.get_available_providers()
        
        for provider in available_providers:
            try:
                # Get provider instance
                provider_instance = await LLMProviderFactory.get_provider(provider)
                
                # Validate configuration
                if await provider_instance.validate_config():
                    self._providers[provider] = provider_instance
                    self._stats[provider] = ProviderStats(provider=provider)
                    logger.info(f"Successfully initialized provider: {provider.value}")
                else:
                    logger.warning(f"Provider {provider.value} failed configuration validation")
                    
            except Exception as e:
                logger.error(f"Failed to initialize provider {provider.value}: {str(e)}")
        
        # Perform initial health check
        await self.health_check_all()
        
        self._initialized = True
        logger.info(f"Provider registry initialized with {len(self._providers)} providers")
    
    async def get_provider(self, provider: LLMProvider) -> LLMProviderInterface:
        """Get a specific provider instance"""
        if not self._initialized:
            await self.initialize()
        
        if provider not in self._providers:
            raise LLMProviderError(f"Provider {provider.value} not available", provider)
        
        return self._providers[provider]
    
    def get_available_providers(self) -> List[LLMProvider]:
        """Get list of available providers"""
        return list(self._providers.keys())
    
    async def get_all_models(self) -> Dict[LLMProvider, List[ModelInfo]]:
        """Get all available models from all providers"""
        if not self._initialized:
            await self.initialize()
        
        models = {}
        for provider, provider_instance in self._providers.items():
            try:
                models[provider] = provider_instance.available_models
            except Exception as e:
                logger.error(f"Failed to get models from provider {provider.value}: {str(e)}")
                models[provider] = []
        
        return models
    
    async def get_models_for_provider(self, provider: LLMProvider) -> List[ModelInfo]:
        """Get all models for a specific provider"""
        if not self._initialized:
            await self.initialize()
        
        if provider not in self._providers:
            return []
        
        try:
            return self._providers[provider].available_models
        except Exception as e:
            logger.error(f"Failed to get models for provider {provider.value}: {str(e)}")
            return []
    
    async def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get a specific model by ID"""
        if not self._initialized:
            await self.initialize()
        
        for provider_instance in self._providers.values():
            for model in provider_instance.available_models:
                if model.id == model_id:
                    return model
        return None
    
    async def get_provider_health(self, provider: LLMProvider) -> Dict[str, Any]:
        """Get health status for a specific provider"""
        if not self._initialized:
            await self.initialize()
        
        health = self._health_status.get(provider, ProviderHealth(provider, "unknown"))
        return {
            "status": health.status,
            "response_time_ms": health.response_time_ms,
            "error": health.error,
            "last_checked": health.last_checked.isoformat() if health.last_checked else None,
            "available_models": health.available_models
        }
    
    async def get_provider_stats(self, provider: LLMProvider) -> Dict[str, Any]:
        """Get statistics for a specific provider"""
        if not self._initialized:
            await self.initialize()
        
        stats = self._stats.get(provider, ProviderStats(provider=provider))
        return {
            "requests_count": stats.requests_count,
            "total_tokens": stats.total_tokens,
            "total_cost": stats.total_cost,
            "avg_response_time_ms": stats.avg_response_time_ms,
            "error_count": stats.error_count,
            "last_request": stats.last_request.isoformat() if stats.last_request else None
        }
    
    async def get_model_stats(self, model_id: str) -> Dict[str, Any]:
        """Get statistics for a specific model"""
        # For now, return basic model info
        model = await self.get_model(model_id)
        if model:
            return {
                "model_id": model.id,
                "provider": model.provider.value,
                "avg_response_time_ms": model.avg_response_time_ms,
                "quality_score": model.quality_score,
                "speed_score": model.speed_score,
                "requests_count": 0,  # Would need to track per-model stats
                "total_tokens": 0
            }
        return {}
    
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get model information from any provider"""
        if not self._initialized:
            await self.initialize()
        
        for provider_instance in self._providers.values():
            model_info = await provider_instance.get_model_info(model_id)
            if model_info:
                return model_info
        
        return None
    
    async def find_provider_for_model(self, model_id: str) -> Optional[LLMProvider]:
        """Find which provider supports a specific model"""
        if not self._initialized:
            await self.initialize()
        
        for provider, provider_instance in self._providers.items():
            if provider_instance.is_model_available(model_id):
                return provider
        
        return None
    
    async def get_best_provider(self, 
                              criteria: str = "speed",
                              exclude_unhealthy: bool = True) -> Optional[LLMProvider]:
        """Get the best provider based on criteria"""
        if not self._initialized:
            await self.initialize()
        
        available_providers = self._providers.keys()
        
        # Filter out unhealthy providers if requested
        if exclude_unhealthy:
            available_providers = [
                p for p in available_providers 
                if self._health_status.get(p, ProviderHealth(p, "unknown")).status == "healthy"
            ]
        
        if not available_providers:
            return None
        
        # Select based on criteria
        if criteria == "speed":
            # Select provider with best average response time
            best_provider = None
            best_time = float('inf')
            
            for provider in available_providers:
                health = self._health_status.get(provider)
                if health and health.response_time_ms and health.response_time_ms < best_time:
                    best_time = health.response_time_ms
                    best_provider = provider
            
            return best_provider
        
        elif criteria == "cost":
            # Select provider with lowest cost per token
            best_provider = None
            best_cost = float('inf')
            
            for provider in available_providers:
                provider_instance = self._providers[provider]
                models = provider_instance.available_models
                if models:
                    avg_cost = sum(m.cost_per_input_token for m in models) / len(models)
                    if avg_cost < best_cost:
                        best_cost = avg_cost
                        best_provider = provider
            
            return best_provider
        
        elif criteria == "reliability":
            # Select provider with lowest error rate
            best_provider = None
            best_error_rate = float('inf')
            
            for provider in available_providers:
                stats = self._stats.get(provider)
                if stats and stats.requests_count > 0:
                    error_rate = stats.error_count / stats.requests_count
                    if error_rate < best_error_rate:
                        best_error_rate = error_rate
                        best_provider = provider
            
            return best_provider
        
        # Default: return first available provider
        return list(available_providers)[0] if available_providers else None
    
    async def health_check_all(self) -> Dict[LLMProvider, ProviderHealth]:
        """Perform health check on all providers"""
        health_checks = []
        
        for provider, provider_instance in self._providers.items():
            health_checks.append(self._health_check_provider(provider, provider_instance))
        
        # Run all health checks concurrently
        results = await asyncio.gather(*health_checks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            provider = list(self._providers.keys())[i]
            if isinstance(result, Exception):
                self._health_status[provider] = ProviderHealth(
                    provider=provider,
                    status="unhealthy",
                    error=str(result),
                    last_checked=datetime.now()
                )
            else:
                self._health_status[provider] = result
        
        return self._health_status
    
    async def _health_check_provider(self, provider: LLMProvider, 
                                   provider_instance: LLMProviderInterface) -> ProviderHealth:
        """Health check for a single provider"""
        try:
            health_info = await provider_instance.health_check()
            
            return ProviderHealth(
                provider=provider,
                status=health_info.get("status", "unknown"),
                response_time_ms=health_info.get("response_time_ms"),
                error=health_info.get("error"),
                last_checked=datetime.now(),
                available_models=len(provider_instance.available_models)
            )
        except Exception as e:
            return ProviderHealth(
                provider=provider,
                status="unhealthy",
                error=str(e),
                last_checked=datetime.now()
            )
    
    def get_health_status(self, provider: Optional[LLMProvider] = None) -> Dict[LLMProvider, ProviderHealth]:
        """Get health status for providers"""
        if provider:
            return {provider: self._health_status.get(provider, ProviderHealth(provider, "unknown"))}
        return self._health_status.copy()
    
    def record_request(self, provider: LLMProvider, 
                      tokens_used: int = 0,
                      cost: float = 0.0,
                      response_time_ms: int = 0,
                      error: bool = False):
        """Record request statistics"""
        if provider not in self._stats:
            self._stats[provider] = ProviderStats(provider=provider)
        
        stats = self._stats[provider]
        stats.requests_count += 1
        stats.total_tokens += tokens_used
        stats.total_cost += cost
        stats.last_request = datetime.now()
        
        if error:
            stats.error_count += 1
        
        # Update average response time
        if response_time_ms > 0:
            total_time = stats.avg_response_time_ms * (stats.requests_count - 1) + response_time_ms
            stats.avg_response_time_ms = total_time / stats.requests_count
    
    def get_stats(self, provider: Optional[LLMProvider] = None) -> Dict[LLMProvider, ProviderStats]:
        """Get statistics for providers"""
        if provider:
            return {provider: self._stats.get(provider, ProviderStats(provider=provider))}
        return self._stats.copy()
    
    async def get_registry_info(self) -> Dict[str, Any]:
        """Get complete registry information"""
        if not self._initialized:
            await self.initialize()
        
        return {
            "initialized": self._initialized,
            "available_providers": [p.value for p in self.get_available_providers()],
            "total_providers": len(self._providers),
            "health_status": {
                p.value: {
                    "status": h.status,
                    "response_time_ms": h.response_time_ms,
                    "available_models": h.available_models,
                    "last_checked": h.last_checked.isoformat() if h.last_checked else None,
                    "error": h.error
                }
                for p, h in self._health_status.items()
            },
            "stats": {
                p.value: {
                    "requests_count": s.requests_count,
                    "total_tokens": s.total_tokens,
                    "total_cost": s.total_cost,
                    "avg_response_time_ms": s.avg_response_time_ms,
                    "error_count": s.error_count,
                    "last_request": s.last_request.isoformat() if s.last_request else None
                }
                for p, s in self._stats.items()
            },
            "timestamp": datetime.now().isoformat()
        }

# Global registry instance
_registry = LLMProviderRegistry()

async def get_registry() -> LLMProviderRegistry:
    """Get the global provider registry"""
    if not _registry._initialized:
        await _registry.initialize()
    return _registry