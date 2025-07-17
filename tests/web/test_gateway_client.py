"""Tests for gateway client"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
from app.services.web.utils.gateway_client import GaiaAPIClient


pytestmark = pytest.mark.unit


@pytest.fixture
def gateway_client():
    """Create gateway client instance"""
    return GaiaAPIClient("http://test-gateway:8000")


class TestGaiaAPIClient:
    """Test gateway API client"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, gateway_client):
        """Test successful login"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "session": {"access_token": "jwt-token"},
            "user": {"id": "123", "email": "test@example.com"}
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(gateway_client.client, 'post', return_value=mock_response) as mock_post:
            result = await gateway_client.login("test@example.com", "password")
            
            assert result["session"]["access_token"] == "jwt-token"
            mock_post.assert_called_once_with(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "password"}
            )
    
    @pytest.mark.asyncio
    async def test_login_failure(self, gateway_client):
        """Test login with invalid credentials"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"detail":"Invalid credentials"}'
        mock_response.json.return_value = {"detail": "Invalid credentials"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", 
            request=Mock(), 
            response=mock_response
        )
        
        with patch.object(gateway_client.client, 'post', return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError):
                await gateway_client.login("test@example.com", "wrongpass")
    
    @pytest.mark.asyncio
    async def test_register_success(self, gateway_client):
        """Test successful registration"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "session": {"access_token": "new-jwt-token"},
            "user": {"id": "456", "email": "new@example.com"}
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(gateway_client.client, 'post', return_value=mock_response) as mock_post:
            result = await gateway_client.register("new@example.com", "password123")
            
            assert result["user"]["email"] == "new@example.com"
            mock_post.assert_called_once_with(
                "/api/v1/auth/register",
                json={
                    "email": "new@example.com",
                    "password": "password123",
                    "username": "new"
                }
            )
    
    @pytest.mark.asyncio
    async def test_register_with_error_detail(self, gateway_client):
        """Test registration error with detail extraction"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"detail":"Service error: {\\"detail\\":\\"Please enter a valid email address\\"}"}'
        mock_response.json.return_value = {
            "detail": 'Service error: {"detail":"Please enter a valid email address"}'
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request",
            request=Mock(),
            response=mock_response
        )
        
        with patch.object(gateway_client.client, 'post', return_value=mock_response):
            with pytest.raises(Exception) as exc_info:
                await gateway_client.register("bad@email", "password123")
            
            # Check that the error detail was extracted
            assert "Service error:" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_jwt(self, gateway_client):
        """Test chat completion with JWT auth"""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Hello!"}
        mock_response.raise_for_status = Mock()
        
        with patch.object(gateway_client.client, 'post', return_value=mock_response) as mock_post:
            result = await gateway_client.chat_completion(
                [{"role": "user", "content": "Hi"}],
                "real-jwt-token"
            )
            
            assert result["response"] == "Hello!"
            # Should use v1 endpoint with JWT
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/api/v1/chat/completions"
            assert call_args[1]["headers"]["Authorization"] == "Bearer real-jwt-token"
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_dev_token(self, gateway_client):
        """Test chat completion with dev token (API key fallback)"""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Hello!"}
        mock_response.raise_for_status = Mock()
        
        with patch.object(gateway_client.client, 'post', return_value=mock_response) as mock_post:
            result = await gateway_client.chat_completion(
                [{"role": "user", "content": "Hi"}],
                "dev-token-12345"
            )
            
            assert result["response"] == "Hello!"
            # Should use v0.2 endpoint with API key
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/api/v0.2/chat"
            assert "X-API-Key" in call_args[1]["headers"]
    
    @pytest.mark.asyncio
    async def test_health_check(self, gateway_client):
        """Test health check"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status = Mock()
        
        with patch.object(gateway_client.client, 'get', return_value=mock_response):
            result = await gateway_client.health_check()
            
            assert result["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client works as context manager"""
        async with GaiaAPIClient() as client:
            assert isinstance(client, GaiaAPIClient)
            assert client.client is not None