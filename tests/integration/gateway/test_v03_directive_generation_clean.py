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
        # Pattern to match minimal JSON-RPC directives: {"m":"method","p":{...}}
        # Also accepts optional "s" field: {"m":"method","s":"subcategory","p":{...}}
        directive_pattern = r'\{"m":"[^"]+","p":\{[^}]*\}\}|\{"m":"[^"]+","s":"[^"]+","p":\{[^}]*\}\}'
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
            
            # Should contain pause directives (only supported method currently)
            directive_methods = [d.get("m") for d in directives]
            
            assert "pause" in directive_methods, f"Expected 'pause' directive, got: {directive_methods}"
            
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
                    "message": "Guide me through a breathing exercise with timed pauses",
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            response_text = data["response"]
            
            # Extract directives
            directives = self.extract_directives(response_text)
            
            # Should contain directives for breathing exercise with pauses
            assert len(directives) > 0, "No directives found for breathing exercise request"
            
            # Validate each directive follows minimal JSON-RPC format
            for directive in directives:
                # Required: method field
                assert "m" in directive, f"Missing method 'm' in directive: {directive}"
                assert isinstance(directive["m"], str), f"Method must be string: {directive}"
                assert len(directive["m"]) > 0, f"Method cannot be empty: {directive}"
                
                # Should NOT have category field (deprecated)
                assert "c" not in directive, f"Directive should not have 'c' field: {directive}"
                
                # Optional: subcategory field
                if "s" in directive:
                    assert isinstance(directive["s"], str), f"Subcategory must be string: {directive}"
                    assert len(directive["s"]) > 0, f"Subcategory cannot be empty: {directive}"
                
                # Required: parameters field for pause
                assert "p" in directive, f"Missing parameters 'p' in directive: {directive}"
                assert isinstance(directive["p"], dict), f"Parameters must be dict: {directive}"
                
                # Check for pause method and secs parameter
                assert directive["m"] == "pause", f"Only 'pause' method is currently supported, got: {directive['m']}"
                assert "secs" in directive["p"], f"Pause directive must have 'secs' parameter: {directive}"
                assert isinstance(directive["p"]["secs"], (int, float)), f"'secs' must be a number: {directive}"
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Directives not implemented in streaming responses")
    async def test_v03_streaming_includes_directives(self, gateway_url, api_key):
        """Test that v0.3 streaming responses include directives."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Make streaming request
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Guide me through a breathing exercise with pauses",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                
                # Collect all streaming chunks
                chunks = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str and data_str != "[DONE]":
                            try:
                                chunk_data = json.loads(data_str)
                                chunks.append(chunk_data)
                            except json.JSONDecodeError:
                                continue
                
                # Combine all response chunks
                full_response = ""
                for chunk in chunks:
                    if "response" in chunk:
                        full_response += chunk["response"]
                
                # Extract directives from the full response
                directives = self.extract_directives(full_response)
                
                # Should contain directives even in streaming mode
                assert len(directives) > 0, f"No directives in streaming response: {full_response[:200]}..."
                
                print(f"✅ Streaming response contained {len(directives)} directives")