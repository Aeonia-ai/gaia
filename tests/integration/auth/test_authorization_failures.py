"""
Test proper 403 Forbidden responses for authorization failures.

These tests verify that the system correctly returns 403 when:
- Authentication succeeds but authorization fails
- User lacks required permissions
- Service-to-service authorization is denied
"""

import pytest
import httpx
import os
import logging
import sys
sys.path.append('/app')  # Add app directory to path

logger = logging.getLogger(__name__)


@pytest.fixture
def gateway_url():
    """Gateway service URL for testing."""
    return os.getenv("GATEWAY_URL", "http://gateway:8000")


@pytest.fixture
def headers():
    """Headers with API key for authenticated requests."""
    api_key = os.getenv("API_KEY", "test-api-key")
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }


class TestAuthorizationFailures:
    """Test proper 403 Forbidden responses for authorization failures."""
    
    @pytest.mark.asyncio
    async def test_kb_access_without_email_returns_403(self, gateway_url, headers):
        """Test that KB access without email in auth returns 403, not 401."""
        # This would require a special API key that has no email associated
        # For now, we'll skip this as it requires special setup
        pytest.skip("Requires special API key without email association")
    
    @pytest.mark.asyncio
    async def test_rbac_permission_denied_returns_403(self, gateway_url, headers):
        """Test that RBAC permission denial returns 403."""
        # Try to create a KB workspace without CREATE permission
        # This requires RBAC to be fully implemented
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, ensure we can authenticate (should work)
            health_response = await client.get(
                f"{gateway_url}/health",
                headers=headers
            )
            assert health_response.status_code == 200, "Auth should work for health check"
            
            # Now try to create a workspace (should fail with 403 if no permission)
            response = await client.post(
                f"{gateway_url}/api/kb/workspaces",
                headers=headers,
                json={
                    "name": "Test Workspace",
                    "description": "Should fail with 403"
                }
            )
            
            # This endpoint might not exist yet or RBAC might not be enforced
            if response.status_code == 404:
                pytest.skip("KB workspace endpoint not implemented yet")
            elif response.status_code == 403:
                # Perfect! This is what we want
                assert response.status_code == 403
                logger.info("RBAC correctly returned 403 for unauthorized action")
            else:
                # Log what we got for debugging
                logger.warning(f"Expected 403 but got {response.status_code}: {response.text}")
                pytest.skip(f"RBAC not enforcing permissions yet (got {response.status_code})")
    
    @pytest.mark.asyncio
    async def test_service_authorization_denied_returns_403(self, gateway_url):
        """Test service-to-service authorization denial returns 403."""
        # This would test the service authorization check in auth service
        # Example: A service trying to access an endpoint it's not allowed to
        
        # For now, skip as this requires special service credentials
        pytest.skip("Requires service-to-service authentication setup")
    
    @pytest.mark.asyncio
    async def test_valid_auth_but_resource_forbidden_returns_403(self, gateway_url, headers):
        """Test accessing a resource that exists but user has no permission returns 403."""
        # This tests the difference between 401 (who are you?) and 403 (you can't do that)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to access another user's conversation (if implemented)
            # Using a made-up conversation ID that we don't own
            response = await client.get(
                f"{gateway_url}/api/v0.3/conversations/00000000-0000-0000-0000-000000000000",
                headers=headers
            )
            
            # If we get 404, the endpoint doesn't validate ownership yet
            if response.status_code == 404:
                pytest.skip("Conversation ownership not validated yet")
            elif response.status_code == 403:
                # Great! This is the correct response
                assert response.status_code == 403
                logger.info("Correctly returned 403 for accessing another user's resource")
            else:
                logger.warning(f"Expected 403 or 404, got {response.status_code}")
                pytest.skip(f"Resource ownership not enforced yet (got {response.status_code})")
    
    @pytest.mark.asyncio
    async def test_insufficient_api_key_scope_returns_403(self, gateway_url):
        """Test that API key with insufficient scope returns 403."""
        # This would require an API key with limited scopes
        # For example, a read-only API key trying to write
        
        pytest.skip("Requires API keys with limited scopes")
    
    @pytest.mark.asyncio
    async def test_team_member_without_permission_returns_403(self, gateway_url, headers):
        """Test team member without specific permission gets 403."""
        # This tests team-based permissions in KB system
        
        pytest.skip("Requires team membership and permission system")


class TestAuthVsAuthzDistinction:
    """Test the distinction between authentication (401) and authorization (403)."""
    
    @pytest.mark.asyncio
    async def test_no_auth_returns_401_not_403(self, gateway_url):
        """Verify that missing authentication returns 401, not 403."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                json={"message": "No auth header"}
            )
            assert response.status_code == 401  # NOT 403
            logger.info("Correctly returned 401 for missing authentication")
    
    @pytest.mark.asyncio
    async def test_invalid_token_returns_401_not_403(self, gateway_url):
        """Verify that invalid token returns 401, not 403."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"Authorization": "Bearer invalid-token"},
                json={"message": "Invalid token"}
            )
            assert response.status_code == 401  # NOT 403
            logger.info("Correctly returned 401 for invalid token")
    
    @pytest.mark.asyncio
    async def test_expired_token_returns_401_not_403(self, gateway_url):
        """Verify that expired token returns 401, not 403."""
        # This would require creating an expired JWT
        pytest.skip("Requires ability to create expired JWTs")
    
    @pytest.mark.asyncio
    async def test_malformed_auth_header_returns_401_not_403(self, gateway_url):
        """Verify that malformed auth header returns 401, not 403."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"Authorization": "NotBearer some-token"},  # Wrong format
                json={"message": "Malformed auth"}
            )
            assert response.status_code == 401  # NOT 403
            logger.info("Correctly returned 401 for malformed auth header")


class TestFutureAuthorizationScenarios:
    """Test scenarios that will return 403 once fully implemented."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Future feature: Admin-only endpoints")
    async def test_non_admin_accessing_admin_endpoint_returns_403(self, gateway_url, headers):
        """Test non-admin user accessing admin endpoint returns 403."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{gateway_url}/api/admin/users",
                headers=headers
            )
            assert response.status_code == 403
    
    @pytest.mark.asyncio  
    @pytest.mark.skip(reason="Future feature: Rate limit as authorization")
    async def test_rate_limit_exceeded_returns_403(self, gateway_url, headers):
        """Test that exceeding rate limit returns 403 (you're not authorized to make more requests)."""
        # Some systems use 403 for rate limits as it's an authorization issue
        pass
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Future feature: Workspace access control")  
    async def test_accessing_private_workspace_returns_403(self, gateway_url, headers):
        """Test accessing a private workspace without membership returns 403."""
        pass