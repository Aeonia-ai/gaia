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

## Quick Start

### Prerequisites
```bash
# One-time setup
./scripts/setup-dev-environment.sh

# Ensure services are running
docker compose up -d
```

### 🚨 CRITICAL: Append-Only Test Fixes Log
**When working on test failures, ALWAYS update [APPEND-ONLY-TEST-FIXES-LOG.md](../../APPEND-ONLY-TEST-FIXES-LOG.md)**

This log captures institutional knowledge about:
- Test failure patterns and root causes
- Successful fixes and their reasoning
- Framework-specific gotchas (FastHTML, HTMX, Playwright)
- Testing best practices learned through experience

**Format**: Append entries chronologically - NEVER overwrite existing content.

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
│   ├── test_chat_api.py
│   ├── test_personas_api.py
│   └── test_kb_endpoints.py
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

## Additional Resources

- [TESTING_BEST_PRACTICES.md](TESTING_BEST_PRACTICES.md) - Detailed patterns and practices
- [TEST_INFRASTRUCTURE.md](TEST_INFRASTRUCTURE.md) - Technical details about test runners
- [Tester Agent](/docs/agents/tester.md) - AI assistant for writing and debugging tests
- [E2E Real Auth Testing](e2e-real-auth-testing.md) - Details on testing with real authentication

---

**Remember**: When in doubt, write a test! Tests are documentation that never goes out of date.