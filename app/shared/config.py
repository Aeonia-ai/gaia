"""
Shared configuration settings for Gaia Platform services.
Extends LLM Platform configuration with microservices-specific settings.
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache

class GaiaSettings(BaseSettings):
    """
    Gaia Platform configuration settings.
    Includes all LLM Platform settings plus microservices-specific configuration.
    """
    
    # API Configuration (from LLM Platform)
    API_KEY: str = os.getenv("API_KEY", "")
    
    # LLM API Keys (from LLM Platform)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # Database Configuration (from LLM Platform)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/llm_platform")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "5"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
    DATABASE_POOL_TIMEOUT: int = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
    DATABASE_POOL_RECYCLE: int = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))
    
    # Supabase Configuration (from LLM Platform)
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_JWT_SECRET: Optional[str] = os.getenv("SUPABASE_JWT_SECRET")
    
    # Rate Limiting (from LLM Platform)
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_PERIOD: str = os.getenv("RATE_LIMIT_PERIOD", "minute")
    
    # CORS Configuration (from LLM Platform)
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:8666,http://localhost:3000")
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]
    
    # Logging (from LLM Platform)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # MCP Configuration (from LLM Platform)
    MCP_FILESYSTEM_ROOT: str = os.getenv("MCP_FILESYSTEM_ROOT", "/app/data")
    
    # Universal Asset Server Configuration (from LLM Platform)
    FREESOUND_API_KEY: Optional[str] = os.getenv("FREESOUND_API_KEY")
    MESHY_API_KEY: Optional[str] = os.getenv("MESHY_API_KEY")
    MIDJOURNEY_API_KEY: Optional[str] = os.getenv("MIDJOURNEY_API_KEY")
    MUBERT_API_KEY: Optional[str] = os.getenv("MUBERT_API_KEY")
    STABILITY_API_KEY: Optional[str] = os.getenv("STABILITY_API_KEY")
    
    # Redis Configuration (from LLM Platform)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # Asset Storage Configuration (from LLM Platform)
    ASSET_STORAGE_BUCKET: str = os.getenv("ASSET_STORAGE_BUCKET", "assets")
    MAX_ASSET_FILE_SIZE_MB: int = int(os.getenv("MAX_ASSET_FILE_SIZE_MB", "100"))
    MAX_PREVIEW_IMAGE_SIZE_MB: int = int(os.getenv("MAX_PREVIEW_IMAGE_SIZE_MB", "10"))
    
    # Cost Optimization Parameters (from LLM Platform)
    MAX_GENERATION_COST_PER_ASSET: float = float(os.getenv("MAX_GENERATION_COST_PER_ASSET", "0.50"))
    DEFAULT_CACHE_TTL_SECONDS: int = int(os.getenv("DEFAULT_CACHE_TTL_SECONDS", "3600"))
    MAX_CONCURRENT_GENERATIONS: int = int(os.getenv("MAX_CONCURRENT_GENERATIONS", "5"))
    
    # Performance Settings (from LLM Platform)
    ASSET_SEARCH_LIMIT_DEFAULT: int = int(os.getenv("ASSET_SEARCH_LIMIT_DEFAULT", "20"))
    ASSET_SEARCH_LIMIT_MAX: int = int(os.getenv("ASSET_SEARCH_LIMIT_MAX", "100"))
    SEMANTIC_SEARCH_SIMILARITY_THRESHOLD: float = float(os.getenv("SEMANTIC_SEARCH_SIMILARITY_THRESHOLD", "0.7"))
    
    # === NEW GAIA PLATFORM SETTINGS ===
    
    # NATS Configuration
    NATS_URL: str = os.getenv("NATS_URL", "nats://localhost:4222")
    NATS_TIMEOUT: float = float(os.getenv("NATS_TIMEOUT", "5.0"))
    NATS_MAX_RECONNECT_ATTEMPTS: int = int(os.getenv("NATS_MAX_RECONNECT_ATTEMPTS", "10"))
    
    # Service URLs (for inter-service communication)
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
    ASSET_SERVICE_URL: str = os.getenv("ASSET_SERVICE_URL", "http://localhost:8002") 
    CHAT_SERVICE_URL: str = os.getenv("CHAT_SERVICE_URL", "http://localhost:8003")
    GATEWAY_URL: str = os.getenv("GATEWAY_URL", "http://localhost:8666")
    
    # Service Configuration
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "unknown")
    SERVICE_VERSION: str = os.getenv("SERVICE_VERSION", "1.0.0")
    SERVICE_HOST: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8000"))
    
    # Health Check Configuration
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
    HEALTH_CHECK_TIMEOUT: float = float(os.getenv("HEALTH_CHECK_TIMEOUT", "5.0"))
    
    # Service Discovery and Coordination
    SERVICE_REGISTRY_ENABLED: bool = os.getenv("SERVICE_REGISTRY_ENABLED", "true").lower() == "true"
    SERVICE_HEARTBEAT_INTERVAL: int = int(os.getenv("SERVICE_HEARTBEAT_INTERVAL", "15"))
    
    # Request Timeout Configuration
    INTER_SERVICE_REQUEST_TIMEOUT: float = float(os.getenv("INTER_SERVICE_REQUEST_TIMEOUT", "30.0"))
    CLIENT_REQUEST_TIMEOUT: float = float(os.getenv("CLIENT_REQUEST_TIMEOUT", "60.0"))
    
    # Gateway Configuration
    GATEWAY_REQUEST_TIMEOUT: float = float(os.getenv("GATEWAY_REQUEST_TIMEOUT", "30.0"))
    GATEWAY_MAX_RETRIES: int = int(os.getenv("GATEWAY_MAX_RETRIES", "2"))
    GATEWAY_RETRY_DELAY: float = float(os.getenv("GATEWAY_RETRY_DELAY", "1.0"))
    
    # Environment and Deployment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Performance and Scaling
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
    WORKER_POOL_SIZE: int = int(os.getenv("WORKER_POOL_SIZE", "4"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env

@lru_cache()
def get_settings() -> GaiaSettings:
    """Get cached settings instance."""
    return GaiaSettings()

# Global settings instance
settings = get_settings()

def get_service_info() -> dict:
    """Get current service information."""
    return {
        "name": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "host": settings.SERVICE_HOST,
        "port": settings.SERVICE_PORT,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }

def get_nats_config() -> dict:
    """Get NATS configuration."""
    return {
        "url": settings.NATS_URL,
        "timeout": settings.NATS_TIMEOUT,
        "max_reconnect_attempts": settings.NATS_MAX_RECONNECT_ATTEMPTS
    }

def get_service_urls() -> dict:
    """Get all service URLs for inter-service communication."""
    return {
        "auth": settings.AUTH_SERVICE_URL,
        "asset": settings.ASSET_SERVICE_URL,
        "chat": settings.CHAT_SERVICE_URL,
        "gateway": settings.GATEWAY_URL
    }
