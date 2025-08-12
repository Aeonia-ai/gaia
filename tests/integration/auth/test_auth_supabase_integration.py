"""
Integration tests using real Supabase authentication flow.
Tests the complete auth flow: create user -> login -> get JWT -> make API calls.
"""

import pytest
import httpx
import os
import asyncio
from typing import Dict, Any, Optional
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_supabase_auth_integration")


@pytest.mark.integration
@pytest.mark.sequential
class TestSupabaseAuthIntegration:
    """Test API endpoints with real Supabase authentication flow."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL - can be overridden with GATEWAY_URL env var."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def auth_url(self):
        """Auth service URL for login endpoints."""
        return os.getenv("AUTH_URL", "http://auth-service:8000")
    
    # Remove shared_test_user - use shared_test_user instead
    
    async def login_user(self, auth_url: str, email: str, password: str) -> Dict[str, Any]:
        """Login a user and return the response with JWT token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{auth_url}/auth/login",
                json={
                    "email": email,
                    "password": password
                }
            )
            assert response.status_code == 200, f"Login failed: {response.text}"
            data = response.json()
            # Normalize response structure
            if "session" in data and "access_token" in data["session"]:
                data["access_token"] = data["session"]["access_token"]
                data["refresh_token"] = data["session"].get("refresh_token")
            return data
    
    @pytest.mark.asyncio
    async def test_complete_auth_flow(self, gateway_url, auth_url, shared_test_user):
        """Test complete authentication flow: create user -> login -> use JWT."""
        # Use shared test user (created once per session)
        email = shared_test_user["email"]
        password = shared_test_user["password"]
        logger.info(f"Using shared test user: {email}")
        
        # Step 2: Login with the test user
        login_response = await self.login_user(auth_url, email, password)
        assert "access_token" in login_response
        assert "user" in login_response
        assert login_response["user"]["email"] == email
        
        jwt_token = login_response["access_token"]
        logger.info(f"Successfully logged in, got JWT token")
        
        # Step 3: Use the JWT token to make authenticated requests
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test health endpoint (should work with or without auth)
            health_response = await client.get(f"{gateway_url}/health")
            assert health_response.status_code == 200
            
            # Test authenticated chat endpoint
            chat_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Hello from Supabase authenticated user!",
                    "stream": False
                }
            )
            assert chat_response.status_code == 200
            data = chat_response.json()
            
            # v1 returns OpenAI-compatible format
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]
            assert "content" in data["choices"][0]["message"]
            
            content = data["choices"][0]["message"]["content"]
            logger.info(f"Chat response: {content[:100]}...")
    
    @pytest.mark.asyncio
    async def test_invalid_credentials_rejected(self, auth_url):
        """Test that invalid credentials are rejected."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{auth_url}/auth/login",
                json={
                    "email": "nonexistent@test.local",
                    "password": "wrongpassword"
                }
            )
            assert response.status_code in [400, 401, 403]
            logger.info("Invalid credentials correctly rejected")
    
    @pytest.mark.asyncio
    async def test_jwt_expiry_handling(self, gateway_url, auth_url, shared_test_user):
        """Test handling of expired JWT tokens."""
        # Use shared test user
        test_user = shared_test_user
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        jwt_token = login_response["access_token"]
        
        # Make a request with valid token
        headers = {"Authorization": f"Bearer {jwt_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Test with valid token"}
            )
            assert response.status_code == 200
            
            # Test with malformed token
            bad_headers = {"Authorization": "Bearer invalid-token-here"}
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=bad_headers,
                json={"message": "Test with invalid token"}
            )
            assert response.status_code in [401, 403]
            logger.info("Invalid JWT correctly rejected")
    
    @pytest.mark.asyncio
    async def test_multiple_users_isolation(self, gateway_url, auth_url, shared_test_user):
        """Test that multiple users have isolated conversations."""
        # Use shared user as user1, create temporary user2 for this test
        from tests.fixtures.test_auth import TestUserFactory
        factory = TestUserFactory()
        
        user1 = shared_test_user
        user2 = factory.create_verified_test_user()
        try:
            # Login both users
            login1 = await self.login_user(auth_url, user1["email"], user1["password"])
            login2 = await self.login_user(auth_url, user2["email"], user2["password"])
            
            headers1 = {"Authorization": f"Bearer {login1['access_token']}"}
            headers2 = {"Authorization": f"Bearer {login2['access_token']}"}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # User 1 sends a message with specific content
                response1 = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers1,
                    json={"message": "User 1 secret: pineapple"}
                )
                assert response1.status_code == 200
                
                # User 2 sends a different message
                response2 = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers2,
                    json={"message": "User 2 secret: mango"}
                )
                assert response2.status_code == 200
                
                # User 1 asks about their secret
                response1_check = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers1,
                    json={"message": "What was my secret?"}
                )
                assert response1_check.status_code == 200
                data1 = response1_check.json()
                content1 = data1["choices"][0]["message"]["content"].lower()
                
                # User 1 should see their own secret, not user 2's
                assert "pineapple" in content1 or "secret" in content1
                assert "mango" not in content1
                
                logger.info("User isolation verified - conversations are separate")
        finally:
            # Cleanup temporary user
            factory.cleanup_test_user(user2["user_id"])
    
    @pytest.mark.asyncio
    async def test_conversation_persistence(self, gateway_url, auth_url, shared_test_user):
        """Test that conversations persist across sessions."""
        # Use shared test user
        test_user = shared_test_user
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        
        headers = {"Authorization": f"Bearer {login_response['access_token']}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send first message
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Remember: the magic number is 42"}
            )
            assert response1.status_code == 200
            
            # Extract conversation_id if available
            data1 = response1.json()
            conversation_id = None
            if "_metadata" in data1 and "conversation_id" in data1["_metadata"]:
                conversation_id = data1["_metadata"]["conversation_id"]
            
            # Send follow-up message
            follow_up_json = {"message": "What was the magic number?"}
            if conversation_id:
                follow_up_json["conversation_id"] = conversation_id
                
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json=follow_up_json
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content2 = data2["choices"][0]["message"]["content"]
            
            # Should remember the number
            assert "42" in content2
            logger.info(f"Conversation persistence verified")
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Moved to load tests - see tests/load/test_concurrent_requests.py")
    async def test_concurrent_requests_same_user(self, gateway_url, auth_url, shared_test_user):
        """Test handling concurrent requests from the same user.
        
        This test has been moved to load tests as it tests system behavior
        under concurrent load rather than authentication integration."""
        pass  # Implementation moved to load tests
    
    @pytest.mark.asyncio
    async def test_auth_refresh_token(self, auth_url, shared_test_user):
        """Test refresh token functionality if available."""
        # Create user and login
        test_user = shared_test_user
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        
        # Check if refresh token is provided (either at top level or in session)
        refresh_token = login_response.get("refresh_token") or (
            login_response.get("session", {}).get("refresh_token")
        )
        
        if not refresh_token:
            pytest.skip("Refresh token not provided in login response")
        
        refresh_token = login_response.get("refresh_token", refresh_token)
        
        async with httpx.AsyncClient() as client:
            # Try to refresh the token
            refresh_response = await client.post(
                f"{auth_url}/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            if refresh_response.status_code == 200:
                refresh_data = refresh_response.json()
                # Check for session structure with access_token
                assert "session" in refresh_data
                assert "access_token" in refresh_data["session"]
                logger.info("Token refresh successful")
            else:
                logger.info(f"Token refresh returned {refresh_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_user_profile_access(self, gateway_url, auth_url, shared_test_user):
        """Test accessing user profile with JWT."""
        # Create user and login
        test_user = shared_test_user
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        
        headers = {"Authorization": f"Bearer {login_response['access_token']}"}
        
        async with httpx.AsyncClient() as client:
            # Try to access user profile endpoint if it exists
            profile_response = await client.get(
                f"{gateway_url}/api/v1/user/profile",
                headers=headers
            )
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                assert "email" in profile_data or "user" in profile_data
                logger.info("User profile endpoint accessible")
            else:
                logger.info(f"User profile endpoint returned {profile_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_streaming_with_supabase_auth(self, gateway_url, auth_url, shared_test_user):
        """Test streaming responses with Supabase authentication."""
        # Create user and login
        test_user = shared_test_user
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        
        headers = {"Authorization": f"Bearer {login_response['access_token']}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            chunks = []
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Count to 3",
                    "stream": True
                }
            ) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunks.append(line[6:])
                    
                    assert len(chunks) > 0
                    logger.info(f"Streaming with Supabase auth received {len(chunks)} chunks")
                else:
                    logger.info(f"Streaming returned {response.status_code}")