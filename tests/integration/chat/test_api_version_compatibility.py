"""
Tests for API version compatibility between v1 and v0.3.
Ensures that both API versions work correctly alongside each other.
Note: v0.2 API has been removed from the platform.
"""

import pytest
import httpx
import json


@pytest.fixture
def gateway_url():
    """Gateway service URL for testing."""
    return "http://gateway:8000"


@pytest.fixture
def api_key():
    """Test API key."""
    import os
    return os.getenv("API_KEY", "test-api-key-12345")


@pytest.fixture
def headers(api_key):
    """Standard headers for API requests."""
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }


class TestAPIVersionCompatibility:
    """Test that all API versions work alongside each other."""

    @pytest.mark.asyncio
    async def test_v1_still_works_with_v03(self, gateway_url, headers):
        """Test that v1 API still works alongside v0.3."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # v1 should still work
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Hello from v1"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # v1 OpenAI-compatible format
            assert "choices" in data or "response" in data

    @pytest.mark.asyncio
    async def test_v03_clean_interface(self, gateway_url, headers):
        """Test that v0.3 provides clean interface."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={"message": "Hello from v0.3"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # v0.3 clean format - no internals
            assert "response" in data
            assert "conversation_id" in data
            assert "provider" not in data
            assert "model" not in data

    @pytest.mark.asyncio
    async def test_both_versions_with_same_message(self, gateway_url, headers):
        """Test that v1 and v0.3 API versions handle the same message."""
        test_message = "What is 2+2?"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test v1
            v1_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": test_message}
            )
            assert v1_response.status_code == 200
            v1_data = v1_response.json()
            # Extract response based on format
            if "choices" in v1_data:
                v1_answer = v1_data["choices"][0]["message"]["content"]
            else:
                v1_answer = v1_data.get("response", "")
            assert "4" in v1_answer or "four" in v1_answer.lower()
            
            # Test v0.3
            v03_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={"message": test_message}
            )
            assert v03_response.status_code == 200
            v03_data = v03_response.json()
            assert "response" in v03_data
            assert "4" in v03_data["response"] or "four" in v03_data["response"].lower()
            
            # Verify format differences
            assert "provider" not in v03_data  # v0.3 hides internals
            assert len(v03_data) == 2  # v0.3 only has response and conversation_id

