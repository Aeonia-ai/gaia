"""
Authentication Consistency Tests

These tests ensure authentication works consistently across all services
and prevents common configuration mistakes.
"""
import os
import pytest
import importlib
import pkgutil
from pathlib import Path


class TestAuthenticationConsistency:
    """Verify authentication configuration is consistent across services"""
    
    def test_all_services_use_shared_settings(self):
        """Ensure all services import settings from app.shared"""
        services_dir = Path("app/services")
        
        for service_path in services_dir.iterdir():
            if service_path.is_dir() and not service_path.name.startswith("__"):
                config_file = service_path / "config.py"
                
                if config_file.exists():
                    content = config_file.read_text()
                    
                    # Check for shared settings import
                    assert "from app.shared import settings" in content or \
                           "from app.shared.config import" in content, \
                           f"{service_path.name}/config.py must use shared settings"
                    
                    # Check for forbidden patterns
                    forbidden_patterns = [
                        "WEB_API_KEY",
                        "GATEWAY_API_KEY", 
                        "SERVICE_API_KEY",
                        "AUTH_API_KEY",
                        'env_prefix = "WEB_"',
                        'env_prefix = "GATEWAY_"',
                        'env_prefix = "SERVICE_"'
                    ]
                    
                    for pattern in forbidden_patterns:
                        assert pattern not in content, \
                            f"{service_path.name}/config.py contains forbidden pattern: {pattern}"
    
    def test_env_api_key_is_set(self):
        """Verify API_KEY environment variable is properly set"""
        api_key = os.getenv("API_KEY")
        assert api_key is not None, "API_KEY must be set in environment"
        assert len(api_key) > 20, "API_KEY must be a proper length"
        assert api_key != "your-api-key-here", "API_KEY must not be the default value"
    
    def test_shared_settings_loads_api_key(self):
        """Verify shared settings properly loads API_KEY"""
        from app.shared import settings
        
        assert hasattr(settings, "API_KEY"), "settings must have API_KEY attribute"
        assert settings.API_KEY == os.getenv("API_KEY"), \
            "settings.API_KEY must match environment variable"
    
    def test_gateway_auth_checks_env_key_first(self):
        """Verify gateway authentication checks .env API key before database"""
        from app.shared.security import get_current_auth_legacy
        import inspect
        
        # Get the source code of the function
        source = inspect.getsource(get_current_auth_legacy)
        
        # Find positions of key checks
        env_check_pos = source.find("settings.API_KEY")
        db_check_pos = source.find("get_database_session")
        
        assert env_check_pos != -1, "Must check settings.API_KEY"
        assert db_check_pos != -1, "Must check database"
        assert env_check_pos < db_check_pos, \
            ".env API key check must come BEFORE database check"
    
    def test_no_service_specific_api_keys_in_env(self):
        """Ensure no service-specific API keys in docker-compose.yml"""
        compose_file = Path("docker-compose.yml")
        if compose_file.exists():
            content = compose_file.read_text()
            
            forbidden_vars = [
                "WEB_API_KEY",
                "GATEWAY_API_KEY",
                "AUTH_API_KEY",
                "SERVICE_API_KEY"
            ]
            
            for var in forbidden_vars:
                assert var not in content, \
                    f"docker-compose.yml must not contain {var}"
    
    @pytest.mark.asyncio
    async def test_env_api_key_works_without_database(self):
        """Verify .env API key authentication works without database"""
        from app.shared.security import get_current_auth_legacy
        from fastapi import Request
        from unittest.mock import Mock, MagicMock
        
        # Mock request with API key header
        mock_request = Mock(spec=Request)
        
        # Mock the security dependencies
        mock_credentials = None  # No JWT
        mock_api_key = os.getenv("API_KEY")
        
        # This should work without any database connection
        try:
            result = await get_current_auth_legacy(
                mock_request,
                mock_credentials,
                mock_api_key
            )
            
            assert result["auth_type"] == "api_key"
            assert result["key"] == mock_api_key
        except Exception as e:
            pytest.fail(f".env API key auth should work without database: {e}")
    
    def test_redis_caching_is_optional(self):
        """Verify authentication works even if Redis is down"""
        from app.shared.security import get_current_auth_legacy
        import inspect
        
        # Check that Redis failures are handled gracefully
        source = inspect.getsource(get_current_auth_legacy)
        
        # Should have try/except around Redis operations
        assert "try:" in source and "redis" in source.lower(), \
            "Redis operations must be wrapped in try/except"
        assert "except" in source, \
            "Must handle Redis failures gracefully"


class TestAPIEndpointProtection:
    """Verify API endpoints are properly protected"""
    
    def test_health_endpoints_are_public(self):
        """Ensure health endpoints don't require authentication"""
        # This is tested in test_api_contracts.py
        pass
    
    def test_chat_endpoints_require_auth(self):
        """Ensure chat endpoints require authentication"""
        # This is tested in test_api_contracts.py
        pass


@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for authentication across services"""
    
    @pytest.mark.asyncio
    async def test_service_to_service_auth(self):
        """Verify services can authenticate with each other"""
        # This would test actual service communication
        # Requires running services
        pass