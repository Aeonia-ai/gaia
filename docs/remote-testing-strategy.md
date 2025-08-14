# Remote Testing Strategy for Gaia Platform

## Overview

This document outlines strategies for testing the Gaia Platform against remote deployments (dev, staging, production) rather than just local Docker containers.

## Current State

### What We Have
1. **Environment-aware fixtures** in `tests/load/conftest.py`:
   ```python
   GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway:8000")
   AUTH_URL = os.getenv("AUTH_URL", "http://auth-service:8000")
   ```

2. **Load tests** that can target remote endpoints
3. **API client** (`GaiaAPIClient`) that accepts base URLs
4. **Docker-based integration tests** that assume local services

### Limitations
- Most integration tests hardcode local service URLs
- E2E browser tests expect localhost URLs  
- No systematic approach for remote endpoint testing
- No environment-specific test configurations

## Proposed Remote Testing Architecture

### 1. Environment Configuration

Create environment-specific test configurations:

```bash
# .env.test.local (default)
TEST_GATEWAY_URL=http://gateway:8000
TEST_AUTH_URL=http://auth-service:8000
TEST_WEB_URL=http://localhost:8080
TEST_TIMEOUT=30

# .env.test.dev
TEST_GATEWAY_URL=https://gaia-gateway-dev.fly.dev
TEST_AUTH_URL=https://gaia-auth-dev.fly.dev
TEST_WEB_URL=https://gaia-web-dev.fly.dev
TEST_TIMEOUT=60
TEST_EXPECTED_FAILURES=personas,assets  # Known issues in dev

# .env.test.staging
TEST_GATEWAY_URL=https://gaia-gateway-staging.fly.dev
TEST_AUTH_URL=https://gaia-auth-staging.fly.dev
TEST_WEB_URL=https://gaia-web-staging.fly.dev
TEST_TIMEOUT=60

# .env.test.production
TEST_GATEWAY_URL=https://gaia-gateway-production.fly.dev
TEST_AUTH_URL=https://gaia-auth-production.fly.dev
TEST_WEB_URL=https://gaia-web-production.fly.dev
TEST_TIMEOUT=90
TEST_READ_ONLY=true  # No destructive tests
```

### 2. Test Categories for Remote Execution

#### A. API Contract Tests
- Test API endpoints against OpenAPI specs
- Verify response formats, status codes, headers
- Can run against any environment without side effects

```python
@pytest.mark.remote
@pytest.mark.contract
class TestAPIContracts:
    def test_chat_endpoint_contract(self, remote_gateway):
        response = remote_gateway.post("/api/v1/chat", json={...})
        assert response.status_code == 200
        assert "choices" in response.json()
```

#### B. Smoke Tests
- Basic health checks across all services
- Authentication flow verification
- Critical path testing (login → chat → logout)

```python
@pytest.mark.remote
@pytest.mark.smoke
class TestRemoteSmoke:
    def test_all_services_healthy(self, remote_gateway):
        health = remote_gateway.get("/health").json()
        assert all(s["status"] == "healthy" for s in health["services"].values())
```

#### C. Performance Tests
- Response time benchmarks
- Throughput testing
- Concurrent user simulation

```python
@pytest.mark.remote
@pytest.mark.performance
class TestRemotePerformance:
    async def test_chat_response_time(self, remote_gateway):
        start = time.time()
        await remote_gateway.chat("Hello")
        assert time.time() - start < 3.0  # 3 second SLA
```

#### D. Monitoring Tests
- Continuous checks that run periodically
- Alert on degradation
- Synthetic user journeys

```python
@pytest.mark.remote
@pytest.mark.monitoring
class TestSyntheticMonitoring:
    def test_user_journey_registration_to_chat(self, remote_env):
        # Complete user flow from registration to first chat
```

### 3. Remote Test Framework

#### Base Fixture for Remote Testing

```python
# tests/remote/conftest.py
import os
import pytest
from typing import Dict, Any

@pytest.fixture
def test_env() -> str:
    """Get current test environment."""
    return os.getenv("TEST_ENV", "local")

@pytest.fixture
def remote_config(test_env) -> Dict[str, Any]:
    """Load environment-specific configuration."""
    configs = {
        "local": {
            "gateway_url": "http://gateway:8000",
            "auth_url": "http://auth-service:8000",
            "timeout": 30,
            "destructive_allowed": True,
        },
        "dev": {
            "gateway_url": "https://gaia-gateway-dev.fly.dev",
            "auth_url": "https://gaia-auth-dev.fly.dev", 
            "timeout": 60,
            "destructive_allowed": True,
            "expected_failures": ["personas", "assets"],
        },
        "staging": {
            "gateway_url": "https://gaia-gateway-staging.fly.dev",
            "auth_url": "https://gaia-auth-staging.fly.dev",
            "timeout": 60,
            "destructive_allowed": True,
        },
        "production": {
            "gateway_url": "https://gaia-gateway-production.fly.dev",
            "auth_url": "https://gaia-auth-production.fly.dev",
            "timeout": 90,
            "destructive_allowed": False,  # Read-only in production!
        }
    }
    return configs[test_env]

@pytest.fixture
async def remote_gateway(remote_config):
    """Gateway client configured for remote testing."""
    async with GaiaAPIClient(
        base_url=remote_config["gateway_url"],
        timeout=remote_config["timeout"]
    ) as client:
        yield client

@pytest.fixture
def skip_if_expected_failure(remote_config, request):
    """Skip tests that are expected to fail in certain environments."""
    expected_failures = remote_config.get("expected_failures", [])
    for marker in request.node.iter_markers():
        if marker.name in expected_failures:
            pytest.skip(f"Expected failure in {test_env}: {marker.name}")
```

### 4. Test Execution Scripts

#### Remote Test Runner

```bash
#!/bin/bash
# scripts/test-remote.sh

# Usage: ./scripts/test-remote.sh [environment] [test-suite]
# Examples:
#   ./scripts/test-remote.sh dev smoke
#   ./scripts/test-remote.sh staging all
#   ./scripts/test-remote.sh production monitoring

ENV=${1:-dev}
SUITE=${2:-smoke}

# Load environment configuration
export TEST_ENV=$ENV
source .env.test.$ENV

echo "🌍 Running remote tests against: $ENV"
echo "📋 Test suite: $SUITE"

case $SUITE in
    smoke)
        pytest tests/remote/smoke/ -v -m "remote and smoke"
        ;;
    contract)
        pytest tests/remote/contract/ -v -m "remote and contract"
        ;;
    performance)
        pytest tests/remote/performance/ -v -m "remote and performance"
        ;;
    monitoring)
        pytest tests/remote/monitoring/ -v -m "remote and monitoring"
        ;;
    all)
        pytest tests/remote/ -v -m remote
        ;;
    *)
        echo "Unknown test suite: $SUITE"
        exit 1
        ;;
esac
```

### 5. Continuous Monitoring

#### GitHub Actions Workflow

```yaml
# .github/workflows/remote-monitoring.yml
name: Remote Environment Monitoring

on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
  workflow_dispatch:

jobs:
  monitor-dev:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run monitoring tests
        env:
          TEST_ENV: dev
          API_KEY: ${{ secrets.DEV_API_KEY }}
        run: |
          ./scripts/test-remote.sh dev monitoring
      
      - name: Alert on failure
        if: failure()
        uses: actions/slack@v1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          message: "⚠️ Dev environment monitoring failed!"

  monitor-production:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run monitoring tests
        env:
          TEST_ENV: production
          API_KEY: ${{ secrets.PROD_API_KEY }}
        run: |
          ./scripts/test-remote.sh production monitoring
```

### 6. Test Data Management

#### Remote Test Data Strategy

1. **Dedicated test accounts** per environment:
   - `test-dev@gaia.ai` for dev
   - `test-staging@gaia.ai` for staging
   - Read-only synthetic user for production

2. **Test data cleanup**:
   ```python
   @pytest.fixture
   async def remote_test_conversation(remote_gateway):
       """Create and cleanup test conversation."""
       conv = await remote_gateway.create_conversation()
       yield conv
       if remote_config["destructive_allowed"]:
           await remote_gateway.delete_conversation(conv.id)
   ```

3. **Environment-specific test data**:
   - Dev/Staging: Create and destroy test data
   - Production: Use read-only operations only

### 7. Migration Path

1. **Phase 1**: Create remote test structure
   - Set up `tests/remote/` directory
   - Create base fixtures and configs
   - Write initial smoke tests

2. **Phase 2**: Adapt existing tests
   - Make integration tests environment-aware
   - Add remote markers to suitable tests
   - Create remote-specific test suites

3. **Phase 3**: Continuous monitoring
   - Set up GitHub Actions
   - Configure alerting
   - Create dashboards

4. **Phase 4**: Performance baselines
   - Establish SLAs per environment
   - Create performance regression tests
   - Monitor trends over time

## Example Remote Tests

### 1. Basic Smoke Test
```python
# tests/remote/smoke/test_basic_health.py
@pytest.mark.remote
@pytest.mark.smoke
class TestRemoteHealth:
    def test_gateway_responsive(self, remote_gateway):
        """Verify gateway is responding."""
        response = remote_gateway.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_all_services_healthy(self, remote_gateway):
        """Verify all services report healthy."""
        health = remote_gateway.get("/health").json()
        for service, status in health["services"].items():
            assert status["status"] == "healthy", f"{service} is not healthy"
```

### 2. Authentication Flow Test
```python
# tests/remote/smoke/test_auth_flow.py
@pytest.mark.remote
@pytest.mark.smoke
class TestRemoteAuthFlow:
    async def test_api_key_auth(self, remote_gateway, test_api_key):
        """Verify API key authentication works."""
        response = await remote_gateway.chat(
            "Hello",
            headers={"X-API-Key": test_api_key}
        )
        assert response.status_code == 200
```

### 3. Performance Benchmark
```python
# tests/remote/performance/test_response_times.py
@pytest.mark.remote
@pytest.mark.performance
class TestResponseTimes:
    @pytest.mark.parametrize("percentile,threshold", [
        (50, 1.0),   # p50 < 1s
        (95, 3.0),   # p95 < 3s
        (99, 5.0),   # p99 < 5s
    ])
    async def test_chat_response_percentiles(self, remote_gateway, percentile, threshold):
        """Verify chat response times meet SLA."""
        times = []
        for _ in range(100):
            start = time.time()
            await remote_gateway.chat("Hello")
            times.append(time.time() - start)
        
        p = np.percentile(times, percentile)
        assert p < threshold, f"p{percentile} ({p:.2f}s) exceeds {threshold}s"
```

## Benefits

1. **Early detection** of production issues
2. **Performance regression** prevention
3. **API contract** enforcement
4. **Environment parity** validation
5. **Automated monitoring** without manual checks

## Next Steps

1. Create `tests/remote/` directory structure
2. Implement base fixtures and configurations
3. Write initial smoke test suite
4. Set up CI/CD integration
5. Establish monitoring dashboards