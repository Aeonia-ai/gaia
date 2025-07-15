"""Web service configuration"""
from pydantic_settings import BaseSettings
from typing import Optional


class WebSettings(BaseSettings):
    """Web service specific settings"""
    # Service info
    service_name: str = "web"
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Gateway connection
    gateway_url: str = "http://gateway:8000"
    
    # Session configuration
    session_secret: str = "change-this-in-production"
    session_cookie_name: str = "gaia_session"
    session_max_age: int = 86400  # 24 hours
    
    # NATS configuration
    nats_url: Optional[str] = "nats://nats:4222"
    
    # Frontend settings
    enable_websocket: bool = True
    enable_htmx: bool = True
    
    # Debug settings
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_prefix = "WEB_"
        env_file = ".env"


# Global settings instance
settings = WebSettings()