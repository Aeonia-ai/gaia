"""Tests for web service authentication routes"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fasthtml.core import FastHTML
from starlette.testclient import TestClient
from app.services.web.routes.auth import setup_routes
from app.services.web.utils.gateway_client import GaiaAPIClient


pytestmark = pytest.mark.unit


@pytest.fixture
def test_app():
    """Create test FastHTML app"""
    app = FastHTML()
    setup_routes(app)
    return app


@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


class TestAuthRoutes:
    """Test authentication routes"""
    
    def test_dev_login_success(self, client):
        """Test dev login with correct credentials"""
        with patch('app.services.web.config.settings.debug', True):
            response = client.post("/auth/login", data={
                "email": "dev@gaia.local",
                "password": "testtest"
            })
            
            assert response.status_code == 303  # Redirect
            assert response.headers["location"] == "/chat"
    
    def test_dev_login_wrong_password(self, client):
        """Test dev login with wrong password"""
        with patch('app.services.web.config.settings.debug', True):
            with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
                # Mock the client to raise an exception
                mock_instance = mock_client.return_value.__aenter__.return_value
                mock_instance.login.side_effect = Exception("Invalid credentials")
                
                response = client.post("/auth/login", data={
                    "email": "dev@gaia.local",
                    "password": "wrong"
                })
                
                assert response.status_code == 200
                assert "Invalid email or password" in response.text
    
    @pytest.mark.asyncio
    async def test_real_login_success(self, client):
        """Test real login via gateway"""
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            # Mock successful login response
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.login.return_value = {
                "session": {
                    "access_token": "test-jwt-token",
                    "refresh_token": "test-refresh-token"
                },
                "user": {
                    "id": "user-123",
                    "email": "test@example.com"
                }
            }
            
            response = client.post("/auth/login", data={
                "email": "test@example.com",
                "password": "password123"
            })
            
            assert response.status_code == 303
            assert response.headers["location"] == "/chat"
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.login.side_effect = Exception("Invalid credentials")
            
            response = client.post("/auth/login", data={
                "email": "test@example.com",
                "password": "wrongpass"
            })
            
            assert response.status_code == 200
            assert "Invalid email or password" in response.text
    
    @pytest.mark.asyncio
    async def test_register_success(self, client):
        """Test successful registration"""
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.register.return_value = {
                "session": {
                    "access_token": "new-jwt-token",
                    "refresh_token": "new-refresh-token"
                },
                "user": {
                    "id": "new-user-123",
                    "email": "newuser@example.com"
                }
            }
            
            response = client.post("/auth/register", data={
                "email": "newuser@example.com",
                "password": "password123"
            })
            
            assert response.status_code == 200
            assert "Registration successful" in response.text
            assert "setTimeout" in response.text  # Redirect script
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.register.side_effect = Exception('Service error: {"detail":"Please enter a valid email address"}')
            
            response = client.post("/auth/register", data={
                "email": "invalid@test.com",
                "password": "password123"
            })
            
            assert response.status_code == 200
            assert "Please enter a valid email address" in response.text
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, client):
        """Test registration with weak password"""
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.register.side_effect = Exception('Service error: {"detail":"Password must be at least 6 characters long"}')
            
            response = client.post("/auth/register", data={
                "email": "test@example.com",
                "password": "123"
            })
            
            assert response.status_code == 200
            assert "Password must be at least 6 characters" in response.text
    
    def test_logout(self, client):
        """Test logout clears session"""
        # First login
        with patch('app.services.web.config.settings.debug', True):
            client.post("/auth/login", data={
                "email": "dev@gaia.local",
                "password": "test"
            })
        
        # Then logout
        response = client.get("/logout")
        
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
    
    def test_auth_middleware_redirects_unauthenticated(self, client):
        """Test middleware redirects unauthenticated requests"""
        # Try to access protected route without login
        response = client.get("/chat", follow_redirects=False)
        
        # Should redirect to login
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
    
    def test_auth_middleware_allows_public_routes(self, client):
        """Test middleware allows public routes"""
        # These should work without authentication
        public_routes = ["/", "/login", "/register", "/health"]
        
        for route in public_routes:
            response = client.get(route, follow_redirects=False)
            # Should not redirect to login
            assert response.status_code != 303 or response.headers.get("location") != "/login"