"""
Comprehensive authentication flow tests for the web service.
Tests all auth endpoints to ensure they work correctly and remain public.
"""
import pytest
import httpx
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

pytestmark = pytest.mark.asyncio


class TestAuthenticationFlow:
    """Test suite for authentication workflows"""
    
    @pytest.fixture
    def mock_gateway_client(self):
        """Mock the GaiaAPIClient for testing"""
        with patch('app.services.web.routes.auth.GaiaAPIClient') as mock:
            client = AsyncMock()
            mock.return_value.__aenter__.return_value = client
            yield client
    
    async def test_login_endpoint_is_public(self, client):
        """Test that login endpoint doesn't require authentication"""
        # Login endpoint should be accessible without any auth headers
        response = await client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Should not return 401/403 (auth required)
        assert response.status_code != 401
        assert response.status_code != 403
    
    async def test_register_endpoint_is_public(self, client):
        """Test that register endpoint doesn't require authentication"""
        # Register endpoint should be accessible without any auth headers
        response = await client.post("/auth/register", data={
            "email": "newuser@example.com",
            "password": "password123"
        })
        
        # Should not return 401/403 (auth required)
        assert response.status_code != 401
        assert response.status_code != 403
    
    async def test_signup_alias_works(self, client):
        """Test that /auth/signup is an alias for /auth/register"""
        # Both endpoints should behave identically
        response = await client.post("/auth/signup", data={
            "email": "newuser@example.com",
            "password": "password123"
        })
        
        # Should not return 404
        assert response.status_code != 404
    
    async def test_successful_login_flow(self, client, mock_gateway_client):
        """Test successful login with verified email"""
        # Mock successful login response
        mock_gateway_client.login.return_value = {
            "session": {
                "access_token": "test-jwt-token",
                "refresh_token": "test-refresh-token"
            },
            "user": {
                "id": "user-123",
                "email": "test@example.com",
                "email_confirmed_at": "2024-01-01T00:00:00Z",
                "user_metadata": {"name": "Test User"}
            }
        }
        
        response = await client.post("/auth/login", 
            data={"email": "test@example.com", "password": "password123"},
            follow_redirects=False
        )
        
        # Should redirect to chat on success
        assert response.status_code == 303
        assert response.headers["location"] == "/chat"
        
        # Should have called gateway client
        mock_gateway_client.login.assert_called_once_with(
            "test@example.com", "password123"
        )
    
    async def test_login_with_unverified_email(self, client, mock_gateway_client):
        """Test login attempt with unverified email"""
        # Mock login response with unverified email
        mock_gateway_client.login.return_value = {
            "session": {"access_token": "test-jwt-token"},
            "user": {
                "id": "user-123",
                "email": "test@example.com",
                "email_confirmed_at": None  # Not verified
            }
        }
        
        response = await client.post("/auth/login",
            data={"email": "test@example.com", "password": "password123"}
        )
        
        # Should show verification notice, not redirect
        assert response.status_code == 200
        assert "verify your email" in response.text.lower()
        assert "resend verification" in response.text.lower()
    
    async def test_login_with_invalid_credentials(self, client, mock_gateway_client):
        """Test login with wrong credentials"""
        # Mock login failure
        mock_gateway_client.login.side_effect = httpx.HTTPStatusError(
            "Invalid credentials",
            request=MagicMock(),
            response=MagicMock(status_code=401, text="Invalid email or password")
        )
        
        response = await client.post("/auth/login",
            data={"email": "test@example.com", "password": "wrongpassword"}
        )
        
        # Should show error message
        assert response.status_code == 200
        assert "invalid email or password" in response.text.lower()
    
    async def test_successful_registration_flow(self, client, mock_gateway_client):
        """Test successful registration"""
        # Mock successful registration
        mock_gateway_client.register.return_value = {
            "user": {
                "id": "user-123",
                "email": "newuser@example.com",
                "email_confirmed_at": None  # Needs verification
            }
        }
        
        response = await client.post("/auth/register",
            headers={"HX-Request": "true"},  # HTMX request
            data={"email": "newuser@example.com", "password": "password123"}
        )
        
        # Should show verification notice
        assert response.status_code == 200
        assert "verify your email" in response.text.lower()
        assert "newuser@example.com" in response.text
    
    async def test_registration_with_existing_email(self, client, mock_gateway_client):
        """Test registration with already registered email"""
        # Mock registration failure
        error_response = MagicMock()
        error_response.status_code = 400
        error_response.text = '{"detail": "User already registered"}'
        error_response.json.return_value = {"detail": "User already registered"}
        
        mock_gateway_client.register.side_effect = httpx.HTTPStatusError(
            "Registration failed",
            request=MagicMock(),
            response=error_response
        )
        
        response = await client.post("/auth/register",
            data={"email": "existing@example.com", "password": "password123"}
        )
        
        # Should show appropriate error
        assert response.status_code == 200
        assert "already registered" in response.text.lower()
    
    async def test_registration_password_validation(self, client, mock_gateway_client):
        """Test registration with invalid password"""
        # Mock validation error
        error_response = MagicMock()
        error_response.text = '{"detail": "Password must be at least 6 characters"}'
        
        mock_gateway_client.register.side_effect = Exception(
            'Service error: {"detail": "Registration failed: Password must be at least 6 characters"}'
        )
        
        response = await client.post("/auth/register",
            data={"email": "test@example.com", "password": "short"}
        )
        
        # Should show password requirement
        assert response.status_code == 200
        assert "at least 6 characters" in response.text.lower()
    
    async def test_email_confirmation_flow(self, client, mock_gateway_client):
        """Test email confirmation link handling"""
        # Mock successful confirmation
        mock_gateway_client.confirm_email.return_value = {
            "success": True,
            "user": {"email": "test@example.com"}
        }
        
        response = await client.get("/auth/confirm",
            params={
                "token": "test-confirmation-token",
                "type": "signup",
                "email": "test@example.com"
            }
        )
        
        # Should show success message
        assert response.status_code == 200
        assert "email confirmed" in response.text.lower()
        assert "login" in response.text.lower()
    
    async def test_resend_verification_flow(self, client, mock_gateway_client):
        """Test resending verification email"""
        # Mock successful resend
        mock_gateway_client.resend_verification.return_value = {
            "success": True
        }
        
        response = await client.post("/auth/resend-verification",
            data={"email": "test@example.com"}
        )
        
        # Should show info message
        assert response.status_code == 200
        assert "verification email resent" in response.text.lower()
        assert "test@example.com" in response.text
    
    async def test_logout_clears_session(self, client):
        """Test logout functionality"""
        # First set up a session
        with client.session_transaction() as sess:
            sess["jwt_token"] = "test-token"
            sess["user"] = {"id": "123", "email": "test@example.com"}
        
        response = await client.get("/logout", follow_redirects=False)
        
        # Should redirect to login
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        
        # Session should be cleared
        with client.session_transaction() as sess:
            assert "jwt_token" not in sess
            assert "user" not in sess
    
    async def test_dev_login_only_in_debug_mode(self, client):
        """Test that dev login is only available in debug mode"""
        with patch('app.services.web.config.settings.debug', False):
            response = await client.post("/auth/dev-login",
                data={"email": "dev@gaia.local"}
            )
            
            # Should show error in production
            assert "not available" in response.text.lower()
    
    async def test_auth_middleware_protects_routes(self, client):
        """Test that auth middleware protects non-public routes"""
        # Try accessing protected route without auth
        response = await client.get("/chat", follow_redirects=False)
        
        # Should redirect to login
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
    
    async def test_auth_middleware_allows_public_routes(self, client):
        """Test that auth middleware allows public routes"""
        public_routes = ["/", "/login", "/register", "/auth/confirm", "/health"]
        
        for route in public_routes:
            response = await client.get(route, follow_redirects=False)
            # Should not redirect to login
            assert response.headers.get("location") != "/login"


class TestGatewayIntegration:
    """Test integration between web service and gateway"""
    
    async def test_gateway_client_no_auth_on_public_endpoints(self):
        """Ensure gateway client doesn't send auth headers for public endpoints"""
        from app.services.web.utils.gateway_client import GaiaAPIClient
        
        client = GaiaAPIClient()
        
        # Check that login method doesn't add auth headers
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.json.return_value = {"success": True}
            mock_post.return_value.raise_for_status = MagicMock()
            
            await client.login("test@example.com", "password")
            
            # Should not have Authorization or X-API-Key headers
            call_args = mock_post.call_args
            headers = call_args[1].get('headers', {})
            assert 'Authorization' not in headers
            assert 'X-API-Key' not in headers
        
        # Check register method
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.json.return_value = {"success": True}
            mock_post.return_value.raise_for_status = MagicMock()
            
            await client.register("test@example.com", "password")
            
            # Should not have auth headers
            call_args = mock_post.call_args
            headers = call_args[1].get('headers', {})
            assert 'Authorization' not in headers
            assert 'X-API-Key' not in headers