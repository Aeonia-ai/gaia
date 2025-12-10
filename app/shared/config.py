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
    
    # Environment-specific URLs for Supabase redirects
    WEB_SERVICE_BASE_URL: Optional[str] = os.getenv("WEB_SERVICE_BASE_URL")  # Override for cloud deployment
    
    # Rate Limiting (from LLM Platform)
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_PERIOD: str = os.getenv("RATE_LIMIT_PERIOD", "minute")
    
    # CORS Configuration (from LLM Platform)
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:8666,http://localhost:8080")
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]
    
    # Logging (from LLM Platform)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # MCP Configuration (from LLM Platform)
    MCP_FILESYSTEM_ROOT: str = os.getenv("MCP_FILESYSTEM_ROOT", "/app/data")
    
    # Universal Asset Server Configuration (from LLM Platform)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
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
    KB_SERVICE_URL: str = os.getenv("KB_SERVICE_URL", "http://localhost:8004")
    GATEWAY_URL: str = os.getenv("GATEWAY_URL", "http://localhost:8666")
    CHAT_INCLUDE_AUX_TOOLS: bool = os.getenv("CHAT_INCLUDE_AUX_TOOLS", "false").lower() == "true"
    CHAT_EXPERIENCE_CACHE_TTL_SECONDS: int = int(os.getenv("CHAT_EXPERIENCE_CACHE_TTL_SECONDS", "300"))
    
    # Service Configuration
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "unknown")
    SERVICE_VERSION: str = os.getenv("SERVICE_VERSION", "1.0.0")
    
    # KB Configuration
    KB_PATH: str = os.getenv("KB_PATH", "/kb")
    KB_STORAGE_MODE: str = os.getenv("KB_STORAGE_MODE", "git")  # "git", "database", "hybrid"
    KB_MCP_ENABLED: bool = os.getenv("KB_MCP_ENABLED", "true").lower() == "true"
    KB_CACHE_TTL: int = int(os.getenv("KB_CACHE_TTL", "300"))  # 5 minutes
    KB_GIT_BACKUP_ENABLED: bool = os.getenv("KB_GIT_BACKUP_ENABLED", "true").lower() == "true"
    KB_BACKUP_INTERVAL: int = int(os.getenv("KB_BACKUP_INTERVAL", "300"))  # 5 minutes
    KB_BATCH_COMMITS: bool = os.getenv("KB_BATCH_COMMITS", "true").lower() == "true"
    KB_PUSH_ENABLED: bool = os.getenv("KB_PUSH_ENABLED", "false").lower() == "true"
    
    # KB Git Sync Configuration
    KB_GIT_AUTO_SYNC: bool = os.getenv("KB_GIT_AUTO_SYNC", "true").lower() == "true"
    KB_SYNC_INTERVAL: int = int(os.getenv("KB_SYNC_INTERVAL", "3600"))  # 1 hour
    KB_GIT_REMOTE: str = os.getenv("KB_GIT_REMOTE", "origin")
    KB_GIT_BRANCH: str = os.getenv("KB_GIT_BRANCH", "main")
    
    # KB Git Repository Configuration
    KB_GIT_REPO_URL: Optional[str] = os.getenv("KB_GIT_REPO_URL")  # e.g., "https://github.com/user/kb.git"
    KB_GIT_AUTH_TOKEN: Optional[str] = os.getenv("KB_GIT_AUTH_TOKEN")  # GitHub token for private repos
    KB_GIT_AUTO_CLONE: bool = os.getenv("KB_GIT_AUTO_CLONE", "true").lower() == "true"
    
    # KB Semantic Search Configuration
    KB_SEMANTIC_SEARCH_ENABLED: bool = os.getenv("KB_SEMANTIC_SEARCH_ENABLED", "false").lower() == "true"
    KB_SEMANTIC_CACHE_TTL: int = int(os.getenv("KB_SEMANTIC_CACHE_TTL", "3600"))  # 1 hour
    
    # Multi-User KB Configuration
    KB_MULTI_USER_ENABLED: bool = os.getenv("KB_MULTI_USER_ENABLED", "false").lower() == "true"
    KB_USER_ISOLATION: str = os.getenv("KB_USER_ISOLATION", "strict")  # "strict" or "permissive"
    KB_DEFAULT_VISIBILITY: str = os.getenv("KB_DEFAULT_VISIBILITY", "private")  # "private" or "public"
    KB_SHARING_ENABLED: bool = os.getenv("KB_SHARING_ENABLED", "true").lower() == "true"
    KB_WORKSPACE_ENABLED: bool = os.getenv("KB_WORKSPACE_ENABLED", "true").lower() == "true"
    KB_TEAM_ENABLED: bool = os.getenv("KB_TEAM_ENABLED", "true").lower() == "true"
    
    # RBAC Configuration
    RBAC_CACHE_TTL: int = int(os.getenv("RBAC_CACHE_TTL", "300"))  # 5 minutes
    RBAC_AUDIT_ENABLED: bool = os.getenv("RBAC_AUDIT_ENABLED", "true").lower() == "true"
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
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Performance and Scaling
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
    WORKER_POOL_SIZE: int = int(os.getenv("WORKER_POOL_SIZE", "4"))

    # Web UI Feature Flags
    SINGLE_CHAT_MODE: bool = os.getenv("SINGLE_CHAT_MODE", "false").lower() == "true"

    # Chat Service Configuration
    CHAT_INCLUDE_AUX_TOOLS: bool = os.getenv("CHAT_INCLUDE_AUX_TOOLS", "true").lower() == "true"
    CHAT_EXPERIENCE_CACHE_TTL_SECONDS: int = int(os.getenv("CHAT_EXPERIENCE_CACHE_TTL_SECONDS", "300"))

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

def get_web_service_base_url() -> str:
    """Get the base URL for the web service based on environment."""
    if settings.WEB_SERVICE_BASE_URL:
        # Explicit override for cloud deployment
        return settings.WEB_SERVICE_BASE_URL
    elif settings.ENVIRONMENT in ["production", "prod"]:
        # Production environment
        return "https://gaia-web-production.fly.dev"
    elif settings.ENVIRONMENT in ["staging", "stage"]:
        # Staging environment  
        return "https://gaia-web-staging.fly.dev"
    elif settings.ENVIRONMENT in ["dev", "development"]:
        # Development environment (cloud-based)
        return "https://gaia-web-dev.fly.dev"
    else:
        # Local development (default)
        return "http://localhost:8080"

def get_supabase_redirect_urls() -> dict:
    """Get Supabase redirect URLs for current environment."""
    base_url = get_web_service_base_url()
    return {
        "site_url": base_url,
        "redirect_urls": [
            f"{base_url}/auth/confirm",
            f"{base_url}/auth/callback",
            f"{base_url}/"
        ]
    }

def get_nats_config() -> dict:
    """Get NATS configuration with smart service discovery."""
    # Check if we have separate NATS_HOST and NATS_PORT (multi-cloud approach)
    nats_host = os.getenv("NATS_HOST")
    nats_port = os.getenv("NATS_PORT")
    
    if nats_host and nats_port:
        # Environment-based service discovery for multi-cloud portability
        nats_url = f"nats://{nats_host}:{nats_port}"
    else:
        # Fallback to hardcoded NATS_URL or default
        nats_url = settings.NATS_URL
    
    return {
        "url": nats_url,
        "timeout": settings.NATS_TIMEOUT,
        "max_reconnect_attempts": settings.NATS_MAX_RECONNECT_ATTEMPTS
    }

def get_service_url(service_name: str) -> str:
    """
    Get service URL with smart cloud-agnostic service discovery.
    
    Supports multiple deployment patterns:
    1. Environment-based URLs (ENVIRONMENT=dev -> gaia-{service}-dev.fly.dev)
    2. Explicit URL override via {SERVICE}_URL environment variable
    3. Local development defaults
    """
    service_name = service_name.lower()
    
    # Check for explicit URL override first
    url_env_var = f"{service_name.upper()}_SERVICE_URL"
    explicit_url = os.getenv(url_env_var)
    if explicit_url:
        return explicit_url
    
    # Use environment-based service discovery
    environment = settings.ENVIRONMENT.lower()
    
    if environment in ["local", "development"]:
        # Local development
        port_map = {
            "auth": 8001,
            "asset": 8002, 
            "chat": 8003,
            "kb": 8004,
            "gateway": 8666,
            "web": 8080,
            "nats": 4222
        }
        port = port_map.get(service_name, 8000)
        return f"http://localhost:{port}"
    
    else:
        # Cloud deployment - auto-generate URL based on environment
        # Format: gaia-{service}-{environment}.fly.dev
        # This pattern can be adapted for other cloud providers
        cloud_provider = os.getenv("CLOUD_PROVIDER", "fly")
        
        if cloud_provider == "fly":
            return f"https://gaia-{service_name}-{environment}.fly.dev"
        elif cloud_provider == "aws":
            region = os.getenv("AWS_REGION", "us-west-2") 
            return f"https://gaia-{service_name}-{environment}.{region}.elb.amazonaws.com"
        elif cloud_provider == "gcp":
            region = os.getenv("GCP_REGION", "us-west1")
            project = os.getenv("GCP_PROJECT", "gaia-platform")
            return f"https://gaia-{service_name}-{environment}-{region}.run.app"
        elif cloud_provider == "azure":
            region = os.getenv("AZURE_REGION", "westus2")
            return f"https://gaia-{service_name}-{environment}.{region}.azurecontainer.io"
        else:
            # Fallback to fly.io pattern
            return f"https://gaia-{service_name}-{environment}.fly.dev"

def get_service_urls() -> dict:
    """Get all service URLs for inter-service communication."""
    return {
        "auth": get_service_url("auth"),
        "asset": get_service_url("asset"),
        "chat": get_service_url("chat"),
        "kb": get_service_url("kb"),
        "gateway": get_service_url("gateway"),
        "web": get_service_url("web")
    }
