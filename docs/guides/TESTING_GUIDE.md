# GAIA Platform Testing Guide

> **This is the canonical testing guide for the GAIA platform.** It consolidates all testing documentation into a single, authoritative source.

> **🆕 Update**: A new testing strategy is being developed as part of web service standardization. See [Web Testing Strategy Post-Standardization](../web-testing-strategy-post-standardization.md) for upcoming improvements that will dramatically simplify web testing.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Testing Philosophy](#testing-philosophy)
3. [Test Organization](#test-organization)
4. [Running Tests](#running-tests)
5. [Writing Tests](#writing-tests)
6. [Test Categories](#test-categories)
7. [Development Workflow](#development-workflow)
8. [CI/CD Integration](#cicd-integration)
9. [Troubleshooting](#troubleshooting)
10. [Test Consolidation](#test-consolidation)

## Quick Start

### Prerequisites
```bash
# One-time setup
./scripts/setup-dev-environment.sh

# Ensure services are running
docker compose up -d
```


### Running Your First Tests
```bash
# Run all tests asynchronously (avoids timeouts)
./scripts/pytest-for-claude.sh

# Monitor test progress
./scripts/check-test-progress.sh

# Run specific test categories
./scripts/pytest-for-claude.sh tests/unit -v        # Unit tests (fastest)
./scripts/pytest-for-claude.sh tests/integration -v # Integration tests
./scripts/pytest-for-claude.sh tests/e2e -v        # End-to-end tests
```

**⚠️ CRITICAL**: Always use `./scripts/pytest-for-claude.sh` instead of `pytest` directly. The Bash tool in Claude Code has a 2-minute timeout, but tests can take 5-15 minutes.

## Testing Philosophy

### CRITICAL: Tests Define Truth, Not Current Behavior

**When a test fails, FIX THE CODE, not the test!** Tests are specifications of correct behavior. Changing tests to match broken code is a critical anti-pattern that undermines the entire purpose of testing.

```python
# ❌ WRONG: Changing test to accept incorrect behavior
assert response.status_code in [200, 401]  # Whatever the code returns!

# ✅ RIGHT: Fix the service to return correct status
assert response.status_code == 401  # This is the specification
```

See [Tests Define Truth](CRITICAL_TESTING_PRINCIPLE_TESTS_DEFINE_TRUTH.md) for detailed guidance.

### Core Principle: Automated Tests Over Manual Scripts

We prioritize automated tests because they provide:
- **Reproducibility**: Same results every time
- **Knowledge Capture**: Documents how the system works
- **Regression Prevention**: Catches breaking changes
- **CI/CD Integration**: Automated validation

```bash
# ❌ Bad: Manual curl command (lost after terminal closes)
curl -H "X-API-Key: $API_KEY" http://localhost:8666/api/v1/chat

# ✅ Good: Automated test (permanent, validated, documented)
./scripts/pytest-for-claude.sh tests/integration/test_chat_api.py -v
```

### Test-Driven Development (TDD)
1. **Write a failing test** that defines desired behavior
2. **Write minimal code** to make the test pass
3. **Refactor** while keeping tests green
4. **Repeat** for each new feature or bug fix

## Test Organization

```
tests/
├── unit/                    # Fast, isolated component tests
│   ├── test_api_client.py
│   ├── test_auth_utils.py
│   └── test_conversation_store.py
├── integration/             # Service interaction tests
│   ├── chat/
│   │   ├── test_intelligent_routing.py  # NEW: Routing logic tests
│   │   ├── test_unified_streaming_format.py
│   │   └── test_mcp_agent_hot_loading.py  # NEW: Hot loading tests
│   ├── gateway/
│   │   └── test_gateway_auth_endpoints.py
│   ├── kb/
│   │   └── test_kb_endpoints.py
│   └── compatibility/
│       └── test_llm_platform.py  # NEW: Legacy API tests
├── performance/             # Performance benchmarks
│   └── test_kb_storage_performance.py  # NEW: Storage perf tests
├── e2e/                     # End-to-end user flows
│   ├── test_real_auth_e2e.py
│   └── test_chat_flow_e2e.py
├── web/                     # Browser-based UI tests
│   ├── test_chat_behaviors.py
│   └── test_layout_integrity.py
└── fixtures/                # Shared test utilities
    ├── test_auth.py         # Auth helpers
    └── test_data.py         # Test data generators
```

## Running Tests

### Basic Commands

```bash
# Run all tests
./scripts/pytest-for-claude.sh

# Run with verbose output
./scripts/pytest-for-claude.sh -v

# Run specific test file
./scripts/pytest-for-claude.sh tests/unit/test_api_client.py -v

# Run specific test method
./scripts/pytest-for-claude.sh tests/unit/test_api_client.py::TestAPIClient::test_health_check -v

# Run tests matching pattern
./scripts/pytest-for-claude.sh -k "chat" -v

# Run with debug output
./scripts/pytest-for-claude.sh -v -s
```

### Monitoring Test Progress

Since tests run asynchronously, use these commands to monitor:

```bash
# Check if tests are still running
./scripts/check-test-progress.sh

# Watch test output in real-time
tail -f logs/tests/pytest/test-run-*.log

# View last test results
cat logs/tests/pytest/test-run-*.log | grep -E "(PASSED|FAILED|ERROR)"
```

### Test Markers

```bash
# Skip slow tests
./scripts/pytest-for-claude.sh -m "not slow"

# Run only integration tests
./scripts/pytest-for-claude.sh -m "integration"

# Run security tests
./scripts/pytest-for-claude.sh -m "security"
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from tests.fixtures.test_auth import JWTTestAuth

class TestChatAPI:
    """Test chat API endpoints"""
    
    @pytest.fixture
    def jwt_auth(self):
        """Create JWT auth helper"""
        return JWTTestAuth()
    
    @pytest.mark.asyncio
    async def test_send_message(self, jwt_auth):
        """Test sending a chat message"""
        # Arrange
        headers = jwt_auth.create_auth_headers(user_id="test-user")
        message_data = {"message": "Hello, AI!"}
        
        # Act
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://chat-service:8000/v1/chat",
                headers=headers,
                json=message_data
            )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0
```

### Using Fixtures

```python
# Common fixtures from tests/fixtures/test_auth.py
from tests.fixtures.test_auth import JWTTestAuth, TestUserFactory

# For unit tests (no real auth)
jwt_auth = JWTTestAuth()
headers = jwt_auth.create_auth_headers(user_id="test-123")

# For integration tests (real Supabase users)
user_factory = TestUserFactory()
test_user = user_factory.create_verified_test_user()
# ... perform real login to get token
user_factory.cleanup_all()  # Clean up after tests
```

### Best Practices

1. **Use descriptive test names**: `test_chat_message_with_invalid_token_returns_401`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **One assertion focus**: Test one behavior per test
4. **Clean up resources**: Use fixtures with cleanup
5. **Mock external services**: Except in E2E tests
6. **Separate tests by API version**: Don't mix v1, v0.2, and v0.3 tests in the same file
7. **Test version-specific behaviors**: Each API version has different context persistence patterns
8. **Validate response formats**: v0.3 should never expose internal details

**API Version Test Organization**:
- Keep API versions in separate test files for clarity
- Name files with version prefix: `test_api_v1_*.py`, `test_api_v02_*.py`, `test_api_v03_*.py`
- Ensure equivalent test coverage across all supported API versions
- Document version-specific behaviors in test comments

For more patterns, see [TESTING_BEST_PRACTICES.md](TESTING_BEST_PRACTICES.md).

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Speed**: Very fast (< 1 second per test)
- **Dependencies**: Mocked
- **Example**: Testing a utility function

```bash
./scripts/pytest-for-claude.sh tests/unit -v
```

### Integration Tests (`tests/integration/`)
- **Purpose**: Test service interactions
- **Speed**: Medium (1-5 seconds per test)
- **Dependencies**: Real services, test database
- **Example**: Testing API endpoints

```bash
./scripts/pytest-for-claude.sh tests/integration -v
```

#### API Version Test Organization

Integration tests are organized by API version to ensure clear separation and equivalent coverage:

**v0.3 API Tests** (`test_api_v03_*.py`)
- Clean interface with no exposed provider details
- Automatic persona integration via unified chat
- Always-on directive enhancement system
- Example: `test_api_v03_conversations_auth.py`, `test_api_v03_endpoints.py`

**v1 API Tests** (`test_api_v1_*.py`, `test_v1_*.py`)
- OpenAI-compatible format
- Requires explicit conversation_id for context persistence
- Model/provider selection support
- Example: `test_api_v1_conversations_auth.py`, `test_v1_conversation_persistence.py`

**v0.2 API Tests** (`test_api_v02_*.py`, `test_v02_*.py`)
- Legacy format with provider details
- Automatic context persistence without conversation_id
- Direct provider/model exposure
- Example: `test_api_v02_completions_auth.py`, `test_v02_conversation_persistence.py`

**Key API Version Behaviors**:
```python
# v1: Requires conversation_id for context
response1 = await client.post("/api/v1/chat", json={"message": "Remember 42"})
# Context lost without conversation_id
response2 = await client.post("/api/v1/chat", json={"message": "What number?"})
# Context maintained with conversation_id
response3 = await client.post("/api/v1/chat", json={
    "message": "What number?",
    "conversation_id": response1.json()["_metadata"]["conversation_id"]
})

# v0.2: Automatic context persistence
response1 = await client.post("/api/v0.2/chat", json={"message": "Remember blue"})
# Context maintained automatically
response2 = await client.post("/api/v0.2/chat", json={"message": "What color?"})

# v0.3: Clean interface with hidden intelligence
response = await client.post("/api/v0.3/chat", json={"message": "Hello"})
# Returns only: {"response": "...", "conversation_id": "..."}
# No provider, model, or internal details exposed
```

### End-to-End Tests (`tests/e2e/`)
- **Purpose**: Test complete user workflows
- **Speed**: Slow (5-30 seconds per test)
- **Dependencies**: All real services, real authentication
- **Example**: User registration → login → chat → logout

```bash
# Requires SUPABASE_SERVICE_KEY in .env
./scripts/pytest-for-claude.sh tests/e2e -v
```

**🚨 CRITICAL: E2E tests MUST use real authentication - NO MOCKS!**

#### E2E Test Pattern with Real Auth
```python
from tests.fixtures.test_auth import TestUserFactory
import uuid

async def test_complete_user_journey():
    """Test with real Supabase authentication."""
    factory = TestUserFactory()
    
    # Create unique test user
    test_email = f"e2e-{uuid.uuid4().hex[:8]}@test.local"
    test_password = "TestPassword123!"
    
    try:
        # Create verified user (no email confirmation needed)
        user = factory.create_verified_test_user(
            email=test_email,
            password=test_password
        )
        
        # Test real login and functionality
        # ... test implementation ...
            
    finally:
        # Always clean up test users
        factory.cleanup()
```

#### Why Real Authentication?
- **Integration bugs**: Mocks hide real authentication flow issues
- **User experience**: Test what users actually experience
- **Security validation**: Verify auth tokens work correctly
- **Complete coverage**: Test JWT generation, validation, session management

### Browser Tests (`tests/web/`)
- **Purpose**: Test UI behavior and interactions
- **Speed**: Slow (10-60 seconds per test)
- **Dependencies**: Playwright, running web service
- **Example**: Chat interface functionality

```bash
# Requires browser dependencies
./scripts/pytest-for-claude.sh tests/web -v
```

## Development Workflow

### 1. Before Starting Development
```bash
# Ensure tests pass
./scripts/pytest-for-claude.sh tests/unit tests/integration -v

# Check specific area you'll work on
./scripts/pytest-for-claude.sh tests/integration/test_chat_api.py -v
```

### 2. During Development
```bash
# Run affected tests frequently
./scripts/pytest-for-claude.sh tests/unit/test_my_component.py -v

# Use test-driven development
# 1. Write failing test
# 2. Implement feature
# 3. Verify test passes
```

### 3. Before Committing
```bash
# Run all relevant tests
./scripts/pytest-for-claude.sh tests/unit tests/integration -v

# Check for regressions
./scripts/pytest-for-claude.sh tests/e2e/test_critical_paths.py -v

# Verify no test artifacts remain
docker compose exec db psql -U postgres -d gaia_test -c "SELECT COUNT(*) FROM users WHERE email LIKE '%test%';"
```

### 4. After Merging
```bash
# Full test suite
./scripts/pytest-for-claude.sh

# Monitor for flaky tests
./scripts/check-test-progress.sh
```

## CI/CD Integration

### GitHub Actions
Tests automatically run on:
- Pull requests
- Pushes to main
- Nightly schedules

### Local CI Simulation
```bash
# Run tests as CI would
docker compose down -v
docker compose up -d
./scripts/pytest-for-claude.sh --ci-mode
```

## Troubleshooting

### Common Issues

#### Tests Timeout in Claude Code
```bash
# ❌ Wrong: Direct pytest
pytest tests/  # Times out after 2 minutes

# ✅ Right: Async runner
./scripts/pytest-for-claude.sh tests/
```

#### Import Errors
```bash
# Ensure you're in the right directory
cd /path/to/gaia
export PYTHONPATH="${PYTHONPATH}:${PWD}"
```

#### Database Connection Errors
```bash
# Restart services
docker compose down
docker compose up -d

# Wait for services to be ready
sleep 10
```

#### Authentication Failures
```bash
# Check environment variables
grep SUPABASE .env

# For E2E tests, ensure service key is set
echo "SUPABASE_SERVICE_KEY=your-key" >> .env
```

### Debugging Failed Tests

**🚨 ALWAYS document findings in [APPEND-ONLY-TEST-FIXES-LOG.md](../../APPEND-ONLY-TEST-FIXES-LOG.md)**

1. **Run with verbose output**:
   ```bash
   ./scripts/pytest-for-claude.sh tests/failing_test.py -v -s
   ```

2. **Check logs**:
   ```bash
   # Test logs
   tail -f logs/tests/pytest/test-run-*.log
   
   # Service logs
   docker compose logs -f chat-service
   ```

3. **Run interactively**:
   ```bash
   # Drop into debugger on failure
   ./scripts/pytest-for-claude.sh tests/failing_test.py --pdb
   ```

4. **Isolate the test**:
   ```bash
   # Run just the failing test
   ./scripts/pytest-for-claude.sh tests/file.py::TestClass::test_method -v -s
   ```

5. **Document the fix**:
   - Root cause analysis in APPEND-ONLY-TEST-FIXES-LOG.md
   - Pattern recognition for similar future failures
   - Framework-specific gotchas discovered

### Performance Issues

1. **Run tests in parallel** (⚠️ See warning):
   ```bash
   ./scripts/pytest-for-claude.sh -n auto
   ```
   
   **WARNING**: While parallel execution is faster, it can cause test failures due to:
   - Resource conflicts (shared test users, database connections)
   - State pollution between tests
   - Timing issues with HTMX and WebSocket tests
   - See [TEST_INFRASTRUCTURE.md](TEST_INFRASTRUCTURE.md#️-critical-parallel-execution-issues) for details
   
   The default `pytest-for-claude.sh` runs tests sequentially to avoid these issues.

2. **Skip slow tests during development**:
   ```bash
   ./scripts/pytest-for-claude.sh -m "not slow"
   ```

3. **Profile test execution**:
   ```bash
   ./scripts/pytest-for-claude.sh --durations=10
   ```

## Contract Testing (Coming Soon)

Contract testing ensures that services can communicate correctly by validating API contracts between producers and consumers.

### Why Contract Testing?
- **Prevents Integration Failures**: Catch breaking changes before deployment
- **Faster Than E2E Tests**: Test service contracts in isolation
- **Clear Service Boundaries**: Documents expected API behavior
- **Independent Development**: Teams can work without full system

### Implementation Plan
```bash
# Future implementation
./scripts/run-contract-tests.sh --service gateway --consumer web
./scripts/generate-contracts.sh --from-openapi
```

### Contract Test Organization
```
tests/contracts/
├── gateway/
│   ├── chat-service.contract.json
│   └── auth-service.contract.json
├── web/
│   └── gateway.contract.json
└── shared/
    └── contract-schemas.json
```

## Performance Testing

Performance testing ensures the system meets speed and scalability requirements.

### Performance Test Strategy

**1. Baseline Establishment**
```bash
# Run baseline performance tests
./scripts/performance/baseline.sh --service chat --endpoint /v1/chat

# Expected baselines:
# - Chat response: < 3 seconds
# - Auth validation: < 100ms
# - Conversation load: < 500ms
```

**2. Load Testing Setup**
```bash
# Create load test script
cat > scripts/load-tests/chat-load.sh << 'EOF'
#!/bin/bash
# Run load tests externally to avoid Claude timeout
echo "⚠️ Warning: This will consume API quota"
echo "Running load test with k6..."

docker run --rm -v $(pwd)/tests/load:/scripts \
  grafana/k6 run /scripts/chat-load-test.js

# Collect results
./scripts/collect-load-results.sh
EOF
```

**3. Performance Monitoring**
```python
# tests/performance/test_response_times.py
import time
import pytest

@pytest.mark.performance
async def test_chat_response_time(client):
    """Ensure chat responses are under 3 seconds"""
    start = time.time()
    response = await client.post("/v1/chat", json={"message": "Hello"})
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 3.0, f"Response took {duration:.2f}s, expected < 3s"
```

**4. Regression Detection**
- Store performance baselines in `tests/performance/baselines.json`
- Compare current results against baselines
- Flag regressions > 20% automatically
- Track trends over time

### External Performance Testing
Due to Claude's 2-minute timeout, intensive performance tests should run externally:

```bash
# Trigger remote performance tests
./scripts/trigger-remote-perf-tests.sh --env staging --suite load

# Poll for results
./scripts/check-perf-results.sh --job-id $JOB_ID
```

## Test Data Management Best Practices

### Namespace Isolation
```python
# Use unique namespaces per test run
import uuid

class TestWithIsolation:
    @pytest.fixture
    def test_namespace(self):
        return f"test-{uuid.uuid4().hex[:8]}"
    
    async def test_isolated_data(self, test_namespace):
        # All test data uses namespace prefix
        user_email = f"{test_namespace}-user@test.local"
        conversation_id = f"{test_namespace}-conv-1"
```

### Cleanup Strategies
```python
# Automatic cleanup with fixtures
@pytest.fixture
async def test_data_cleanup(test_namespace):
    yield
    # Cleanup runs after test
    await cleanup_namespace_data(test_namespace)
```

## Testing Best Practices

### Naming Conventions
```python
# Test files: test_*.py or *_test.py
test_chat_service.py

# Test classes: Test<Component>
class TestChatService:
    pass

# Test methods: test_<behavior>_<condition>_<expected>
def test_send_message_with_empty_text_raises_error(self):
    pass

# Fixtures: descriptive names without "fixture" suffix
@pytest.fixture
def authenticated_user():  # Good
    pass
```

### Common Antipatterns to Avoid

#### 1. Testing Implementation Details
```python
# ❌ Bad: Testing private methods
def test_private_method(self):
    service = Service()
    result = service._calculate_internal_state()  # Don't test this

# ✅ Good: Test public interface
def test_service_behavior(self):
    service = Service()
    result = service.process_data(input_data)
    assert result.status == "success"
```

#### 2. Overusing Mocks
```python
# ❌ Bad: Mocking everything
@patch('app.database')
@patch('app.cache')
@patch('app.logger')
def test_with_too_many_mocks(mock_db, mock_cache, mock_logger):
    # You're not testing real behavior anymore

# ✅ Good: Mock only external dependencies
def test_with_real_components(self):
    # Use real database, mock only external APIs
    with patch('app.external_api.call'):
        result = service.process()
```

#### 3. Ignoring Test Failures
```python
# ❌ Bad: Changing test to match broken code
assert response.status_code in [200, 201, 404]  # Too permissive!

# ✅ Good: Fix the code to match test expectations
assert response.status_code == 201  # Precise expectation
```

### Mock Usage Guidelines by Test Type

#### Unit Tests - Mock External Dependencies
```python
@patch('app.external.openai_client')
def test_chat_logic(mock_openai):
    # Mock external API, test business logic
    mock_openai.complete.return_value = "Mocked response"
```

#### Integration Tests - Use Real Internal Services
```python
def test_service_integration():
    # Use real database, Redis, internal services
    # Only mock external APIs if needed
```

#### E2E Tests - No Mocks
```python
async def test_full_user_journey():
    # Everything must be real
    # Use TestUserFactory for real users
    # Test actual system behavior
```

### Load Testing Separation
Load tests should be separated from regular tests to avoid:
- API quota consumption
- Rate limiting issues
- Non-deterministic failures

```bash
# Load tests in separate directory
tests/load/
├── README.md
├── conftest.py
└── test_concurrent_requests.py

# Run explicitly with warnings
./scripts/run-load-tests.sh
```

## Test Consolidation

### All Tests Are Now in the pytest Suite

**🎯 Important**: We have consolidated all testing into the automated pytest suite. Individual test scripts in `scripts/` have been deprecated.

### Deprecated Test Scripts

The following test scripts have been migrated to pytest:

| Old Script | New Location | Description |
|------------|--------------|-------------|
| `test-gateway-endpoints.sh` | `tests/integration/gateway/test_gateway_auth_endpoints.py` | Gateway endpoint testing |
| `test_streaming_endpoint.py` | `tests/integration/chat/test_unified_streaming_format.py` | Streaming response tests |
| `test-intelligent-routing.sh` | `tests/integration/chat/test_intelligent_routing.py` | Routing logic tests |
| `test-mcp-agent-hot-loading.sh` | `tests/integration/chat/test_mcp_agent_hot_loading.py` | Hot loading performance |
| `test-kb-storage-performance.py` | `tests/performance/test_kb_storage_performance.py` | KB performance benchmarks |
| `test_llm_platform_compatibility.sh` | `tests/integration/compatibility/test_llm_platform.py` | Legacy API compatibility |

### Running Specific Test Categories

```bash
# Authentication tests
./scripts/pytest-for-claude.sh tests/integration/gateway/test_gateway_auth_endpoints.py -v

# Chat and streaming tests
./scripts/pytest-for-claude.sh tests/integration/chat/ -v

# Intelligent routing tests
./scripts/pytest-for-claude.sh tests/integration/chat/test_intelligent_routing.py -v

# Performance tests
./scripts/pytest-for-claude.sh tests/performance/ -v

# Compatibility tests
./scripts/pytest-for-claude.sh tests/integration/compatibility/ -v
```

### Why Consolidation?

1. **Single Source of Truth**: All tests in one place (`tests/` directory)
2. **Consistent Authentication**: All tests use the same auth fixtures
3. **Better CI/CD**: One command runs all tests
4. **Unified Coverage**: Single test coverage report
5. **Easier Maintenance**: One testing framework to maintain

### For Developers

If you're looking for a test script that used to be in `scripts/`, check the table above for its new location. All test functionality has been preserved or enhanced in the pytest suite.

## Additional Resources

- [TEST_INFRASTRUCTURE.md](TEST_INFRASTRUCTURE.md) - Technical details about test runners
- [CRITICAL_TESTING_PRINCIPLE_TESTS_DEFINE_TRUTH.md](CRITICAL_TESTING_PRINCIPLE_TESTS_DEFINE_TRUTH.md) - Core testing philosophy
- [TEST_CONSOLIDATION_PLAN.md](TEST_CONSOLIDATION_PLAN.md) - Details about test consolidation
- [Tester Agent](/.claude/agents/tester.md) - AI assistant for writing and debugging tests
- [Mobile Testing Guide](mobile-testing-guide.md) - Mobile-specific testing patterns
- [Security Testing Strategy](security-testing-strategy.md) - Security testing approaches

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

The testing procedures and organization described in this document have been verified against the current codebase.

-   **✅ Test Scripts:**
    *   **Claim:** The document refers to several test scripts, including `pytest-for-claude.sh`, `check-test-progress.sh`, and `setup-dev-environment.sh`.
    *   **Code Reference:** `scripts/` directory.
    *   **Verification:** This is **VERIFIED**. The key scripts for running and managing tests are present in the `scripts/` directory.

-   **✅ Test Organization:**
    *   **Claim:** The tests are organized into `unit`, `integration`, `e2e`, `performance`, and `web` directories.
    *   **Code Reference:** `tests/` directory.
    *   **Verification:** This is **VERIFIED**. The `tests/` directory follows this structure.

-   **✅ Test Fixtures:**
    *   **Claim:** Shared test utilities and fixtures are located in `tests/fixtures/`.
    *   **Code Reference:** `tests/fixtures/`.
    *   **Verification:** This is **VERIFIED**. The `tests/fixtures/` directory contains shared test helpers.

-   **⚠️ Test Consolidation:**
    *   **Claim:** All testing has been consolidated into the `pytest` suite, and individual test scripts in `scripts/` have been deprecated.
    *   **Verification:** This is **PARTIALLY VERIFIED**. While many tests have been migrated to the `pytest` suite, several standalone test scripts still exist in the `scripts/` directory (e.g., `test-gateway-endpoints.sh`, `test-mcp-agent-hot-loading.sh`). The consolidation is not yet complete.

**Overall Conclusion:** This document provides a mostly accurate guide to the testing philosophy and structure of the project. The main discrepancy is that the test consolidation effort is still in progress. Developers should be aware that both the `pytest` suite and some legacy test scripts are currently in use.

---

**Remember**: When in doubt, write a test! Tests are documentation that never goes out of date.