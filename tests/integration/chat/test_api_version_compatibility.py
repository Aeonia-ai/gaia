"""
Tests for API version backward compatibility.
Ensures that v0.3 doesn't break existing v0.2 and v1 functionality.
This is a legitimate cross-version test file.
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
    async def test_v02_still_works_with_v03(self, gateway_url, headers):
        """Test that v0.2 API still works alongside v0.3."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # v0.2 should still work with old format
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "Hello from v0.2"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # v0.2 format includes provider details
            assert "response" in data
            assert "provider" in data
            assert "model" in data

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
    async def test_all_versions_with_same_message(self, gateway_url, headers):
        """Test that all API versions handle the same message."""
        test_message = "What is 2+2?"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test v0.2
            v02_response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": test_message}
            )
            assert v02_response.status_code == 200
            v02_data = v02_response.json()
            assert "response" in v02_data
            assert "4" in v02_data["response"] or "four" in v02_data["response"].lower()
            
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
            assert "provider" in v02_data  # v0.2 exposes internals
            assert "provider" not in v03_data  # v0.3 hides internals
            assert len(v03_data) == 2  # v0.3 only has response and conversation_id

    @pytest.mark.asyncio
    async def test_v03_vs_v02_directive_difference(self, gateway_url, headers):
        """Test that v0.3 has directives while v0.2 does not."""
        import re
        
        def extract_directives(response_text: str) -> list:
            """Extract JSON-RPC directives from response text."""
            directive_pattern = r'\{"m":"[^"]+","p":\{[^}]*\}\}'
            matches = re.findall(directive_pattern, response_text)
            directives = []
            for match in matches:
                try:
                    directive = json.loads(match)
                    directives.append(directive)
                except json.JSONDecodeError:
                    continue
            return directives
        
        message = "Guide me through a calming meditation"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test v0.2 (should not have directives)
            v02_response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": message, "stream": False}
            )
            
            # Test v0.3 (should have directives)
            v03_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={"message": message, "stream": False}
            )
            
            assert v02_response.status_code == 200
            assert v03_response.status_code == 200
            
            v02_data = v02_response.json()
            v03_data = v03_response.json()
            
            # Extract directives from both responses
            v02_directives = extract_directives(v02_data.get("response", ""))
            v03_directives = extract_directives(v03_data.get("response", ""))
            
            # v0.2 should have no directives (or very few)
            # v0.3 should have directives
            assert len(v03_directives) > len(v02_directives), (
                f"v0.3 should have more directives than v0.2. "
                f"v0.2: {len(v02_directives)}, v0.3: {len(v03_directives)}"
            )