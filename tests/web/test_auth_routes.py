"""Tests for web service authentication routes

NOTE: Fixed async/sync patterns and mock import paths.
See tests/web/README_TEST_FIXES.md for detailed documentation.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fasthtml.core import FastHTML
from starlette.testclient import TestClient
from app.services.web.routes.auth import setup_routes
from app.services.web.utils.gateway_client import GaiaAPIClient


pytestmark = pytest.mark.unit


# Remove local fixtures - use the ones from conftest.py that provide the full app


class TestAuthRoutes:
    """Test authentication routes"""
    
    def test_dev_login_success(self, client):
        """Test dev login with correct credentials"""
        with patch('app.services.web.config.settings.debug', True):
            response = client.post("/auth/login", data={
                "email": "dev@gaia.local",
                "password": "testtest"
            }, follow_redirects=False)
            
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
                assert "Login failed. Please try again." in response.text
    
    def test_real_login_success(self, client, mock_gateway_client):
        """Test real login via gateway"""
        # Mock successful login response
        mock_gateway_client.login.return_value = {
            "session": {
                "access_token": "test-jwt-token",
                "refresh_token": "test-refresh-token"
            },
            "user": {
                "id": "user-123",
                "email": "test@example.com",
                "email_confirmed_at": "2024-01-01T00:00:00Z"
            }
        }
        
        with patch('app.services.web.routes.auth.GaiaAPIClient') as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_gateway_client
            
            response = client.post("/auth/login", data={
                "email": "test@example.com",
                "password": "password123"
            }, follow_redirects=False)
            
            assert response.status_code == 303
            assert response.headers["location"] == "/chat"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.login.side_effect = Exception("Invalid credentials")
            
            response = client.post("/auth/login", data={
                "email": "test@example.com",
                "password": "wrongpass"
            })
            
            assert response.status_code == 200
            assert "Login failed. Please try again." in response.text
    
    def test_register_success(self, client, mock_gateway_client):
        """Test successful registration"""
        # Mock successful registration response
        mock_gateway_client.register.return_value = {
            "user": {
                "id": "new-user-123",
                "email": "newuser@example.com",
                "email_confirmed_at": None  # Needs verification
            }
        }
        
        with patch('app.services.web.routes.auth.GaiaAPIClient') as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_gateway_client
            
            response = client.post("/auth/register", data={
                "email": "newuser@example.com",
                "password": "password123"
            })
            
            assert response.status_code == 200
            # Should show email verification notice instead of "Registration successful"
            assert "check your email" in response.text.lower()
            assert "newuser@example.com" in response.text
    
    def test_register_invalid_email(self, client):
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
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.register.side_effect = Exception('Service error: {"detail":"Password must be at least 6 characters long"}')
            
            response = client.post("/auth/register", data={
                "email": "test@example.com",
                "password": "123"
            })
            
            assert response.status_code == 200
            assert "Password should be at least 6 characters" in response.text
    
    def test_logout(self, client):
        """Test logout clears session"""
        # First login
        with patch('app.services.web.config.settings.debug', True):
            client.post("/auth/login", data={
                "email": "dev@gaia.local",
                "password": "test"
            })
        
        # Then logout
        response = client.get("/logout", follow_redirects=False)
        
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
        public_routes = ["/login", "/register", "/health"]
        
        for route in public_routes:
            response = client.get(route, follow_redirects=False)
            # Should not redirect to login
            assert not (response.status_code == 303 and response.headers.get("location") == "/login"), f"Route {route} incorrectly redirected to login"
    
    def test_home_page_shows_landing_page_todo(self, client):
        """Test that home page shows a landing page for unauthenticated users"""
        # TODO: Currently / redirects to /login, but should show a home page
        # This test documents the intended behavior
        response = client.get("/", follow_redirects=False)
        
        # Current behavior: redirects to login
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        
        # TODO: Future behavior should be:
        # assert response.status_code == 200
        # assert "Welcome to Gaia" in response.text or similar home page content
        # assert "Sign In" in response.text  # Login button
        # assert "Sign Up" in response.text  # Register button