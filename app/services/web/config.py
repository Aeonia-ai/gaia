"""Web service configuration"""
from app.shared import settings as shared_settings
from typing import Optional


class WebSettings:
    """Web service specific settings - inherits from shared"""
    # Service info
    service_name: str = "web"
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Gateway connection - use shared settings
    gateway_url: str = shared_settings.GATEWAY_URL
    api_key: str = shared_settings.API_KEY
    
    # Session configuration
    session_secret: str = shared_settings.SESSION_SECRET if hasattr(shared_settings, 'SESSION_SECRET') else "gaia-dev-session-secret-2025"
    session_cookie_name: str = "gaia_session"
    session_max_age: int = 86400  # 24 hours
    
    # NATS configuration
    nats_url: Optional[str] = shared_settings.NATS_URL
    
    # Frontend settings
    enable_websocket: bool = True
    enable_htmx: bool = True
    
    # Debug settings
    debug: bool = shared_settings.DEBUG
    log_level: str = shared_settings.LOG_LEVEL


# Global settings instance
settings = WebSettings()
