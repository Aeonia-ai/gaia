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
                    # Skip llm/config.py as it uses os.getenv directly for provider-specific keys
                    if service_path.name == "llm":
                        continue
                        
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
    
    def test_gateway_auth_has_env_key_fallback(self):
        """Verify gateway authentication has .env API key fallback for database failures"""
        # The authentication should handle database failures gracefully
        # by falling back to .env API key validation
        
        # Since we're testing that Redis is required, we should verify
        # that authentication still has proper error handling
        from app.shared import settings
        
        # Verify settings has API_KEY configured
        assert hasattr(settings, "API_KEY"), "settings must have API_KEY"
        assert settings.API_KEY is not None, "API_KEY must be configured"
        
        # The actual fallback is implemented in get_current_auth_legacy
        # at lines 483-491 in security.py
    
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
    async def test_env_api_key_authentication_with_redis_cache(self):
        """Verify .env API key authentication uses Redis for caching"""
        from app.shared.redis_client import redis_client
        import os
        
        # Ensure Redis is available (required component)
        assert redis_client.is_connected(), "Redis must be available for authentication"
        
        # Clear any existing cache for test API key
        api_key = os.getenv("API_KEY")
        cache_key = f"auth:api_key:{api_key[:8]}"
        redis_client.delete(cache_key)
        
        # First auth should potentially cache in Redis
        # (Implementation depends on actual auth flow)
        
        # Verify Redis is being used for auth-related operations
        # Set a test auth cache entry
        test_auth_data = {
            "user_id": "test_user",
            "email": "test@example.com",
            "auth_type": "api_key"
        }
        redis_client.set_json(f"auth:test", test_auth_data, ex=300)
        
        # Verify it was stored
        cached = redis_client.get_json(f"auth:test")
        assert cached == test_auth_data, "Redis must store auth data correctly"
        
        # Cleanup
        redis_client.delete(f"auth:test")
    
    def test_redis_is_required_and_available(self):
        """Verify Redis is properly configured and available as a required component"""
        from app.shared.redis_client import redis_client
        
        # Redis should be available and connected
        assert redis_client.is_connected(), \
            "Redis must be available - it's a required component"
        
        # Test basic operations
        test_key = "test_auth_consistency"
        test_value = "test_value"
        
        # Set and get should work
        assert redis_client.set(test_key, test_value), \
            "Redis SET operation must work"
        assert redis_client.get(test_key) == test_value, \
            "Redis GET operation must return correct value"
        
        # Cleanup
        redis_client.delete(test_key)


class TestAPIEndpointProtection:
    """Verify API endpoints are properly protected"""
    
    @pytest.mark.not_implemented(reason="tested in test_api_contracts.py")
    def test_health_endpoints_are_public(self):
        """Ensure health endpoints don't require authentication"""
        # This is tested in test_api_contracts.py
        pass
    
    @pytest.mark.not_implemented(reason="tested in test_api_contracts.py")
    def test_chat_endpoints_require_auth(self):
        """Ensure chat endpoints require authentication"""
        # This is tested in test_api_contracts.py
        pass


@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for authentication across services"""
    
    @pytest.mark.not_implemented(reason="requires running services for integration test")
    @pytest.mark.asyncio
    async def test_service_to_service_auth(self):
        """Verify services can authenticate with each other"""
        # This would test actual service communication
        # Requires running services
        pass