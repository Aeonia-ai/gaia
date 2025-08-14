"""
Authentication flow tests for remote environments.

Tests various authentication methods work correctly.
"""

import pytest
import logging
import os
import httpx

logger = logging.getLogger(__name__)


@pytest.mark.remote
@pytest.mark.smoke
class TestRemoteAuthFlow:
    """Test authentication flows in remote environments."""
    
    @pytest.mark.asyncio
    async def test_api_key_authentication(self, remote_gateway, api_key):
        """Verify API key authentication works."""
        # Test with API key in header
        response = await remote_gateway.post(
            "/api/v1/chat",
            json={
                "message": "Hello, testing API key auth",
                "stream": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
        assert "content" in data["choices"][0]["message"]
        
        logger.info("API key authentication successful")
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, remote_config):
        """Verify invalid API keys are rejected."""
        async with httpx.AsyncClient(
            base_url=remote_config["gateway_url"],
            timeout=remote_config["timeout"],
            headers={"X-API-Key": "invalid-key-12345"}
        ) as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "This should fail"}
            )
            
            assert response.status_code == 401
            assert "detail" in response.json()
    
    @pytest.mark.asyncio
    async def test_missing_auth_rejected(self, remote_config):
        """Verify requests without authentication are rejected."""
        async with httpx.AsyncClient(
            base_url=remote_config["gateway_url"],
            timeout=remote_config["timeout"]
        ) as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "No auth provided"}
            )
            
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("TEST_ENV") == "production",
        reason="JWT login testing not allowed in production"
    )
    async def test_jwt_authentication_flow(self, remote_auth, remote_gateway, remote_test_user):
        """Test JWT authentication flow (login → use token → refresh)."""
        # Step 1: Login to get JWT
        login_response = await remote_auth.post(
            "/auth/login",
            json={
                "email": remote_test_user["email"],
                "password": remote_test_user["password"]
            }
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Test user login failed: {login_response.text}")
        
        auth_data = login_response.json()
        access_token = auth_data.get("access_token")
        refresh_token = auth_data.get("refresh_token")
        
        assert access_token, "No access token received"
        assert refresh_token, "No refresh token received"
        
        # Step 2: Use JWT for API call
        async with httpx.AsyncClient(
            base_url=remote_gateway.base_url,
            timeout=remote_gateway.timeout,
            headers={"Authorization": f"Bearer {access_token}"}
        ) as jwt_client:
            response = await jwt_client.post(
                "/api/v1/chat",
                json={"message": "Testing JWT auth"}
            )
            
            assert response.status_code == 200
            assert "choices" in response.json()
        
        logger.info("JWT authentication flow successful")
    
    @pytest.mark.asyncio
    async def test_concurrent_auth_requests(self, remote_gateway, track_response_time):
        """Test multiple concurrent authenticated requests."""
        import asyncio
        
        async def make_request(index: int):
            response = await remote_gateway.post(
                "/api/v1/chat",
                json={"message": f"Concurrent request {index}"}
            )
            return response.status_code
        
        track_response_time.start()
        
        # Make 5 concurrent requests
        tasks = [make_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        track_response_time.assert_under(10.0, "5 concurrent requests")
        
        # All should succeed
        assert all(status == 200 for status in results)