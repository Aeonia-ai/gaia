"""
Unit tests for web auth routes.

Tests the authentication behavior that browser tests depend on.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse
from fasthtml.components import Div
import os


class TestWebAuthRoutes:
    """Unit tests for web authentication routes"""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object"""
        request = AsyncMock(spec=Request)
        request.form = AsyncMock(return_value={
            "email": "test@test.local",
            "password": "testpass"
        })
        request.headers = {}
        request.session = {}
        return request
    
    @pytest.fixture
    def mock_gateway_client(self):
        """Create a mock gateway client"""
        client = AsyncMock()
        client.login = AsyncMock(return_value={
            "session": {
                "access_token": "test-jwt-token",
                "refresh_token": "test-refresh-token"
            },
            "user": {
                "id": "test-user-id",
                "email": "test@test.local",
                "email_confirmed_at": "2024-01-01T00:00:00Z"
            }
        })
        return client
    
    @pytest.mark.asyncio
    async def test_login_regular_form_submission(self, mock_request, mock_gateway_client):
        """Test login with regular form submission (non-HTMX)"""
        from app.services.web.routes.auth import login
        
        # Mock the GaiaAPIClient
        with patch('app.services.web.routes.auth.GaiaAPIClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_gateway_client
            
            # Call login handler
            response = await login(mock_request)
            
            # Should return redirect response
            assert isinstance(response, RedirectResponse)
            assert response.status_code == 303
            assert response.headers["location"] == "/chat"
            
            # Should set session data
            assert mock_request.session["jwt_token"] == "test-jwt-token"
            assert mock_request.session["user"]["email"] == "test@test.local"
    
    @pytest.mark.asyncio
    async def test_login_htmx_request(self, mock_request, mock_gateway_client):
        """Test login with HTMX request"""
        from app.services.web.routes.auth import login
        
        # Set HTMX header
        mock_request.headers["hx-request"] = "true"
        
        with patch('app.services.web.routes.auth.GaiaAPIClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_gateway_client
            
            # Call login handler
            response = await login(mock_request)
            
            # Should return HTMLResponse with HX-Redirect header
            assert isinstance(response, HTMLResponse)
            assert response.headers["HX-Redirect"] == "/chat"
    
    @pytest.mark.asyncio
    async def test_test_login_endpoint(self, mock_request):
        """Test the test-login endpoint for browser tests"""
        from app.services.web.routes.auth import test_login
        
        # Enable test mode
        with patch.dict(os.environ, {"TEST_MODE": "true"}):
            # Test with non-HTMX request
            response = await test_login(mock_request)
            
            # Should redirect to chat
            assert isinstance(response, RedirectResponse)
            assert response.status_code == 303
            assert response.headers["location"] == "/chat"
            
            # Should set session
            assert mock_request.session["jwt_token"] == "test-token-test@test.local"
            assert mock_request.session["user"]["email"] == "test@test.local"
    
    @pytest.mark.asyncio
    async def test_test_login_htmx(self, mock_request):
        """Test the test-login endpoint with HTMX"""
        from app.services.web.routes.auth import test_login
        
        # Enable test mode and set HTMX header
        mock_request.headers["hx-request"] = "true"
        
        with patch.dict(os.environ, {"TEST_MODE": "true"}):
            response = await test_login(mock_request)
            
            # Should return HTMLResponse with HX-Redirect
            assert isinstance(response, HTMLResponse)
            assert response.headers["HX-Redirect"] == "/chat"
    
    @pytest.mark.asyncio
    async def test_login_unverified_email(self, mock_request, mock_gateway_client):
        """Test login with unverified email"""
        from app.services.web.routes.auth import login
        
        # Mock unverified email response
        mock_gateway_client.login.return_value = {
            "session": {"access_token": "test-jwt-token"},
            "user": {
                "id": "test-user-id",
                "email": "test@test.local",
                "email_confirmed_at": None  # Not verified
            }
        }
        
        with patch('app.services.web.routes.auth.GaiaAPIClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_gateway_client
            
            with patch('app.services.web.routes.auth.auth_page_replacement') as mock_auth_page:
                response = await login(mock_request)
                
                # Should call auth_page_replacement for unverified email
                mock_auth_page.assert_called_once()
                call_args = mock_auth_page.call_args[1]
                assert "Email Not Verified" in call_args["title"]
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, mock_request, mock_gateway_client):
        """Test login with invalid credentials"""
        from app.services.web.routes.auth import login
        
        # Mock login failure
        mock_gateway_client.login.side_effect = Exception("Invalid credentials")
        
        with patch('app.services.web.routes.auth.GaiaAPIClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_gateway_client
            
            with patch('app.services.web.routes.auth.gaia_error_message') as mock_error:
                mock_error.return_value = "Error response"
                
                response = await login(mock_request)
                
                # Should return error message
                mock_error.assert_called_with("Invalid email or password")
    
    @pytest.mark.asyncio
    async def test_dev_login_in_debug_mode(self, mock_request):
        """Test dev login works in debug mode"""
        from app.services.web.routes.auth import dev_login
        
        # Set dev credentials
        mock_request.form.return_value = {
            "email": "dev@gaia.local",
            "password": "testtest"
        }
        
        with patch('app.services.web.routes.auth.settings') as mock_settings:
            mock_settings.debug = True
            
            response = await dev_login(mock_request)
            
            # Should redirect to chat
            assert isinstance(response, RedirectResponse)
            assert response.status_code == 303
            assert response.headers["location"] == "/chat"
            
            # Should set dev session
            assert mock_request.session["user"]["email"] == "dev@gaia.local"
    
    def test_browser_test_expectations(self):
        """Document what browser tests need to mock correctly"""
        expected_mocks = {
            "regular_redirect": {
                "route": "/auth/login",
                "response": {
                    "status": 303,
                    "headers": {"Location": "/chat"}
                }
            },
            "htmx_redirect": {
                "route": "/auth/login",
                "headers_required": {"hx-request": "true"},
                "response": {
                    "status": 200,
                    "headers": {"HX-Redirect": "/chat"},
                    "body": "HTML content (can be empty)"
                }
            },
            "test_mode_login": {
                "route": "/auth/test-login",
                "env_required": {"TEST_MODE": "true"},
                "form_data": {
                    "email": "anything@test.local",
                    "password": "anything"
                }
            }
        }
        
        # This documents the expected behavior for browser tests
        assert expected_mocks is not None