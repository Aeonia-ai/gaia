"""Integration tests for persona API endpoints"""
import pytest
import httpx
from tests.fixtures.test_auth import JWTTestAuth

BASE_URL = "http://chat-service:8000"


class TestPersonasAPI:
    """Test persona API endpoints"""
    
    @pytest.fixture
    def jwt_auth(self):
        """Create JWT auth helper"""
        return JWTTestAuth()
    
    @pytest.mark.asyncio
    async def test_list_personas_requires_auth(self):
        """Test that listing personas requires authentication"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/personas/")
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_personas_with_auth(self, jwt_auth):
        """Test listing personas with valid authentication"""
        headers = jwt_auth.create_auth_headers(user_id="test-user-123")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/personas/", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "personas" in data
            assert "total" in data
            # Should have at least the default Mu persona
            assert data["total"] >= 1
            assert any(p["name"] == "Mu" for p in data["personas"])
    
    @pytest.mark.asyncio
    async def test_get_current_persona_defaults_to_mu(self, jwt_auth):
        """Test that users get Mu as default persona"""
        headers = jwt_auth.create_auth_headers(user_id="new-user-456")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/personas/current", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["persona"]["name"] == "Mu"
            assert "cheerful robot companion" in data["persona"]["description"].lower()
    
    @pytest.mark.asyncio
    async def test_set_user_persona(self, jwt_auth):
        """Test setting a user's active persona"""
        headers = jwt_auth.create_auth_headers(user_id="test-user-789")
        
        async with httpx.AsyncClient() as client:
            # First get list of personas
            response = await client.get(f"{BASE_URL}/personas/", headers=headers)
            personas = response.json()["personas"]
            mu_persona = next(p for p in personas if p["name"] == "Mu")
            
            # Set Mu as active persona
            response = await client.post(
                f"{BASE_URL}/personas/set",
                headers=headers,
                json={"persona_id": mu_persona["id"]}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["persona_id"] == mu_persona["id"]
            
            # Verify it's now the current persona
            response = await client.get(f"{BASE_URL}/personas/current", headers=headers)
            assert response.json()["persona"]["id"] == mu_persona["id"]
    
    @pytest.mark.asyncio
    async def test_get_specific_persona(self, jwt_auth):
        """Test getting a specific persona by ID"""
        headers = jwt_auth.create_auth_headers(user_id="test-user-321")
        
        async with httpx.AsyncClient() as client:
            # Get list to find Mu's ID
            response = await client.get(f"{BASE_URL}/personas/", headers=headers)
            mu_persona = next(p for p in response.json()["personas"] if p["name"] == "Mu")
            
            # Get specific persona
            response = await client.get(f"{BASE_URL}/personas/{mu_persona['id']}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["persona"]["id"] == mu_persona["id"]
            assert data["persona"]["name"] == "Mu"
    
    @pytest.mark.asyncio
    async def test_persona_affects_chat_response(self, jwt_auth):
        """Test that persona selection affects chat responses"""
        headers = jwt_auth.create_auth_headers(user_id="test-user-chat")
        
        async with httpx.AsyncClient() as client:
            # Send a chat message (should use default Mu persona)
            response = await client.post(
                f"{BASE_URL}/v1/chat",
                headers=headers,
                json={
                    "message": "Hello, who are you?",
                    "response_format": "text"
                }
            )
            assert response.status_code == 200
            response_text = response.json()["response"]
            
            # Should contain Mu-like personality indicators
            # (robotic expressions, cheerful tone, etc.)
            assert any(indicator in response_text.lower() for indicator in [
                "beep", "boop", "mu", "robot", "companion"
            ])