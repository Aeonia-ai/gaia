"""
Comprehensive API authentication tests for Gaia Platform.
Tests authentication across all API versions consistently.
"""

import pytest
import httpx
import os
from typing import Dict, Any
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestAuthManager

logger = setup_service_logger("test_api_auth_comprehensive")


class TestAPIAuthenticationComprehensive:
    """Test API authentication methods across all versions."""
    
    pytestmark = pytest.mark.xdist_group("api_auth_comprehensive")
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway service URL for testing."""
        return "http://gateway:8000"
    
    @pytest.fixture
    def auth_manager(self):
        """Provide test authentication manager."""
        return TestAuthManager(test_type="unit")
    
    @pytest.fixture
    def protected_endpoints(self, gateway_url):
        """List of protected endpoints across all API versions."""
        return [
            f"{gateway_url}/api/v0.2/chat",
            f"{gateway_url}/api/v0.3/chat",
            f"{gateway_url}/api/v1/chat",
        ]
    
    @pytest.mark.asyncio
    async def test_no_auth_fails_all_versions(self, protected_endpoints):
        """Test that protected endpoints fail without authentication across all versions."""
        async with httpx.AsyncClient() as client:
            for endpoint in protected_endpoints:
                response = await client.post(
                    endpoint,
                    json={"message": "This should fail"}
                )
                assert response.status_code in [401, 403], f"Endpoint {endpoint} should require auth"
                logger.info(f"✅ {endpoint} properly requires authentication")
    
    @pytest.mark.asyncio
    async def test_invalid_jwt_fails_all_versions(self, protected_endpoints):
        """Test that invalid JWT token fails across all versions."""
        # Create headers with invalid JWT
        headers = {
            "Authorization": "Bearer invalid-jwt-token",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            for endpoint in protected_endpoints:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    json={"message": "This should fail"}
                )
                assert response.status_code in [401, 403], f"Invalid JWT should fail for {endpoint}"
                logger.info(f"✅ {endpoint} properly rejects invalid JWT")
    
    @pytest.mark.asyncio
    async def test_valid_jwt_works_all_versions(self, protected_endpoints, auth_manager):
        """Test that valid JWT token works across all versions."""
        # Get valid JWT auth headers
        auth_headers = auth_manager.get_auth_headers(
            email="test@test.local",
            role="authenticated"
        )
        headers = {
            **auth_headers,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in protected_endpoints:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    json={"message": "Hello! This should work."}
                )
                # Should work or at least not be an auth error
                assert response.status_code not in [401, 403], f"Valid JWT should work for {endpoint}: {response.status_code}"
                logger.info(f"✅ {endpoint} accepts valid JWT (status: {response.status_code})")
    
    
    @pytest.mark.asyncio
    async def test_auth_consistency_across_versions(self, gateway_url, auth_manager):
        """Test that authentication behavior is consistent across all API versions."""
        auth_headers = auth_manager.get_auth_headers(
            email="test@test.local",
            role="authenticated"
        )
        headers = {
            **auth_headers,
            "Content-Type": "application/json"
        }
        
        # Test different API versions with same auth
        api_tests = [
            (f"{gateway_url}/api/v0.2/chat", {"message": "v0.2 auth test"}),
            (f"{gateway_url}/api/v0.3/chat", {"message": "v0.3 auth test"}),
            (f"{gateway_url}/api/v1/chat", {"message": "v1 auth test"}),
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint, payload in api_tests:
                response = await client.post(endpoint, headers=headers, json=payload)
                
                # All should succeed with same auth
                assert response.status_code not in [401, 403], f"Auth failed for {endpoint}"
                assert response.status_code < 500, f"Server error for {endpoint}: {response.status_code}"
                
                logger.info(f"✅ Authentication consistent for {endpoint}")
    
    
    @pytest.mark.asyncio
    async def test_role_based_access_validation(self, gateway_url, auth_manager):
        """Test that different user roles work consistently."""
        # Test different roles
        roles_to_test = ["authenticated", "admin"]
        
        for role in roles_to_test:
            auth_headers = auth_manager.get_auth_headers(
                email=f"test-{role}@test.local",
                role=role
            )
            headers = {
                **auth_headers,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={"message": f"Testing {role} role"}
                )
                
                # Should work for all valid roles
                assert response.status_code not in [401, 403], f"Role {role} should have access"
                logger.info(f"✅ Role '{role}' has proper access")


class TestAPICompatibilityAuth:
    """Test API compatibility authentication patterns."""
    
    pytestmark = pytest.mark.xdist_group("api_compatibility_auth")
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway service URL for testing."""
        return "http://gateway:8000"
    
    @pytest.fixture
    def auth_manager(self):
        """Provide test authentication manager."""
        return TestAuthManager(test_type="unit")
    
    @pytest.fixture
    def headers(self, auth_manager):
        """Standard headers with JWT authentication."""
        auth_headers = auth_manager.get_auth_headers(
            email="test@test.local",
            role="authenticated"
        )
        return {
            **auth_headers,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_cross_version_auth_interoperability(self, gateway_url, headers):
        """Test that authentication works across API versions without changes."""
        test_message = "Cross-version auth test"
        
        # Same auth should work for all versions
        version_tests = [
            ("v0.2", f"{gateway_url}/api/v0.2/chat", {"message": test_message}),
            ("v0.3", f"{gateway_url}/api/v0.3/chat", {"message": test_message}),
            ("v1", f"{gateway_url}/api/v1/chat", {"message": test_message}),
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for version, endpoint, payload in version_tests:
                response = await client.post(endpoint, headers=headers, json=payload)
                
                assert response.status_code == 200, f"{version} auth failed: {response.status_code}"
                logger.info(f"✅ {version} API authenticated successfully")
        
        logger.info("All API versions accept same authentication consistently")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])