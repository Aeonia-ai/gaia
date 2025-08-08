"""Integration tests for persona API endpoints"""
import pytest
import httpx
from tests.fixtures.shared_test_user import shared_test_user

BASE_URL = "http://gateway:8000"


@pytest.mark.skip(reason="Persona endpoints not exposed through gateway - needs architecture decision")
class TestPersonasAPI:
    """Test persona API endpoints"""
    
    @pytest.fixture
    async def auth_headers(self, shared_test_user):
        """Get auth headers using real JWT from shared test user"""
        # Login through gateway to get real JWT
        gateway_url = "http://gateway:8000"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/auth/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            assert response.status_code == 200
            jwt_token = response.json()["session"]["access_token"]
            return {"Authorization": f"Bearer {jwt_token}"}
    
    @pytest.mark.asyncio
    async def test_list_personas_requires_auth(self):
        """Test that listing personas requires authentication"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/")
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_personas_with_auth(self, auth_headers):
        """Test listing personas with valid authentication"""
        headers = auth_headers
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "personas" in data
            assert "total" in data
            # Should have at least the default Mu persona
            assert data["total"] >= 1
            assert any(p["name"] == "Mu" for p in data["personas"])
    
    @pytest.mark.asyncio
    async def test_get_current_persona_defaults_to_mu(self, auth_headers):
        """Test that users get Mu as default persona"""
        headers = auth_headers
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/current", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["persona"]["name"] == "Mu"
            assert "cheerful robot companion" in data["persona"]["description"].lower()
    
    @pytest.mark.asyncio
    async def test_set_user_persona(self, auth_headers):
        """Test setting a user's active persona"""
        headers = auth_headers
        
        async with httpx.AsyncClient() as client:
            # First get list of personas
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/", headers=headers)
            personas = response.json()["personas"]
            mu_persona = next(p for p in personas if p["name"] == "Mu")
            
            # Set Mu as active persona
            response = await client.post(
                f"{BASE_URL}/api/v0.2/personas/set",
                headers=headers,
                json={"persona_id": mu_persona["id"]}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["persona_id"] == mu_persona["id"]
            
            # Verify it's now the current persona
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/current", headers=headers)
            assert response.json()["persona"]["id"] == mu_persona["id"]
    
    @pytest.mark.asyncio
    async def test_get_specific_persona(self, auth_headers):
        """Test getting a specific persona by ID"""
        headers = auth_headers
        
        async with httpx.AsyncClient() as client:
            # Get list to find Mu's ID
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/", headers=headers)
            mu_persona = next(p for p in response.json()["personas"] if p["name"] == "Mu")
            
            # Get specific persona
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/{mu_persona['id']}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["persona"]["id"] == mu_persona["id"]
            assert data["persona"]["name"] == "Mu"
    
    @pytest.mark.asyncio
    async def test_persona_affects_chat_response(self, auth_headers):
        """Test that persona selection affects chat responses"""
        headers = auth_headers
        
        async with httpx.AsyncClient() as client:
            # Send a chat message (should use default Mu persona)
            response = await client.post(
                f"{BASE_URL}/api/v1/chat",
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