"""
Gaia Platform Auth Service

Handles authentication operations for the Gaia Platform:
- JWT token validation and refresh via Supabase
- API key validation
- User registration and login
- Inter-service authentication coordination

Maintains compatibility with LLM Platform authentication patterns.
"""

from .main import app

__all__ = ["app"]
