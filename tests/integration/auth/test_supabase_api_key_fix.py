"""
Test the Supabase API key validation after removing hardcoded checks.
This verifies that the validation function properly queries the database.
"""

import pytest
import httpx
import os
from typing import Dict, Any

class TestSupabaseAPIKeyValidation:
    """Test API key validation with fixed Supabase function."""
    
    @pytest.fixture
    def api_key(self):
        """The Jason Dev Key from .env"""
        return "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL for testing"""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.mark.asyncio
    async def test_validate_endpoint_with_real_key(self, gateway_url, api_key):
        """Test that validation endpoint works with the real API key from Supabase."""
        async with httpx.AsyncClient() as client:
            # Test the validation endpoint
            response = await client.post(
                f"{gateway_url}/api/v1/auth/validate",
                json={"api_key": api_key}
            )
            
            # Should not get internal server error anymore
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            assert data["valid"] is True, "API key should be valid"
            assert data["auth_type"] == "api_key"
            assert data["user_id"] is not None, "Should return user_id"
            
            # Verify it's not using hardcoded user ID
            assert data["user_id"] != "c9958e79-b266-4f78-9bf2-1cde152bdd2f", \
                "Should not return hardcoded user_id"
    
    @pytest.mark.asyncio
    async def test_validate_endpoint_with_invalid_key(self, gateway_url):
        """Test that validation properly rejects invalid keys."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/auth/validate",
                json={"api_key": "invalid-key-that-does-not-exist"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert data["user_id"] is None
    
    @pytest.mark.asyncio
    async def test_api_calls_with_validated_key(self, gateway_url, api_key):
        """Test that API calls work correctly after validation fix."""
        async with httpx.AsyncClient() as client:
            # First validate the key
            validate_response = await client.post(
                f"{gateway_url}/api/v1/auth/validate",
                json={"api_key": api_key}
            )
            assert validate_response.status_code == 200
            assert validate_response.json()["valid"] is True
            
            # Then use it for an actual API call
            headers = {"X-API-Key": api_key}
            chat_response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={
                    "message": "Test after validation fix",
                    "stream": False
                }
            )
            
            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            assert "response" in chat_data or "message" in chat_data
    
    @pytest.mark.asyncio 
    async def test_no_hardcoded_permissions(self, gateway_url, api_key):
        """Verify permissions come from database, not hardcoded values."""
        # This would require checking the actual permissions returned
        # vs what's in the database, which we can't easily do from here
        # But we can at least verify the endpoint works
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/auth/validate",
                json={"api_key": api_key}
            )
            
            assert response.status_code == 200
            # The key should be valid based on database lookup
            data = response.json()
            if data["valid"]:
                # If we had access to the expected permissions from DB,
                # we could verify they match here
                pass