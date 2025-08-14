"""
Basic health checks for remote environments.

These smoke tests verify that services are running and responsive.
They should pass in all environments (dev, staging, production).
"""

import pytest
import logging

logger = logging.getLogger(__name__)


@pytest.mark.remote
@pytest.mark.smoke
class TestRemoteHealth:
    """Basic health checks for remote deployments."""
    
    @pytest.mark.asyncio
    async def test_gateway_health_endpoint(self, remote_gateway, track_response_time):
        """Verify gateway health endpoint is responsive."""
        track_response_time.start()
        
        response = await remote_gateway.get("/health")
        
        track_response_time.assert_under(5.0, "gateway health check")
        
        assert response.status_code == 200
        health = response.json()
        
        assert health["status"] == "healthy"
        assert "timestamp" in health
        assert "version" in health
        
        logger.info(f"Gateway version: {health['version']}")
    
    @pytest.mark.asyncio
    async def test_all_services_healthy(self, remote_gateway, test_env):
        """Verify all expected services report healthy status."""
        response = await remote_gateway.get("/health")
        assert response.status_code == 200
        
        health = response.json()
        services = health.get("services", {})
        
        # Expected services per environment
        expected_services = {
            "local": ["auth", "chat", "kb", "asset"],
            "dev": ["auth", "chat", "kb", "asset"],
            "staging": ["auth", "chat", "kb"],  # Asset might not be deployed
            "production": ["auth", "chat", "kb", "asset"]
        }
        
        for service in expected_services.get(test_env, []):
            if service in services:
                assert services[service]["status"] == "healthy", \
                    f"{service} is not healthy: {services[service]}"
                assert services[service].get("response_time", 0) < 1.0, \
                    f"{service} response time too high"
            else:
                logger.warning(f"Service {service} not found in health check")
    
    @pytest.mark.asyncio
    async def test_database_connectivity(self, remote_gateway):
        """Verify database is connected and responsive."""
        response = await remote_gateway.get("/health")
        assert response.status_code == 200
        
        health = response.json()
        db_health = health.get("database", {})
        
        assert db_health.get("status") == "healthy"
        assert db_health.get("responsive") is True
        
        logger.info(f"Database type: {db_health.get('database', 'unknown')}")
    
    @pytest.mark.asyncio
    async def test_redis_connectivity(self, remote_gateway, test_env):
        """Verify Redis is connected (if configured)."""
        response = await remote_gateway.get("/health")
        assert response.status_code == 200
        
        health = response.json()
        redis_health = health.get("redis")
        
        # Redis might not be configured in all environments
        if redis_health:
            assert redis_health.get("status") == "healthy"
            assert redis_health.get("connected") is True
        else:
            logger.info(f"Redis not configured in {test_env}")
    
    @pytest.mark.asyncio
    async def test_supabase_connectivity(self, remote_gateway):
        """Verify Supabase connection is healthy."""
        response = await remote_gateway.get("/health")
        assert response.status_code == 200
        
        health = response.json()
        supabase_health = health.get("supabase")
        
        if supabase_health:
            assert supabase_health.get("status") == "healthy"
            assert supabase_health.get("responsive") is True
            assert "url" in supabase_health
            
            logger.info(f"Supabase URL: {supabase_health['url']}")
    
    @pytest.mark.asyncio
    async def test_direct_service_health(self, remote_chat, test_env):
        """Test direct access to individual services (if accessible)."""
        # Skip if we can't access services directly
        if test_env in ["staging", "production"]:
            pytest.skip("Direct service access not available in this environment")
        
        response = await remote_chat.get("/health")
        assert response.status_code == 200
        
        health = response.json()
        assert health["service"] == "chat"
        assert health["status"] == "healthy"