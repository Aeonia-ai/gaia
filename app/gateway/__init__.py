"""
Gaia Platform Gateway Service

The gateway service is the main entry point for all client requests.
It maintains backward compatibility with the LLM Platform API while
routing requests to appropriate microservices.

Key responsibilities:
- Accept all client connections on port 8666 
- Authenticate requests (JWT + API key support)
- Route requests to auth, asset, and chat services
- Maintain identical API endpoints for client compatibility
- Coordinate responses from multiple services when needed
- Provide health monitoring and service discovery
"""

from .main import app

__all__ = ["app"]
