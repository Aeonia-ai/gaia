"""
System health and infrastructure regression test suite for Gaia Platform.
Tests core system functionality that should work across all API versions.
"""

import pytest
import httpx
import os
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_system_health_regression")


class TestSystemHealthRegression:
    """Test system health endpoints for regression."""
    
    pytestmark = pytest.mark.xdist_group("system_health_regression")
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway service URL for testing."""
        return "http://gateway:8000"
    
    @pytest.mark.asyncio
    async def test_gateway_health_regression(self, gateway_url):
        """Test main gateway health endpoint regression."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health")
            assert response.status_code == 200, "Gateway health should always work"
            data = response.json()
            assert data.get("status") in ["healthy", "degraded"], f"Invalid health status: {data}"
            assert "services" in data, "Health should include services info"
            assert "timestamp" in data, "Health should include timestamp"
            logger.info(f"Gateway health: {data['status']}")
    
    @pytest.mark.asyncio
    async def test_root_endpoint_regression(self, gateway_url):
        """Test root endpoint returns version info regression."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/")
            assert response.status_code == 200, "Root endpoint should always work"
            data = response.json()
            assert "message" in data or "version" in data, "Root should have message or version"
            logger.info(f"Root endpoint response: {data}")
    
    @pytest.mark.asyncio
    async def test_options_cors_regression(self, gateway_url):
        """Test OPTIONS requests for CORS regression."""
        async with httpx.AsyncClient() as client:
            response = await client.options(f"{gateway_url}/api/v1/chat")
            # Should handle OPTIONS (either 200 or 405, but not 500)
            assert response.status_code not in [500, 502, 503], "OPTIONS should not cause server error"
            logger.info(f"OPTIONS CORS handling: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_invalid_endpoint_regression(self, gateway_url):
        """Test that invalid endpoints return proper 404."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v999/nonexistent")
            assert response.status_code == 404, "Invalid endpoints should return 404"
            logger.info("Invalid endpoint properly returns 404")
    
    @pytest.mark.asyncio
    async def test_malformed_json_handling_regression(self, gateway_url):
        """Test malformed JSON handling regression."""
        headers = {
            "X-API-Key": os.getenv("API_KEY", "test-key-123"),
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            # Send malformed JSON
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                content='{"message": "incomplete json'  # Malformed
            )
            # Should handle gracefully (400 bad request, not 500)
            assert response.status_code in [400, 422], "Malformed JSON should return 400/422"
            logger.info(f"Malformed JSON handling: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_large_request_handling_regression(self, gateway_url):
        """Test large request handling regression."""
        headers = {
            "X-API-Key": os.getenv("API_KEY", "test-key-123"),
            "Content-Type": "application/json"
        }
        
        # Create a large but reasonable message
        large_message = "This is a test message. " * 500  # ~12KB
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": large_message}
            )
            # Should either process successfully or reject with clear error
            assert response.status_code not in [500, 502, 503], "Large requests should not cause server error"
            logger.info(f"Large request handling: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling_regression(self, gateway_url):
        """Test that system handles concurrent requests without crashing."""
        headers = {
            "X-API-Key": os.getenv("API_KEY", "test-key-123"),
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send 3 concurrent requests (not load testing, just basic concurrency)
            import asyncio
            tasks = []
            for i in range(3):
                task = client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={"message": f"Concurrent test {i+1}"}
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # At least most should succeed (allowing for some rate limiting)
            successful = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code < 500)
            assert successful >= 2, f"Concurrent requests causing server errors: {successful}/3 successful"
            logger.info(f"Concurrent request handling: {successful}/3 successful")


class TestSystemInfrastructureRegression:
    """Test system infrastructure components."""
    
    pytestmark = pytest.mark.xdist_group("system_infrastructure_regression")
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    @pytest.mark.asyncio
    async def test_response_headers_regression(self, gateway_url):
        """Test that important response headers are present."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health")
            
            # Check important headers
            assert "content-type" in response.headers, "Content-Type header missing"
            assert response.headers["content-type"].startswith("application/json"), "Wrong content type"
            
            # Security headers (if implemented)
            security_headers = ["x-content-type-options", "x-frame-options", "vary"]
            present_headers = [h for h in security_headers if h in response.headers]
            logger.info(f"Security headers present: {present_headers}")
    
    @pytest.mark.asyncio
    async def test_http_method_support_regression(self, gateway_url):
        """Test that proper HTTP methods are supported/rejected."""
        async with httpx.AsyncClient() as client:
            # GET on health should work
            get_response = await client.get(f"{gateway_url}/health")
            assert get_response.status_code == 200, "GET on health should work"
            
            # POST on health should not work
            post_response = await client.post(f"{gateway_url}/health")
            assert post_response.status_code in [405, 404], "POST on health should not work"
            
            logger.info("HTTP method restrictions work correctly")
    
    @pytest.mark.asyncio
    async def test_content_encoding_regression(self, gateway_url):
        """Test that content encoding works."""
        headers = {"Accept-Encoding": "gzip, deflate"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health", headers=headers)
            assert response.status_code == 200, "Gzip requests should work"
            # Response should still be readable (httpx handles decompression)
            data = response.json()
            assert "status" in data, "Compressed response should be readable"
            logger.info(f"Content encoding: {response.headers.get('content-encoding', 'none')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])