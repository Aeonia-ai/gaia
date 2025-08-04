# GAIA Platform Testing Guide

## Overview

The GAIA Platform uses a comprehensive three-tier testing strategy with automated tests for unit, integration, and end-to-end (E2E) scenarios. This guide consolidates all testing documentation into a single canonical source.

**🚨 CRITICAL**: Always use `./scripts/pytest-for-claude.sh` for running tests - NEVER use `pytest` directly (it will timeout after 2 minutes).

## Quick Start

```bash
# Set up environment (one-time)
./scripts/setup-dev-environment.sh

# Run all tests asynchronously
./scripts/pytest-for-claude.sh

# Monitor test progress
./scripts/check-test-progress.sh

# Run specific test categories
./scripts/pytest-for-claude.sh tests/unit -v        # Fast unit tests
./scripts/pytest-for-claude.sh tests/integration -v # Integration tests  
./scripts/pytest-for-claude.sh tests/e2e -v        # End-to-end tests
```

## Testing Philosophy

**Core Principle**: Automated tests over manual scripts

```bash
# ❌ BAD: Manual curl (knowledge lost after terminal closes)
curl -H "X-API-Key: $API_KEY" http://localhost:8666/api/v1/chat

# ✅ GOOD: Automated test (reproducible, validated, documented)
./scripts/pytest-for-claude.sh tests/integration/test_chat_api.py -v
```

### Why Automated Tests?

1. **Reproducibility**: Identical results every time
2. **Knowledge Capture**: Tests document how the system works
3. **Regression Prevention**: Catch bugs before deployment
4. **CI/CD Integration**: Automatic validation on every push
5. **Living Documentation**: Tests show actual system behavior

## Test Architecture

### Three-Tier Testing Strategy

```
┌─────────────────────────────────────────────────┐
│                   E2E Tests                     │
│        (Real auth, browser, user flows)         │
├─────────────────────────────────────────────────┤
│              Integration Tests                   │
│         (Real services, API contracts)          │
├─────────────────────────────────────────────────┤
│                 Unit Tests                      │
│         (Isolated logic, mocked deps)           │
└─────────────────────────────────────────────────┘
```

### Test Organization

```
tests/
├── unit/           # Fast, isolated tests (~100 tests)
├── integration/    # Service interaction tests (~80 tests)
├── e2e/           # Browser + real auth tests (~20 tests)
├── fixtures/      # Shared test utilities
└── utils/         # Test helpers (TestUserFactory, etc.)
```

## Environment Setup

### Required Environment Variables

```bash
# Basic testing
export API_KEY="your-test-api-key"

# E2E tests (REQUIRED for real auth)
export SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"

# Optional debugging
export PYTEST_VERBOSE="-vv"
export PYTEST_CAPTURE="no"  # See print statements
export BROWSER_TEST_MODE="visible"  # See browser during tests
```

### Docker Services

```bash
# Start all services
docker compose up -d

# Verify services are healthy
docker compose ps

# View logs if tests fail
docker compose logs -f gateway auth-service chat-service
```

## Running Tests

### By Test Type

```bash
# Unit tests (fast, ~2 seconds)
./scripts/pytest-for-claude.sh tests/unit -v

# Integration tests (~30 seconds)
./scripts/pytest-for-claude.sh tests/integration -v

# E2E tests (2-5 minutes, requires SUPABASE_SERVICE_KEY)
./scripts/pytest-for-claude.sh tests/e2e -v

# All tests (~5-10 minutes)
./scripts/pytest-for-claude.sh
```

### Specific Tests

```bash
# Run a specific test file
./scripts/pytest-for-claude.sh tests/integration/test_chat_api.py -v

# Run a specific test function
./scripts/pytest-for-claude.sh tests/integration/test_chat_api.py::test_send_message -v

# Run tests matching a pattern
./scripts/pytest-for-claude.sh -k "chat" -v

# Skip slow tests
./scripts/pytest-for-claude.sh -m "not slow" -v
```

### Monitoring Progress

```bash
# Start tests
./scripts/pytest-for-claude.sh

# Check if still running
./scripts/check-test-progress.sh

# Watch live output
tail -f pytest-*.log

# Find failures quickly
grep -E "FAILED|ERROR" pytest-*.log
```

## Writing Tests

### Unit Tests

Unit tests validate isolated logic with mocked dependencies:

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.unit
async def test_calculate_response_time():
    """Test response time calculation logic."""
    with patch('app.services.time_service') as mock_time:
        mock_time.get_current_time.return_value = 1000
        
        result = calculate_response_time(start=900)
        assert result == 100
```

**Characteristics**:
- Fast (<100ms per test)
- Heavy mocking
- No external dependencies
- Test pure logic

### Integration Tests

Integration tests verify service interactions with real dependencies:

```python
import pytest
import httpx

@pytest.mark.integration
async def test_chat_through_gateway(gateway_url, headers):
    """Test chat endpoint through gateway with real services."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{gateway_url}/api/v0.2/chat",
            headers=headers,
            json={"message": "Hello from integration test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["conversation_id"] is not None
```

**Characteristics**:
- Medium speed (~500ms per test)
- No mocking (real services)
- Docker dependencies required
- Test service contracts

### E2E Tests

E2E tests validate complete user journeys with real authentication:

```python
import pytest
import uuid
from playwright.async_api import async_playwright
from tests.utils.auth import TestUserFactory

@pytest.mark.e2e
async def test_user_login_and_chat():
    """Test complete user journey from login to chat."""
    factory = TestUserFactory()
    
    try:
        # Create unique test user
        user = factory.create_verified_test_user(
            email=f"e2e-{uuid.uuid4().hex[:8]}@test.local",
            password="TestPassword123!"
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Real login through UI
            await page.goto("http://localhost:8669/login")
            await page.fill('input[name="email"]', user["email"])
            await page.fill('input[name="password"]', user["password"])
            await page.click('button[type="submit"]')
            
            # Wait for redirect to chat
            await page.wait_for_url("**/chat")
            
            # Send message
            await page.fill('input[name="message"]', "Hello AI!")
            await page.click('button[type="submit"]')
            
            # Wait for response
            await page.wait_for_selector("#messages .ai-response")
            
            await browser.close()
            
    finally:
        # Always clean up test users
        factory.cleanup()
```

**🚨 CRITICAL E2E Rules**:
- **NO MOCKS ALLOWED** - Real authentication only
- Must have valid `SUPABASE_SERVICE_KEY`
- Use `TestUserFactory` for user management
- Always clean up test data
- Test complete user flows

## Test Patterns

### Async Test Execution

Claude Code has a 2-minute timeout, but our tests take longer. Always use the async runner:

```bash
# ❌ WRONG: Direct pytest (will timeout)
pytest tests/ -v

# ✅ RIGHT: Async execution
./scripts/pytest-for-claude.sh tests/ -v
```

### Parallel Test Execution

Tests run in parallel by default with pytest-xdist. For tests that can't run in parallel:

```python
@pytest.mark.xdist_group("serial_llm")
async def test_requires_serial_execution():
    """This test will run serially with others in the same group."""
    pass
```

### Test Markers

```python
@pytest.mark.unit          # Fast, isolated unit test
@pytest.mark.integration   # Integration test with real services
@pytest.mark.e2e          # End-to-end browser test
@pytest.mark.slow         # Test takes >5 seconds
@pytest.mark.container_safe  # Safe to run in containers
```

### Fixtures

Common fixtures available:

```python
# Authentication
@pytest.fixture
async def auth_headers():
    """Provides valid auth headers for API requests."""
    
# Service URLs
@pytest.fixture
def gateway_url():
    """Returns gateway URL based on environment."""
    
# Test clients
@pytest.fixture
async def test_client():
    """Provides configured test client."""
```

## Common Issues & Solutions

### "Command timed out after 2m 0.0s"

**Problem**: Direct pytest execution hits Claude's timeout  
**Solution**: Always use `./scripts/pytest-for-claude.sh`

### "Invalid API key" in E2E tests

**Problem**: Missing or invalid Supabase service key  
**Solution**: 
```bash
# Check your .env file
grep SUPABASE_SERVICE_KEY .env

# Verify the key works
python test_supabase_keys.py
```

### "No module named 'app'"

**Problem**: Running tests outside Docker container  
**Solution**: Tests must run in Docker environment
```bash
# Ensure services are running
docker compose up -d

# Use the test runner
./scripts/pytest-for-claude.sh
```

### EventSource/SSE Issues

**Problem**: Playwright doesn't send cookies with EventSource  
**Solution**: Known limitation - test other aspects or use integration tests for streaming

### Tests Pass Locally but Fail in CI

**Problem**: Missing environment variables or services  
**Solution**: 
1. Check Docker service dependencies
2. Verify all required env vars are set
3. Ensure services are healthy before tests run

## Best Practices

### DO:
- ✅ Use `./scripts/pytest-for-claude.sh` for all test execution
- ✅ Write tests for new features before implementing
- ✅ Use real authentication in E2E tests
- ✅ Clean up test data (especially users)
- ✅ Wait for specific conditions, not arbitrary timeouts
- ✅ Run relevant tests before committing
- ✅ Use descriptive test names that explain what's tested

### DON'T:
- ❌ Run `pytest` directly (will timeout)
- ❌ Use mocks in E2E tests
- ❌ Use hardcoded test data (use UUIDs)
- ❌ Skip cleanup in test teardown
- ❌ Test implementation details (test behavior)
- ❌ Write tests after fixing bugs (write first)

## Test Coverage

Current coverage goals:
- Overall: >80%
- Critical paths (auth, payments): >95%
- New code: >90%

Check coverage:
```bash
./scripts/pytest-for-claude.sh --cov=app --cov-report=html
open htmlcov/index.html
```

## CI/CD Integration

Tests run automatically on every push:

```yaml
# .github/workflows/test.yml
- name: Run Tests
  run: |
    docker compose up -d
    ./scripts/pytest-for-claude.sh
    ./scripts/check-test-progress.sh --wait
```

## Performance Benchmarks

Expected test execution times:
- Unit tests: 50-100ms each
- Integration tests: 200-1000ms each
- E2E tests: 2-5s each
- Full suite: <5 minutes

## Advanced Topics

### Security Testing

See [Security Testing Strategy](security-testing-strategy.md) for:
- SQL injection prevention
- XSS testing
- RBAC validation
- Rate limiting tests

### Performance Testing

```bash
# Load testing with locust
locust -f tests/load/locustfile.py

# Stress testing
./scripts/stress-test.sh --concurrent 100
```

### Browser Testing

For UI-specific testing:
- Mobile viewport: 390x844 (iPhone 12)
- Desktop viewport: 1920x1080
- Test with `BROWSER_TEST_MODE=visible` for debugging

### Docker Build Optimization

First build takes 10-15 minutes (includes Playwright). Use async builds:

```bash
# Start build in background
nohup docker compose build > build.log 2>&1 &

# Monitor progress
tail -f build.log
```

## Quick Reference

### Most Common Commands

```bash
# After code changes
./scripts/pytest-for-claude.sh tests/unit tests/integration -v

# Before committing
./scripts/pytest-for-claude.sh -m "not slow" -v

# Debug specific failure
./scripts/pytest-for-claude.sh tests/failing_test.py -vvs

# E2E with visible browser
BROWSER_TEST_MODE=visible ./scripts/pytest-for-claude.sh tests/e2e -v

# Check what's running
./scripts/check-test-progress.sh
```

### Test Selection Cheat Sheet

| Scenario | Command |
|----------|---------|
| Quick validation | `./scripts/pytest-for-claude.sh tests/unit -v` |
| API changes | `./scripts/pytest-for-claude.sh tests/integration -v` |
| UI changes | `./scripts/pytest-for-claude.sh tests/e2e -v` |
| Auth changes | `./scripts/pytest-for-claude.sh -k "auth" -v` |
| Pre-commit | `./scripts/pytest-for-claude.sh -m "not slow" -v` |
| Everything | `./scripts/pytest-for-claude.sh` |

## Related Documentation

- [Tester Agent](../../agents/tester.md) - Specialized testing agent
- [Async Test Execution](async-test-execution.md) - Deep dive on async runner
- [E2E Real Auth Testing](e2e-real-auth-testing.md) - E2E authentication details
- [Docker Test Optimization](docker-test-optimization.md) - Speed up Docker builds
- [Testing Philosophy](testing-philosophy.md) - Why we test this way

## Summary

The GAIA testing framework provides comprehensive coverage through:
1. **Unit tests** for isolated logic validation
2. **Integration tests** for service contract verification  
3. **E2E tests** for complete user journey validation

Remember: Always use `./scripts/pytest-for-claude.sh` and never mock authentication in E2E tests!