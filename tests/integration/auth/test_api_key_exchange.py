"""
Test API key to JWT exchange endpoint.
Tests the /auth/api-key-login endpoint that exchanges API keys for JWTs.
"""

import pytest
import httpx
import jwt
import os
from datetime import datetime, timedelta
from typing import Dict, Any


class TestAPIKeyExchange:
    """Test API key to JWT exchange functionality."""
    
    @pytest.mark.asyncio
    async def test_exchange_valid_api_key(self):
        """Test successful exchange of a valid API key for JWT."""
        auth_url = "http://auth-service:8000"
        
        # Use a test API key from environment or default
        test_api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY", "test-key-123")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": test_api_key}
            )
            
            # Should get a 200 OK with JWT token
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            
            # Verify OAuth2-compatible response structure
            assert "access_token" in data
            assert "token_type" in data
            assert "expires_in" in data
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 900  # 15 minutes
            
            # Verify user info included
            assert "user" in data
            assert "id" in data["user"]
            assert "email" in data["user"]
            
            # Decode and verify JWT structure (without signature verification for test)
            jwt_token = data["access_token"]
            decoded = jwt.decode(jwt_token, options={"verify_signature": False})
            
            # Verify JWT claims match Supabase format
            assert "sub" in decoded  # User ID in sub claim
            assert "aud" in decoded
            assert "exp" in decoded
            assert "iat" in decoded
            assert "email" in decoded
            assert decoded["aud"] == "authenticated"
            assert decoded["role"] == "authenticated"
            
            # Verify user_id is included for backward compatibility
            assert "user_id" in decoded
            assert decoded["user_id"] == decoded["sub"]
            
            # Verify metadata
            assert "user_metadata" in decoded
            assert decoded["user_metadata"]["auth_source"] == "api_key_exchange"
    
    @pytest.mark.asyncio
    async def test_exchange_invalid_api_key(self):
        """Test exchange with an invalid API key returns 401."""
        auth_url = "http://auth-service:8000"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": "invalid-key-12345"}
            )
            
            # Should get a 401 Unauthorized
            assert response.status_code == 401
            data = response.json()
            assert "detail" in data
            assert data["detail"] == "Invalid API key"
    
    @pytest.mark.asyncio
    async def test_exchange_missing_api_key(self):
        """Test exchange without API key returns 422."""
        auth_url = "http://auth-service:8000"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{auth_url}/auth/api-key-login")
            
            # Should get a 422 Unprocessable Entity (missing required header)
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_jwt_can_be_used_for_chat(self):
        """Test that the exchanged JWT can be used to access chat endpoints."""
        auth_url = "http://auth-service:8000"
        chat_url = "http://chat-service:8000"
        
        # First, exchange API key for JWT
        test_api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY", "test-key-123")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Exchange API key for JWT
            exchange_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": test_api_key}
            )
            
            assert exchange_response.status_code == 200
            jwt_token = exchange_response.json()["access_token"]
            
            # Use JWT to create a chat
            chat_response = await client.post(
                f"{chat_url}/chat/",  # Simple chat endpoint with trailing slash
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "message": "Hello from JWT test",  # Simple message format
                    "model": "claude-3-sonnet-20240229",
                    "max_tokens": 10
                }
            )
            
            # Should successfully create chat with JWT auth
            if chat_response.status_code != 200:
                print(f"Chat response status: {chat_response.status_code}")
                print(f"Chat response body: {chat_response.text}")
            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            # The /chat/ endpoint returns a simple response format
            assert "response" in chat_data
            assert "provider" in chat_data
            assert "model" in chat_data
            # Most importantly, it worked without authentication errors!
    
    @pytest.mark.asyncio
    async def test_jwt_expiration_time(self):
        """Test that JWT has correct expiration time (15 minutes)."""
        auth_url = "http://auth-service:8000"
        test_api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY", "test-key-123")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": test_api_key}
            )
            
            assert response.status_code == 200
            jwt_token = response.json()["access_token"]
            
            # Decode JWT without verification
            decoded = jwt.decode(jwt_token, options={"verify_signature": False})
            
            # Check expiration
            exp_timestamp = decoded["exp"]
            iat_timestamp = decoded["iat"]
            
            # Should be 15 minutes (900 seconds)
            assert exp_timestamp - iat_timestamp == 900
            
            # Verify it's approximately 15 minutes from now
            now = datetime.utcnow()
            exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
            time_diff = exp_datetime - now
            
            # Should be between 14 and 16 minutes (allowing for test execution time)
            assert timedelta(minutes=14) < time_diff < timedelta(minutes=16)


class TestAPIKeyExchangeWithSupabase:
    """Test API key exchange with Supabase backend."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("AUTH_BACKEND") != "supabase",
        reason="Only run when AUTH_BACKEND=supabase"
    )
    async def test_exchange_with_supabase_backend(self):
        """Test API key exchange when using Supabase backend."""
        auth_url = "http://auth-service:8000"
        
        # This would use a real API key from Supabase
        # For now, we'll skip if no valid key is available
        test_api_key = os.getenv("TEST_SUPABASE_API_KEY") or os.getenv("API_KEY") or os.getenv("TEST_API_KEY", "test-key-123")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": test_api_key}
            )
            
            if response.status_code == 401:
                pytest.skip("No valid Supabase API key available for testing")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify the JWT contains Supabase URL as issuer
            jwt_token = data["access_token"]
            decoded = jwt.decode(jwt_token, options={"verify_signature": False})
            
            assert "iss" in decoded
            assert "supabase" in decoded["iss"] or decoded["iss"].startswith("https://")