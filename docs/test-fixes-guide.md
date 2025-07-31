# Web Service Test Fixes Guide

This guide addresses the test failures discovered when running web service tests on a fresh machine.

## Issues Identified

1. **Port Configuration**: Tests trying to connect to port 80, but services run on:
   - Gateway: 8666
   - Web: 8080

2. **Async Pattern Mismatch**: Tests using `await client.post()` but Starlette TestClient is synchronous

3. **API Endpoint Mismatches**: Wrong endpoints in tests vs actual implementation

4. **Framework Differences**: Tests written for Flask patterns but running against FastHTML

## Quick Fixes

### 1. Fix Test Client Usage (Remove async)

In `tests/web/test_auth_flow.py` and similar files:

```python
# WRONG - TestClient is synchronous
async def test_login_endpoint_is_public(self, client):
    response = await client.post("/auth/login", data={...})

# CORRECT
def test_login_endpoint_is_public(self, client):
    response = client.post("/auth/login", data={...})
```

### 2. Fix Gateway Client URLs

In `tests/web/test_gateway_client.py`:

```python
# Update endpoint paths
# WRONG
response = await gateway_client.post("/api/v1/chat", ...)

# CORRECT - Check actual gateway endpoints
response = await gateway_client.post("/api/v1/chat/completions", ...)
# or
response = await gateway_client.post("/api/v0.2/chat", ...)
```

### 3. Environment Variable Override for Tests

Create a test environment file or set in conftest.py:

```python
# tests/web/conftest.py
import os
os.environ["GATEWAY_URL"] = "http://localhost:8666"
os.environ["WEB_SERVICE_URL"] = "http://localhost:8080"
```

### 4. Fix Test Client Initialization

Update `tests/web/conftest.py`:

```python
@pytest.fixture
def client():
    """Test client for FastHTML app"""
    # Ensure app is properly initialized
    from app.services.web.main import app
    return TestClient(app)

@pytest.fixture
def async_client():
    """Async HTTP client for integration tests"""
    import httpx
    return httpx.AsyncClient(base_url="http://localhost:8080")
```

### 5. Update Authentication Tests

For tests that need to hit the actual running services:

```python
# Use httpx for real HTTP calls
async def test_real_login_flow():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/auth/login",
            data={"email": "test@example.com", "password": "password"}
        )
        assert response.status_code == 200
```

## Running Tests Correctly

```bash
# Start services first
docker compose up -d

# Run tests
docker compose run test pytest tests/web/ -v

# Or run specific test file
docker compose run test pytest tests/web/test_simple.py -v
```

## Test Categories to Fix

1. **Unit Tests** (use mocked TestClient)
   - Don't need services running
   - Use synchronous TestClient
   - Mock external dependencies

2. **Integration Tests** (use real HTTP client)
   - Need services running
   - Use httpx.AsyncClient
   - Hit actual endpoints

3. **UI Tests** (use Playwright)
   - Need full stack running
   - Test actual browser interactions
   - Already properly async

## Example Fixed Test

```python
# tests/web/test_auth_flow_fixed.py
import pytest
from starlette.testclient import TestClient
import httpx

class TestAuthenticationFlow:
    """Fixed authentication flow tests"""
    
    def test_login_page_renders(self, client):
        """Unit test - synchronous"""
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b"Login" in response.content
    
    @pytest.mark.asyncio
    async def test_login_integration(self):
        """Integration test - async with real services"""
        async with httpx.AsyncClient() as client:
            # First check if services are up
            health = await client.get("http://localhost:8666/health")
            if health.status_code != 200:
                pytest.skip("Services not running")
            
            # Test actual login
            response = await client.post(
                "http://localhost:8080/auth/login",
                data={"email": "dev@gaia.local", "password": "development"}
            )
            assert response.status_code in [200, 303]  # Success or redirect
```

## Summary

The main issue is that the tests were written with assumptions that don't match the actual implementation:
- Wrong ports
- Wrong async patterns  
- Wrong endpoints

These are all fixable by updating the test configuration and patterns, not the application code.