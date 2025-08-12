"""
Test v0.3 directive generation functionality.
Tests that v0.3 endpoints generate JSON-RPC directives in responses.
"""

import pytest
import httpx
import json
import re
import os
from typing import Dict, Any, Optional


class TestV03DirectiveGeneration:
    """Test v0.3 directive generation in responses."""
    
    @pytest.fixture
    def gateway_url(self) -> str:
        """Gateway URL for tests."""
        return "http://gateway:8000"
    
    @pytest.fixture
    def api_key(self) -> str:
        """API key for testing."""
        return os.getenv("API_KEY") or os.getenv("TEST_API_KEY", "test-key-123")
    
    def extract_directives(self, response_text: str) -> list:
        """Extract JSON-RPC directives from response text."""
        # Pattern to match JSON-RPC directives: {"m":"method","p":{...}}
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
    
    @pytest.mark.asyncio
    async def test_v03_generates_directives_for_meditation(self, gateway_url, api_key):
        """Test that v0.3 generates directives for meditation requests."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Guide me through a 30-second breathing meditation",
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have response
            assert "response" in data
            response_text = data["response"]
            assert isinstance(response_text, str)
            assert len(response_text) > 0
            
            # Extract directives
            directives = self.extract_directives(response_text)
            
            # Should contain at least one directive
            assert len(directives) > 0, f"No directives found in response: {response_text[:200]}..."
            
            # Look for meditation or pause directives
            directive_methods = [d.get("m") for d in directives]
            expected_methods = ["meditation", "pause", "effect"]
            
            has_expected = any(method in directive_methods for method in expected_methods)
            assert has_expected, f"Expected directive methods {expected_methods}, got: {directive_methods}"
            
            print(f"✅ Found {len(directives)} directives: {directive_methods}")
    
    @pytest.mark.asyncio
    async def test_v03_generates_pause_directives(self, gateway_url, api_key):
        """Test that v0.3 generates pause directives for timing."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Tell me a story with dramatic pauses",
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            response_text = data["response"]
            
            # Extract directives
            directives = self.extract_directives(response_text)
            
            # Should contain directives (may be pause, effect, or other dramatic elements)
            assert len(directives) > 0, f"No directives found in dramatic story response"
            
            # Validate directive structure
            for directive in directives:
                assert "m" in directive, f"Directive missing method: {directive}"
                assert isinstance(directive["m"], str), f"Method should be string: {directive}"
                
                if "p" in directive:
                    assert isinstance(directive["p"], dict), f"Parameters should be dict: {directive}"
    
    @pytest.mark.asyncio
    async def test_v03_directives_have_valid_json_format(self, gateway_url, api_key):
        """Test that generated directives are valid JSON-RPC format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Create a magical moment with sparkles and effects",
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            response_text = data["response"]
            
            # Extract directives
            directives = self.extract_directives(response_text)
            
            # Should contain directives for magical effects
            assert len(directives) > 0, "No directives found for magical effects request"
            
            # Validate each directive follows JSON-RPC format
            for directive in directives:
                # Required: method field
                assert "m" in directive, f"Missing method 'm' in directive: {directive}"
                assert isinstance(directive["m"], str), f"Method must be string: {directive}"
                assert len(directive["m"]) > 0, f"Method cannot be empty: {directive}"
                
                # Optional: parameters field
                if "p" in directive:
                    assert isinstance(directive["p"], dict), f"Parameters must be dict: {directive}"
                
                # Check for valid method names
                valid_methods = ["pause", "effect", "animation", "meditation", "whisper", "emphasis"]
                assert directive["m"] in valid_methods, f"Unknown method '{directive['m']}' in directive: {directive}"
    
    @pytest.mark.asyncio
    async def test_v03_streaming_includes_directives(self, gateway_url, api_key):
        """Test that v0.3 streaming responses include directives."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Guide me through meditation with pauses",
                    "stream": True
                }
            )
            
            assert response.status_code == 200
            
            # Collect all content from streaming response
            full_response = ""
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    
                    if data_str and data_str != "[DONE]":
                        try:
                            chunk_data = json.loads(data_str)
                            if chunk_data.get("type") == "content":
                                full_response += chunk_data.get("content", "")
                        except json.JSONDecodeError:
                            continue
            
            # Extract directives from full streaming response
            directives = self.extract_directives(full_response)
            
            # Should contain directives even in streaming mode
            assert len(directives) > 0, f"No directives in streaming response: {full_response[:200]}..."
            
            print(f"✅ Streaming response contained {len(directives)} directives")
    
    @pytest.mark.asyncio
    async def test_v03_vs_v02_directive_difference(self, gateway_url, api_key):
        """Test that v0.3 has directives while v0.2 does not."""
        message = "Guide me through a calming meditation"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test v0.2 (should not have directives)
            v02_response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers={"X-API-Key": api_key},
                json={"message": message, "stream": False}
            )
            
            # Test v0.3 (should have directives)
            v03_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={"message": message, "stream": False}
            )
            
            assert v02_response.status_code == 200
            assert v03_response.status_code == 200
            
            v02_data = v02_response.json()
            v03_data = v03_response.json()
            
            # Extract directives from both responses
            v02_directives = self.extract_directives(v02_data.get("response", ""))
            v03_directives = self.extract_directives(v03_data.get("response", ""))
            
            # v0.2 should have no directives (or very few)
            # v0.3 should have directives
            assert len(v03_directives) > len(v02_directives), (
                f"v0.3 should have more directives than v0.2. "
                f"v0.2: {len(v02_directives)}, v0.3: {len(v03_directives)}"
            )
            
            print(f"✅ v0.2 directives: {len(v02_directives)}, v0.3 directives: {len(v03_directives)}")