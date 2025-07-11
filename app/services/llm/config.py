"""
Configuration classes for LLM providers
"""
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum

from .base import LLMProvider, ModelCapability

class ProviderStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"

class ProviderConfig(BaseModel):
    """Base configuration for LLM providers"""
    provider: LLMProvider
    status: ProviderStatus = ProviderStatus.ENABLED
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    rate_limit_requests_per_minute: int = 60
    priority: int = 1  # Lower number = higher priority
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ClaudeConfig(ProviderConfig):
    """Configuration for Claude provider"""
    provider: LLMProvider = LLMProvider.CLAUDE
    pool_size: int = 3
    enable_connection_pooling: bool = True
    default_model: str = "claude-3-haiku-20240307"
    
    @validator('api_key', pre=True, always=True)
    def get_api_key(cls, v):
        return v or os.getenv('ANTHROPIC_API_KEY')
    
    class Config:
        env_prefix = "CLAUDE_"

class OpenAIConfig(ProviderConfig):
    """Configuration for OpenAI provider"""
    provider: LLMProvider = LLMProvider.OPENAI
    organization: Optional[str] = None
    default_model: str = "gpt-4o-mini"
    enable_tiktoken: bool = True
    
    @validator('api_key', pre=True, always=True)
    def get_api_key(cls, v):
        return v or os.getenv('OPENAI_API_KEY')
    
    @validator('organization', pre=True, always=True)
    def get_organization(cls, v):
        return v or os.getenv('OPENAI_ORG_ID')
    
    class Config:
        env_prefix = "OPENAI_"

class GeminiConfig(ProviderConfig):
    """Configuration for Google Gemini provider"""
    provider: LLMProvider = LLMProvider.GEMINI
    project_id: Optional[str] = None
    location: str = "us-central1"
    default_model: str = "gemini-1.5-flash"
    
    @validator('api_key', pre=True, always=True)
    def get_api_key(cls, v):
        return v or os.getenv('GOOGLE_API_KEY')
    
    @validator('project_id', pre=True, always=True)
    def get_project_id(cls, v):
        return v or os.getenv('GOOGLE_PROJECT_ID')
    
    class Config:
        env_prefix = "GEMINI_"

class MistralConfig(ProviderConfig):
    """Configuration for Mistral provider"""
    provider: LLMProvider = LLMProvider.MISTRAL
    default_model: str = "mistral-small-latest"
    
    @validator('api_key', pre=True, always=True)
    def get_api_key(cls, v):
        return v or os.getenv('MISTRAL_API_KEY')
    
    class Config:
        env_prefix = "MISTRAL_"

class ModelFilterConfig(BaseModel):
    """Configuration for model filtering and selection"""
    enabled_providers: List[LLMProvider] = Field(default_factory=lambda: [LLMProvider.CLAUDE, LLMProvider.OPENAI])
    blocked_models: List[str] = Field(default_factory=list)
    preferred_models: Dict[str, str] = Field(default_factory=dict)  # context -> model_id
    capability_requirements: Dict[str, List[ModelCapability]] = Field(default_factory=dict)
    max_cost_per_token: Optional[float] = None
    max_response_time_ms: Optional[int] = None
    require_streaming: bool = False

class LoadBalancingConfig(BaseModel):
    """Configuration for load balancing across providers"""
    strategy: str = "round_robin"  # round_robin, least_loaded, fastest, cheapest, quality
    enable_failover: bool = True
    health_check_interval_seconds: int = 60
    unhealthy_threshold: int = 3  # Number of consecutive failures before marking unhealthy
    recovery_check_interval_seconds: int = 300
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_seconds: int = 60

class CachingConfig(BaseModel):
    """Configuration for caching LLM responses"""
    enable_response_caching: bool = False
    cache_ttl_seconds: int = 3600
    cache_max_size: int = 1000
    cache_key_strategy: str = "content_hash"  # content_hash, exact_match
    cacheable_models: List[str] = Field(default_factory=list)
    exclude_user_specific: bool = True

class MonitoringConfig(BaseModel):
    """Configuration for monitoring and metrics"""
    enable_metrics: bool = True
    track_token_usage: bool = True
    track_response_times: bool = True
    track_error_rates: bool = True
    log_requests: bool = False
    log_responses: bool = False
    metrics_export_interval_seconds: int = 60

class LLMProviderGlobalConfig(BaseModel):
    """Global configuration for all LLM providers"""
    
    # Provider configurations
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    mistral: MistralConfig = Field(default_factory=MistralConfig)
    
    # Feature configurations
    model_filter: ModelFilterConfig = Field(default_factory=ModelFilterConfig)
    load_balancing: LoadBalancingConfig = Field(default_factory=LoadBalancingConfig)
    caching: CachingConfig = Field(default_factory=CachingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # Global settings
    default_provider: LLMProvider = LLMProvider.CLAUDE
    default_model: str = "claude-3-haiku-20240307"  # Fast, reliable default
    enable_auto_selection: bool = False  # Default to single model choice
    enable_auto_fallback: bool = True
    request_timeout_seconds: int = 30
    enable_request_logging: bool = True
    log_level: str = "INFO"
    
    def get_provider_config(self, provider: LLMProvider) -> ProviderConfig:
        """Get configuration for a specific provider"""
        provider_configs = {
            LLMProvider.CLAUDE: self.claude,
            LLMProvider.OPENAI: self.openai,
            LLMProvider.GEMINI: self.gemini,
            LLMProvider.MISTRAL: self.mistral
        }
        return provider_configs.get(provider, ProviderConfig(provider=provider))
    
    def get_enabled_providers(self) -> List[LLMProvider]:
        """Get list of enabled providers"""
        enabled = []
        for provider in LLMProvider:
            config = self.get_provider_config(provider)
            if config.status == ProviderStatus.ENABLED and config.api_key:
                enabled.append(provider)
        return enabled
    
    def is_provider_available(self, provider: LLMProvider) -> bool:
        """Check if a provider is available (enabled and has API key)"""
        config = self.get_provider_config(provider)
        return (config.status == ProviderStatus.ENABLED and 
                config.api_key is not None and 
                len(config.api_key) > 0)
    
    def get_default_model(self) -> str:
        """Get the configured default model"""
        # Allow environment override
        env_default = os.getenv('DEFAULT_LLM_MODEL')
        if env_default:
            return env_default
        return self.default_model
    
    def get_default_provider(self) -> LLMProvider:
        """Get the configured default provider"""
        # Allow environment override  
        env_provider = os.getenv('DEFAULT_LLM_PROVIDER')
        if env_provider:
            try:
                return LLMProvider(env_provider)
            except ValueError:
                pass
        return self.default_provider
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

class UserProviderPreferences(BaseModel):
    """User-specific provider preferences"""
    user_id: str
    preferred_provider: Optional[LLMProvider] = None
    preferred_models: Dict[str, str] = Field(default_factory=dict)  # context -> model_id
    blocked_providers: List[LLMProvider] = Field(default_factory=list)
    max_cost_per_request: Optional[float] = None
    priority_settings: Dict[str, str] = Field(default_factory=dict)  # context -> priority
    custom_prompts: Dict[str, str] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

def load_global_config() -> LLMProviderGlobalConfig:
    """Load global configuration from environment and defaults"""
    return LLMProviderGlobalConfig()

def load_user_preferences(user_id: str) -> UserProviderPreferences:
    """Load user preferences (placeholder - would integrate with database)"""
    return UserProviderPreferences(user_id=user_id)

# Global configuration instance
global_config = load_global_config()

# Provider configuration mapping
PROVIDER_CONFIG_MAP = {
    LLMProvider.CLAUDE: ClaudeConfig,
    LLMProvider.OPENAI: OpenAIConfig,
    LLMProvider.GEMINI: GeminiConfig,
    LLMProvider.MISTRAL: MistralConfig
}