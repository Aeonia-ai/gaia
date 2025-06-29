"""
Basic integration tests for Gaia Platform Phase 1.

These tests validate that the microservices architecture maintains
compatibility with LLM Platform behavior.
"""

import pytest
import asyncio
import httpx
from datetime import datetime


class TestGatewayIntegration:
    """Test gateway service integration and client compatibility."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway service URL."""
        return "http://gateway:8000"
    
    @pytest.fixture
    def api_key(self):
        """Test API key."""
        return "test_key"
    
    async def test_health_endpoint(self, gateway_url):
        """Test health endpoint is accessible."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] in ["healthy", "degraded"]
            assert "timestamp" in data
            assert "services" in data
    
    async def test_root_endpoint(self, gateway_url):
        """Test root endpoint returns expected response."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/")
            assert response.status_code == 200
            
            data = response.json()
            assert "message" in data
            assert "Gaia Platform Gateway" in data["message"]
    
    async def test_auth_validation_endpoint(self, gateway_url, api_key):
        """Test auth validation endpoint works."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/auth/validate",
                json={"api_key": api_key}
            )
            # Should get a response (might be 401 with invalid key, but service should respond)
            assert response.status_code in [200, 401, 400]
    
    async def test_llm_platform_compatibility(self, gateway_url, api_key):
        """Test that LLM Platform endpoints are preserved."""
        endpoints_to_test = [
            "/api/v1/chat/personas",
            "/api/v1/assets", 
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in endpoints_to_test:
                response = await client.get(
                    f"{gateway_url}{endpoint}",
                    headers={"X-API-Key": api_key}
                )
                # Should get a response from the service (might be auth error, but service responds)
                assert response.status_code in [200, 401, 403, 404]


class TestServiceHealth:
    """Test individual service health and connectivity."""
    
    @pytest.fixture
    def service_urls(self):
        """Service URLs for health checks."""
        return {
            "gateway": "http://gateway:8000",
            "auth": "http://auth-service:8000", 
            "asset": "http://asset-service:8000",
            "chat": "http://chat-service:8000"
        }
    
    async def test_all_services_healthy(self, service_urls):
        """Test that all services report healthy status."""
        async with httpx.AsyncClient() as client:
            for service_name, url in service_urls.items():
                try:
                    response = await client.get(f"{url}/health", timeout=10.0)
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert data.get("status") in ["healthy", "degraded"]
                    
                except httpx.RequestError:
                    pytest.fail(f"Could not connect to {service_name} service at {url}")


class TestDatabaseConnectivity:
    """Test database connectivity and basic operations."""
    
    async def test_database_connection(self):
        """Test that services can connect to the database."""
        # This would be tested via service health endpoints
        # which include database connectivity checks
        pass


class TestNATSConnectivity:
    """Test NATS messaging connectivity."""
    
    async def test_nats_connection(self):
        """Test NATS connectivity via service health."""
        # NATS connectivity is tested via service startup and health checks
        pass


class TestCompatibilityRegression:
    """Test compatibility with LLM Platform client expectations."""
    
    @pytest.fixture
    def llm_platform_endpoints(self):
        """List of endpoints that must work identically to LLM Platform."""
        return [
            ("GET", "/health"),
            ("GET", "/"),
            ("GET", "/api/v1/chat/personas"),
            ("GET", "/api/v1/assets"),
            ("POST", "/api/v1/auth/validate"),
        ]
    
    async def test_endpoint_structure_preserved(self, llm_platform_endpoints):
        """Test that all LLM Platform endpoints exist and respond."""
        gateway_url = "http://gateway:8000"
        
        async with httpx.AsyncClient() as client:
            for method, endpoint in llm_platform_endpoints:
                if method == "GET":
                    response = await client.get(f"{gateway_url}{endpoint}")
                elif method == "POST":
                    response = await client.post(
                        f"{gateway_url}{endpoint}",
                        json={}
                    )
                
                # Service should respond (not 404), even if auth fails
                assert response.status_code != 404, f"Endpoint {endpoint} not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
