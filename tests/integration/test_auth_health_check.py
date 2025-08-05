"""
Test auth service health check endpoint.
Tests the comprehensive authentication health endpoint.
"""

import pytest
import httpx
import asyncio
from typing import Dict, Any


class TestAuthHealthCheck:
    """Test authentication health check functionality."""
    
    @pytest.mark.asyncio
    async def test_auth_health_endpoint_exists(self):
        """Test that the auth health endpoint exists and responds."""
        auth_url = "http://auth-service:8000"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{auth_url}/auth/health")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            
            # Verify response structure
            assert "service" in data
            assert "timestamp" in data
            assert "overall_status" in data
            assert "checks" in data
            
            assert data["service"] == "auth"
            assert data["overall_status"] in ["healthy", "warning", "error"]
    
    @pytest.mark.asyncio
    async def test_auth_health_checks_secrets(self):
        """Test that health check validates secrets configuration."""
        auth_url = "http://auth-service:8000"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{auth_url}/auth/health")
            data = response.json()
            
            # Should have secrets check
            assert "secrets" in data["checks"]
            secrets_check = data["checks"]["secrets"]
            
            assert "status" in secrets_check
            assert secrets_check["status"] in ["healthy", "warning", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_auth_health_checks_backend(self):
        """Test that health check reports authentication backend."""
        auth_url = "http://auth-service:8000"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{auth_url}/auth/health")
            data = response.json()
            
            # Should have auth backend check
            assert "auth_backend" in data["checks"]
            backend_check = data["checks"]["auth_backend"]
            
            assert "configured" in backend_check
            assert "status" in backend_check
            assert backend_check["configured"] in ["supabase", "postgresql"]
            assert backend_check["status"] == "healthy"
    
    @pytest.mark.asyncio 
    async def test_auth_health_checks_supabase_when_configured(self):
        """Test that health check validates Supabase when configured."""
        auth_url = "http://auth-service:8000"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{auth_url}/auth/health")
            data = response.json()
            
            # If Supabase is configured, should have supabase check
            backend_check = data["checks"].get("auth_backend", {})
            if backend_check.get("configured") == "supabase":
                assert "supabase" in data["checks"]
                supabase_check = data["checks"]["supabase"]
                
                assert "status" in supabase_check
                # Should be healthy or have specific error
                assert supabase_check["status"] in ["healthy", "error"]
    
    @pytest.mark.asyncio
    async def test_auth_health_checks_api_key_validation(self):
        """Test that health check validates API key validation capability."""
        auth_url = "http://auth-service:8000"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{auth_url}/auth/health")
            data = response.json()
            
            # Should have API key validation check
            assert "api_key_validation" in data["checks"]
            api_key_check = data["checks"]["api_key_validation"]
            
            assert "status" in api_key_check
            assert "backend" in api_key_check 
            assert api_key_check["backend"] in ["supabase", "postgresql"]
            assert api_key_check["status"] in ["healthy", "error"]
    
    @pytest.mark.asyncio
    async def test_auth_health_response_format(self):
        """Test that health response has correct format."""
        auth_url = "http://auth-service:8000"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{auth_url}/auth/health")
            data = response.json()
            
            # Required fields
            required_fields = ["service", "timestamp", "overall_status", "checks"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            # Check data types
            assert isinstance(data["checks"], dict)
            assert data["service"] == "auth"
            
            # If there are errors, should have error_count
            if data["overall_status"] == "error":
                assert "error_count" in data
                assert isinstance(data["error_count"], int)
                assert data["error_count"] > 0
            
            # If there are warnings, should have warning_count
            if data["overall_status"] == "warning":
                assert "warning_count" in data
                assert isinstance(data["warning_count"], int)
                assert data["warning_count"] > 0