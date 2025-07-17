"""Tests for error handling and user feedback"""
import pytest
from unittest.mock import patch, Mock
from app.services.web.routes.auth import setup_routes
from app.services.web.components.gaia_ui import gaia_error_message, gaia_success_message
from fasthtml.core import FastHTML
from starlette.testclient import TestClient


pytestmark = pytest.mark.unit


class TestErrorHandling:
    """Test error handling and display"""
    
    def test_error_message_component(self):
        """Test error message component rendering"""
        error = gaia_error_message("Test error message")
        error_html = str(error)
        
        assert "bg-red-900/20" in error_html
        assert "border-red-600" in error_html
        assert "text-red-300" in error_html
        assert "Test error message" in error_html
        assert "⚠️" in error_html
    
    def test_success_message_component(self):
        """Test success message component rendering"""
        success = gaia_success_message("Test success message")
        success_html = str(success)
        
        assert "bg-green-900/20" in success_html
        assert "border-green-600" in success_html
        assert "text-green-300" in success_html
        assert "Test success message" in success_html
        assert "✓" in success_html
    
    def test_nested_error_parsing(self):
        """Test parsing of nested service errors"""
        app = FastHTML()
        setup_routes(app)
        client = TestClient(app)
        
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            # Simulate nested error from gateway
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.register.side_effect = Exception(
                'Service error: {"detail":"Please enter a valid email address"}'
            )
            
            response = client.post("/auth/register", data={
                "email": "bad@email",
                "password": "password123"
            })
            
            # Should extract the nested error message
            assert "Please enter a valid email address" in response.text
            assert "Service error" not in response.text  # Should be cleaned up
    
    def test_error_categories(self):
        """Test different error category handling"""
        app = FastHTML()
        setup_routes(app)
        client = TestClient(app)
        
        error_cases = [
            ("Email address is invalid", "Please enter a valid email address"),
            ("Password is too weak", "Password must be at least 6 characters"),
            ("Email already registered", "already registered"),
            ("Rate limit exceeded", "Too many attempts"),
            ("Unknown error", "check your email and password")
        ]
        
        for error_input, expected_output in error_cases:
            with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
                mock_instance = mock_client.return_value.__aenter__.return_value
                mock_instance.register.side_effect = Exception(
                    f'Service error: {{"detail":"{error_input}"}}'
                )
                
                response = client.post("/auth/register", data={
                    "email": "test@example.com",
                    "password": "password123"
                })
                
                assert expected_output.lower() in response.text.lower()
    
    def test_malformed_error_handling(self):
        """Test handling of malformed error responses"""
        app = FastHTML()
        setup_routes(app)
        client = TestClient(app)
        
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            # Simulate malformed error
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.register.side_effect = Exception("Some random error")
            
            response = client.post("/auth/register", data={
                "email": "test@example.com",
                "password": "password123"
            })
            
            # Should show generic error message
            assert "Registration failed" in response.text
            assert "Please check your email and password" in response.text
    
    def test_network_error_handling(self):
        """Test network error handling"""
        app = FastHTML()
        setup_routes(app)
        client = TestClient(app)
        
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.login.side_effect = Exception("Connection refused")
            
            response = client.post("/auth/login", data={
                "email": "test@example.com",
                "password": "password123"
            })
            
            # Should show connection error
            assert "Connection error" in response.text
    
    def test_html_escaping_in_errors(self):
        """Test that error messages are properly escaped"""
        app = FastHTML()
        setup_routes(app)
        client = TestClient(app)
        
        with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            # Try to inject HTML
            mock_instance.register.side_effect = Exception(
                'Service error: {"detail":"<script>alert(1)</script>"}'
            )
            
            response = client.post("/auth/register", data={
                "email": "test@example.com",
                "password": "password123"
            })
            
            # Script tag should be escaped
            assert "<script>" not in response.text
            assert "&lt;script&gt;" in response.text or "alert" in response.text