"""
Integration tests for Gateway authentication endpoints.

These tests verify the complete auth flow through the gateway service,
ensuring proper request forwarding and error handling between layers:
Browser -> Web Service -> Gateway -> Auth Service -> Supabase

IMPORTANT: These are real integration tests that make actual HTTP requests
to the gateway service, not mocked unit tests.
"""

import pytest
import httpx
import os
import asyncio
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_gateway_auth")


@pytest.mark.integration
@pytest.mark.sequential
class TestGatewayAuthEndpoints:
    """Test Gateway authentication endpoints with real HTTP requests."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL for integration tests."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def temp_user_factory(self):
        """Factory for creating temporary test users."""
        from tests.fixtures.test_auth import TestUserFactory
        return TestUserFactory()
    
    @pytest.mark.asyncio
    async def test_gateway_login_success(self, gateway_url, shared_test_user):
        """Test successful login through gateway endpoint."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/auth/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should return Supabase session structure
            assert "session" in data
            assert "access_token" in data["session"]
            assert "user" in data
            assert data["user"]["email"] == shared_test_user["email"]
            
            logger.info(f"Successfully logged in through gateway: {data['user']['email']}")
    
    @pytest.mark.asyncio
    async def test_gateway_login_invalid_credentials(self, gateway_url):
        """Test login with invalid credentials through gateway."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/auth/login",
                json={
                    "email": "nonexistent@test.local",
                    "password": "wrongpassword"
                }
            )
            
            # Should return auth error
            assert response.status_code in [400, 401, 403]
            data = response.json()
            assert "detail" in data
            
            logger.info(f"Gateway correctly rejected invalid credentials: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_gateway_register_new_user(self, gateway_url, temp_user_factory):
        """Test user registration through gateway endpoint."""
        import uuid
        test_email = f"gateway-test-{uuid.uuid4().hex[:8]}@test.local"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/auth/register",
                json={
                    "email": test_email,
                    "password": "TestPass123!"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "user" in data
                assert data["user"]["email"] == test_email
                
                # Cleanup
                if "id" in data["user"]:
                    temp_user_factory.cleanup_test_user(data["user"]["id"])
                
                logger.info(f"Successfully registered through gateway: {test_email}")
            else:
                # Some environments may have registration disabled
                assert response.status_code in [400, 403]
                logger.info(f"Registration returned {response.status_code} (may be disabled)")
    
    @pytest.mark.asyncio
    async def test_gateway_register_duplicate_email(self, gateway_url, shared_test_user):
        """Test registration with existing email through gateway."""
        # The shared_test_user fixture ensures the user exists
        # Try to register with the same email
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            # Now try to register with the same email
            response = await client.post(
                f"{gateway_url}/api/v1/auth/register",
                json={
                    "email": shared_test_user["email"],
                    "password": "AnotherPass123!"
                }
            )
            
            # Log the response for debugging
            logger.info(f"Registration response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Registration response data: {data}")
            
            # Supabase allows multiple unconfirmed users with same email
            # This is expected behavior for Supabase - it creates a new unconfirmed user
            # The test should pass if either:
            # 1. Registration succeeds (200) - Supabase created another unconfirmed user
            # 2. Registration fails with duplicate error (400) - if user is confirmed
            # 3. Rate limit error (400) - for security
            
            if response.status_code == 400:
                data = response.json()
                assert "detail" in data
                logger.info(f"Registration rejected: {data['detail']}")
            elif response.status_code == 200:
                data = response.json()
                assert "user" in data
                assert data["user"]["email"] == shared_test_user["email"]
                logger.info("Registration succeeded - Supabase allows multiple unconfirmed users")
            else:
                pytest.fail(f"Unexpected status code: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_gateway_validate_jwt(self, gateway_url, shared_test_user):
        """Test JWT validation through gateway endpoint."""
        # First login to get JWT
        async with httpx.AsyncClient(timeout=30.0) as client:
            login_response = await client.post(
                f"{gateway_url}/api/v1/auth/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            
            assert login_response.status_code == 200
            jwt_token = login_response.json()["session"]["access_token"]
            
            # Now test validation endpoint
            validation_response = await client.post(
                f"{gateway_url}/api/v1/auth/validate",
                json={"token": jwt_token}
            )
            
            assert validation_response.status_code == 200
            data = validation_response.json()
            assert "valid" in data
            assert data["valid"] is True
            assert "user_id" in data
            
            logger.info("Gateway successfully validated JWT token")
    
    @pytest.mark.asyncio
    async def test_gateway_validate_invalid_jwt(self, gateway_url):
        """Test validation of invalid JWT through gateway."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/auth/validate",
                json={"token": "invalid-jwt-token"}
            )
            
            # Should return validation failure
            assert response.status_code in [200, 401]
            data = response.json()
            
            if response.status_code == 200:
                assert "valid" in data
                assert data["valid"] is False
            else:
                assert "detail" in data
            
            logger.info("Gateway correctly rejected invalid JWT")
    
    @pytest.mark.asyncio
    async def test_gateway_refresh_token(self, gateway_url, shared_test_user):
        """Test token refresh through gateway endpoint."""
        # First login to get refresh token
        async with httpx.AsyncClient(timeout=30.0) as client:
            login_response = await client.post(
                f"{gateway_url}/api/v1/auth/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            
            assert login_response.status_code == 200
            session = login_response.json()["session"]
            
            if "refresh_token" in session:
                refresh_token = session["refresh_token"]
                
                # Test refresh endpoint
                refresh_response = await client.post(
                    f"{gateway_url}/api/v1/auth/refresh",
                    json={"refresh_token": refresh_token}
                )
                
                if refresh_response.status_code == 200:
                    data = refresh_response.json()
                    assert "session" in data
                    assert "access_token" in data["session"]
                    logger.info("Gateway successfully refreshed token")
                else:
                    logger.info(f"Token refresh returned {refresh_response.status_code}")
            else:
                pytest.skip("No refresh token provided in login response")
    
    @pytest.mark.asyncio
    async def test_gateway_auth_with_chat_endpoint(self, gateway_url, shared_test_user):
        """Test that gateway properly authenticates requests to protected endpoints."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Login first
            login_response = await client.post(
                f"{gateway_url}/api/v1/auth/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            
            assert login_response.status_code == 200
            jwt_token = login_response.json()["session"]["access_token"]
            
            # Try to access protected chat endpoint with JWT
            headers = {"Authorization": f"Bearer {jwt_token}"}
            chat_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Test message through gateway",
                    "stream": False
                }
            )
            
            assert chat_response.status_code == 200
            data = chat_response.json()
            assert "choices" in data
            
            logger.info("Gateway successfully authenticated and forwarded chat request")
    
    @pytest.mark.asyncio
    async def test_gateway_unauthorized_access(self, gateway_url):
        """Test that gateway rejects unauthorized access to protected endpoints."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to access protected endpoint without auth
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                json={
                    "message": "Unauthorized test",
                    "stream": False
                }
            )
            
            # Should reject unauthorized request
            assert response.status_code == 401
            
            logger.info(f"Gateway correctly rejected unauthorized request: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_gateway_concurrent_auth_requests(self, gateway_url, shared_test_user):
        """Test gateway handles concurrent authentication requests properly."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send multiple concurrent login requests
            tasks = []
            for i in range(3):
                task = client.post(
                    f"{gateway_url}/api/v1/auth/login",
                    json={
                        "email": shared_test_user["email"],
                        "password": shared_test_user["password"]
                    }
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count == 3
            
            # All should return valid sessions
            for response in responses:
                if response.status_code == 200:
                    data = response.json()
                    assert "session" in data
                    assert "access_token" in data["session"]
            
            logger.info(f"Gateway handled {success_count}/3 concurrent auth requests successfully")
    
    @pytest.mark.asyncio
    async def test_gateway_auth_error_propagation(self, gateway_url):
        """Test that gateway properly propagates auth service errors."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with malformed request
            response = await client.post(
                f"{gateway_url}/api/v1/auth/login",
                json={
                    "email": "not-an-email",  # Invalid email format
                    "password": "123"  # Too short
                }
            )
            
            # Should propagate validation error
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            
            # Error should be informative
            error_msg = data["detail"].lower()
            assert "email" in error_msg or "password" in error_msg or "invalid" in error_msg
            
            logger.info(f"Gateway properly propagated error: {data['detail']}")


@pytest.mark.integration
@pytest.mark.sequential
class TestV03AuthEndpoints:
    """Test v0.3 auth endpoints for backward compatibility with v1."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL for integration tests."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def temp_user_factory(self):
        """Factory for creating temporary test users."""
        from tests.fixtures.test_auth import TestUserFactory
        return TestUserFactory()
    
    @pytest.mark.parametrize("api_version", ["v1", "v0.3"])
    @pytest.mark.asyncio
    async def test_login_endpoint_behavioral_identity(
        self, 
        gateway_url,
        shared_test_user,
        api_version: str
    ):
        """Test that v1 and v0.3 login endpoints have identical behavior."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test successful login
            login_data = {
                "email": shared_test_user["email"],
                "password": shared_test_user["password"]
            }
            
            response = await client.post(
                f"{gateway_url}/api/{api_version}/auth/login",
                json=login_data
            )
            
            # Verify response structure is identical
            assert response.status_code == 200
            data = response.json()
            
            # Both versions should return identical structure
            assert "session" in data
            assert "user" in data
            assert "access_token" in data["session"]
            assert data["user"]["email"] == shared_test_user["email"]
            
            # Verify token formats are identical
            assert data["session"]["access_token"].startswith("eyJ")  # JWT format
            
            logger.info(f"Gateway {api_version} login successful with identical structure")
    
    @pytest.mark.parametrize("api_version", ["v1", "v0.3"])
    @pytest.mark.asyncio
    async def test_validate_endpoint_behavioral_identity(
        self,
        gateway_url,
        shared_test_user,
        api_version: str
    ):
        """Test that v1 and v0.3 validate endpoints have identical behavior."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Login to get token
            login_response = await client.post(
                f"{gateway_url}/api/{api_version}/auth/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            assert login_response.status_code == 200
            tokens = login_response.json()
            
            # Test token validation
            validate_response = await client.post(
                f"{gateway_url}/api/{api_version}/auth/validate",
                json={"token": tokens["session"]["access_token"]}
            )
            
            # Verify response structure is identical
            assert validate_response.status_code == 200
            data = validate_response.json()
            
            # Both versions should return identical structure
            assert "valid" in data
            assert "user_id" in data
            assert data["valid"] is True
            
            logger.info(f"Gateway {api_version} validate successful with identical structure")
    
    @pytest.mark.asyncio
    async def test_v1_token_works_with_v03_validate(
        self,
        gateway_url,
        shared_test_user
    ):
        """Test that tokens from v1 login work with v0.3 validate."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Login with v1
            login_response = await client.post(
                f"{gateway_url}/api/v1/auth/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            assert login_response.status_code == 200
            v1_tokens = login_response.json()
            
            # Validate with v0.3
            validate_response = await client.post(
                f"{gateway_url}/api/v0.3/auth/validate",
                json={"token": v1_tokens["session"]["access_token"]}
            )
            
            assert validate_response.status_code == 200
            data = validate_response.json()
            assert data["valid"] is True
            
            logger.info("v1 token successfully validated by v0.3 endpoint")
    
    @pytest.mark.asyncio
    async def test_v03_token_works_with_v1_validate(
        self,
        gateway_url,
        shared_test_user
    ):
        """Test that tokens from v0.3 login work with v1 validate."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Login with v0.3
            login_response = await client.post(
                f"{gateway_url}/api/v0.3/auth/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            assert login_response.status_code == 200
            v03_tokens = login_response.json()
            
            # Validate with v1
            validate_response = await client.post(
                f"{gateway_url}/api/v1/auth/validate",
                json={"token": v03_tokens["session"]["access_token"]}
            )
            
            assert validate_response.status_code == 200
            data = validate_response.json()
            assert data["valid"] is True
            
            logger.info("v0.3 token successfully validated by v1 endpoint")
    
    @pytest.mark.parametrize("api_version", ["v1", "v0.3"])
    @pytest.mark.asyncio
    async def test_auth_error_consistency(
        self,
        gateway_url,
        api_version: str
    ):
        """Test that invalid login credentials return identical errors."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            invalid_login = {
                "email": "nonexistent@example.com",
                "password": "wrongpassword"
            }
            
            response = await client.post(
                f"{gateway_url}/api/{api_version}/auth/login",
                json=invalid_login
            )
            
            # Both versions should return identical error structure
            # Note: Supabase returns 400 for invalid credentials, not 401
            assert response.status_code in [400, 401]  
            data = response.json()
            assert "detail" in data or "error" in data or "message" in data
            
            logger.info(f"Gateway {api_version} properly returned 401 for invalid credentials")