"""
Shared utilities for Gaia Platform microservices.

This module provides common functionality used across all Gaia services:
- NATS client for inter-service messaging
- Database configuration and session management  
- Security and authentication utilities
- Supabase client configuration
- Logging setup and utilities
- Configuration management

These utilities maintain compatibility with the LLM Platform while adding
microservices-specific functionality for service coordination and messaging.
"""

from .config import settings, get_settings, get_service_info, get_nats_config, get_service_urls
from .database import (
    get_database_session, 
    get_database_url, 
    test_database_connection,
    database_health_check,
    engine,
    Base
)
from .logging import (
    get_logger, 
    configure_logging_for_service,
    log_service_startup,
    log_service_shutdown,
    log_nats_event,
    log_service_request,
    log_auth_event
)
from .nats_client import (
    NATSClient,
    get_nats_client,
    ensure_nats_connection,
    NATSSubjects,
    ServiceHealthEvent,
    AssetGenerationEvent,
    ChatMessageEvent
)
from .security import (
    AuthenticationResult,
    validate_supabase_jwt,
    get_current_auth,
    get_current_auth_legacy,
    get_current_auth_unified,
    validate_auth_for_service,
    require_authentication
)
from .supabase import (
    get_supabase_client,
    test_supabase_connection,
    supabase_health_check,
    get_supabase_config
)

__all__ = [
    # Configuration
    "settings",
    "get_settings", 
    "get_service_info",
    "get_nats_config",
    "get_service_urls",
    
    # Database
    "get_database_session",
    "get_database_url", 
    "test_database_connection",
    "database_health_check",
    "engine",
    "Base",
    
    # Logging
    "get_logger",
    "configure_logging_for_service",
    "log_service_startup",
    "log_service_shutdown", 
    "log_nats_event",
    "log_service_request",
    "log_auth_event",
    
    # NATS
    "NATSClient",
    "get_nats_client",
    "ensure_nats_connection", 
    "NATSSubjects",
    "ServiceHealthEvent",
    "AssetGenerationEvent", 
    "ChatMessageEvent",
    
    # Security
    "AuthenticationResult",
    "validate_supabase_jwt",
    "get_current_auth",
    "get_current_auth_legacy",
    "validate_auth_for_service", 
    "require_authentication",
    
    # Supabase
    "get_supabase_client",
    "test_supabase_connection",
    "supabase_health_check",
    "get_supabase_config"
]
