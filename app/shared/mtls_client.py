"""
mTLS Client for Service-to-Service Communication

This module provides HTTP clients with mutual TLS authentication
for secure communication between Gaia microservices.
"""
import os
import ssl
import httpx
from typing import Dict, Optional, Any
from pathlib import Path

from app.shared.config import settings
from app.shared.jwt_service import generate_service_jwt
from app.shared.logging import configure_logging_for_service

# Configure logging
logger = configure_logging_for_service("mtls_client")

# Certificate paths
TLS_CERT_PATH = os.getenv("TLS_CERT_PATH", "/app/certs/cert.pem")
TLS_KEY_PATH = os.getenv("TLS_KEY_PATH", "/app/certs/key.pem")
TLS_CA_PATH = os.getenv("TLS_CA_PATH", "/app/certs/ca.pem")


def create_ssl_context(
    verify_hostname: bool = True,
    require_cert: bool = True
) -> ssl.SSLContext:
    """
    Create SSL context for mTLS communication.
    
    Args:
        verify_hostname: Whether to verify hostname (disable for local dev)
        require_cert: Whether to require client certificate
        
    Returns:
        Configured SSL context
    """
    # Create SSL context
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    
    # Load CA certificate
    if Path(TLS_CA_PATH).exists():
        context.load_verify_locations(TLS_CA_PATH)
        logger.info(f"Loaded CA certificate from {TLS_CA_PATH}")
    else:
        logger.warning(f"CA certificate not found at {TLS_CA_PATH}, using default CA bundle")
    
    # Load client certificate and key
    if require_cert and Path(TLS_CERT_PATH).exists() and Path(TLS_KEY_PATH).exists():
        context.load_cert_chain(
            certfile=TLS_CERT_PATH,
            keyfile=TLS_KEY_PATH
        )
        logger.info(f"Loaded client certificate from {TLS_CERT_PATH}")
    else:
        logger.warning("Client certificate not found, proceeding without mTLS")
    
    # Configure verification
    if not verify_hostname:
        context.check_hostname = False
        context.hostname_checks_common_name = False
    
    # Set minimum TLS version
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    return context


class MTLSClient:
    """
    HTTP client with mTLS support for service-to-service communication.
    """
    
    def __init__(
        self,
        service_name: str,
        base_url: Optional[str] = None,
        use_mtls: bool = True,
        use_jwt: bool = True,
        timeout: float = 30.0
    ):
        """
        Initialize mTLS client.
        
        Args:
            service_name: Name of the calling service
            base_url: Base URL for requests
            use_mtls: Whether to use mTLS (can disable for local dev)
            use_jwt: Whether to include JWT in requests
            timeout: Request timeout in seconds
        """
        self.service_name = service_name
        self.base_url = base_url
        self.use_jwt = use_jwt
        self.timeout = timeout
        
        # Create SSL context if using mTLS
        if use_mtls and settings.ENVIRONMENT != "local":
            ssl_context = create_ssl_context(
                verify_hostname=(settings.ENVIRONMENT != "local")
            )
            self.client = httpx.AsyncClient(
                verify=ssl_context,
                timeout=timeout
            )
        else:
            # No mTLS for local development
            self.client = httpx.AsyncClient(
                verify=False if settings.ENVIRONMENT == "local" else True,
                timeout=timeout
            )
            
        logger.info(
            f"Created mTLS client for {service_name} "
            f"(mTLS: {use_mtls and settings.ENVIRONMENT != 'local'}, JWT: {use_jwt})"
        )
    
    async def _get_headers(self) -> Dict[str, str]:
        """Generate request headers with JWT if enabled."""
        headers = {
            "Content-Type": "application/json",
            "X-Service-Name": self.service_name
        }
        
        if self.use_jwt:
            # Generate service JWT
            jwt_token = await generate_service_jwt(self.service_name)
            headers["Authorization"] = f"Bearer {jwt_token}"
            
        return headers
    
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with mTLS and JWT.
        
        Args:
            method: HTTP method
            url: Request URL (relative or absolute)
            **kwargs: Additional arguments for httpx
            
        Returns:
            HTTP response
        """
        # Build full URL if base_url is set
        if self.base_url and not url.startswith(("http://", "https://")):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        # Add authentication headers
        headers = await self._get_headers()
        if "headers" in kwargs:
            kwargs["headers"].update(headers)
        else:
            kwargs["headers"] = headers
        
        # Make request
        logger.info(f"Making {method} request to {url}")
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make GET request."""
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make POST request."""
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make PUT request."""
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make DELETE request."""
        return await self.request("DELETE", url, **kwargs)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Factory functions for common service clients
def create_auth_client(service_name: str) -> MTLSClient:
    """Create mTLS client for auth service."""
    return MTLSClient(
        service_name=service_name,
        base_url=settings.AUTH_SERVICE_URL,
        use_mtls=True,
        use_jwt=True
    )


def create_gateway_client(service_name: str) -> MTLSClient:
    """Create mTLS client for gateway service."""
    return MTLSClient(
        service_name=service_name,
        base_url=settings.GATEWAY_URL,
        use_mtls=True,
        use_jwt=True
    )


def create_asset_client(service_name: str) -> MTLSClient:
    """Create mTLS client for asset service."""
    return MTLSClient(
        service_name=service_name,
        base_url=settings.ASSET_SERVICE_URL,
        use_mtls=True,
        use_jwt=True
    )


def create_chat_client(service_name: str) -> MTLSClient:
    """Create mTLS client for chat service."""
    return MTLSClient(
        service_name=service_name,
        base_url=settings.CHAT_SERVICE_URL,
        use_mtls=True,
        use_jwt=True
    )


# Development/testing helpers
if __name__ == "__main__":
    import asyncio
    
    async def test_mtls_client():
        """Test mTLS client functionality."""
        # Test with auth service
        async with create_auth_client("test-service") as client:
            try:
                # Test health endpoint
                response = await client.get("/health")
                print(f"Auth service health: {response.json()}")
                
                # Test with JWT validation
                response = await client.post(
                    "/auth/validate",
                    json={"token": "test-token"}
                )
                print(f"Validation response: {response.json()}")
                
            except Exception as e:
                print(f"Test failed: {e}")
    
    asyncio.run(test_mtls_client())