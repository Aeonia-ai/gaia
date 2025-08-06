# Testing Philosophy

## 🎯 Core Principle: Automated Tests Over Manual Scripts

**Always use automated tests instead of manual curl commands or ad-hoc scripts.** This isn't just about convenience - it's about building reliable, repeatable validation that catches regressions and integrates with CI/CD.

## Why Automated Tests?

### 1. **Reproducibility & Consistency**
```bash
# ❌ Bad: Manual curl that gets lost in terminal history
curl -H "X-API-Key: $API_KEY" http://localhost:8666/api/v1/providers

# ✅ Better: Test script (legacy approach)
./scripts/test.sh --local providers

# 🚀 Best: Automated tests with validation
./scripts/pytest-for-claude.sh tests/test_provider_model_endpoints.py -v
```

Automated tests provide:
- **Identical results** every time (no human interpretation)
- **Clear pass/fail status** with specific error messages
- **CI/CD integration** for continuous validation
- **Regression prevention** through consistent checking

### 2. **Environment Handling**
Automated tests automatically:
- Run in **Docker environment** for consistency
- Use **proper service URLs** (Docker internal networking)
- Handle **authentication** through standardized fixtures
- Provide **environment-specific testing** (local, dev, staging, prod)

### 3. **Knowledge Capture & Validation**
Each automated test captures and validates:
- **Correct endpoint URLs** and request formats
- **Required authentication** and headers
- **Expected response structure** (v0.2 vs v1 formats)
- **Success and failure scenarios**
- **Business logic validation** (not just connectivity)

### 4. **Evolution and Improvement**
When you discover a new test case:
1. **Don't just run curl** - Add it to the automated test suite
2. **Found a bug?** - Write an automated test that would have caught it
3. **Fixed an issue?** - Update tests to verify the fix permanently
4. **New feature?** - Add comprehensive test coverage from the start

## Automated Test Architecture

### Test Runner (New Approach)
```bash
./scripts/pytest-for-claude.sh    # Async pytest runner (avoids timeouts)
./scripts/pytest-for-claude.sh tests/integration  # Run specific category
./scripts/check-test-progress.sh  # Check test progress
```

### Test Files (pytest-based)
```
tests/
├── test_working_endpoints.py           # Core functionality (11 tests)
├── test_api_endpoints_comprehensive.py # Full coverage (9 tests)
├── test_v02_chat_api.py                # v0.2 API detailed (14 tests)
├── test_provider_model_endpoints.py    # Provider/model (11 tests)
├── test_kb_endpoints.py                # Knowledge Base (12 tests)
└── test_comprehensive_suite.py         # Integration (8 tests)
```

### Legacy Scripts (Deprecated)
```
scripts/
├── test.sh                    # Legacy manual test runner → Use pytest-for-claude.sh
├── test-comprehensive.sh      # Legacy comprehensive → Use pytest-for-claude.sh
├── test-kb-operations.sh      # Legacy KB tests → Use pytest-for-claude.sh
├── manage-users.sh           # User management (still active)
└── layout-check.sh           # UI validation (still active)
```

## Migration to Automated Testing

### Quick Migration Guide
```bash
# Old manual approach
./scripts/test.sh --local health
./scripts/test.sh --local chat "test message"
./scripts/test.sh --local providers

# New automated approach  
./scripts/pytest-for-claude.sh tests/test_working_endpoints.py::test_health -v
./scripts/pytest-for-claude.sh tests/test_v02_chat_api.py -v
./scripts/pytest-for-claude.sh tests/test_provider_model_endpoints.py -v
```

### Benefits of Migration
- **50+ automated tests** vs manual script interpretation
- **Consistent results** with clear pass/fail status
- **CI/CD integration** for continuous validation
- **Response format validation** (v0.2 vs v1 compatibility)
- **Regression prevention** through automated checking
- **Faster feedback** with targeted test execution

### Complete Test Coverage
| Category | Tests | Purpose |
|----------|-------|---------|
| Health & Status | 5 tests | System health, service status |
| Chat & Communication | 25 tests | v0.2/v1 endpoints, conversation flow |
| Knowledge Base | 12 tests | KB health, search, integration |
| Providers & Models | 11 tests | Provider endpoints, model info |
| Authentication | 8 tests | Security, API key validation |
| Integration | 8 tests | End-to-end, performance monitoring |

## Best Practices

### 1. **Use Automated Tests First**
When adding new functionality:
```bash
# ❌ Old approach: Manual test scripts
echo "Testing new feature..." >> test-kb-operations.sh

# ✅ New approach: Add to automated test suite
# Add test methods to appropriate test file in tests/
# Run: ./scripts/pytest-for-claude.sh tests/[test_file.py] -v
```

### 2. **Follow Test Patterns**
```python
# Use consistent pytest patterns
async def test_new_feature(self, gateway_url, headers):
    """Test description of what this validates."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{gateway_url}/api/endpoint",
            headers=headers,
            json={"test": "data"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
        
        logger.info(f"Test result: {data}")
```

### 3. **Comprehensive Test Coverage**
Each test should validate:
- **Functional correctness** (does it work?)
- **Response format** (correct structure?)
- **Error handling** (fails gracefully?)
- **Authentication** (properly secured?)
- **Business logic** (meets requirements?)

### 4. **Make Tests Discoverable**
```bash
# ❌ Bad: Hidden manual testing
curl -X POST $SECRET_ENDPOINT -d @complex_payload.json

# ✅ Good: Automated test with clear purpose
./scripts/pytest-for-claude.sh --help    # Shows pytest help
./scripts/pytest-for-claude.sh tests/test_webhooks.py -v  # Clear test file
```

## Common Patterns

### Testing Authentication
```bash
# Use test script functions
./scripts/test.sh --local auth

# Not manual curl
curl -H "X-API-Key: ..." 
```

### Testing New Endpoints
```bash
# 1. Add to comprehensive test
vim scripts/test-comprehensive.sh
# Add: test_endpoint "GET" "/api/v1/new-endpoint" "" "New feature test"

# 2. Run to verify
./scripts/test-comprehensive.sh
```

### Debugging Issues
```bash
# 1. Reproduce with test script
./scripts/test-kb-operations.sh | grep -A10 "failing test"

# 2. Fix the issue

# 3. Verify fix with same script
./scripts/test-kb-operations.sh
```

## Anti-Patterns to Avoid

### ❌ One-off Curl Commands
```bash
# This knowledge is lost after you close the terminal
curl -X POST http://localhost:8666/api/v0.2/kb/search \
  -H "X-API-Key: abc123" \
  -d '{"message": "test"}'
```

### ❌ Hardcoded Values
```bash
# API keys and URLs should come from environment
API_KEY="hardcoded-key-bad"
curl "http://hardcoded-url-bad.com/api"
```

### ❌ No Error Handling
```bash
# What happens when this fails?
curl $URL | jq '.result'
```

### ✅ Instead: Robust Test Scripts
```bash
# Reusable, environment-aware, error-handling test
./scripts/test.sh --local kb-search "test query"
```

## Adding New Tests

When you need to test something new:

1. **Check if a test script exists**
   ```bash
   ls scripts/test-*.sh
   ```

2. **Extend existing script if appropriate**
   ```bash
   # Add to test-kb-operations.sh for KB features
   # Add to test-comprehensive.sh for general features
   ```

3. **Create new script for new domains**
   ```bash
   # New feature area? New test script
   cp scripts/test-template.sh scripts/test-newfeature.sh
   ```

4. **Document what you're testing**
   ```bash
   # Always include comments explaining the test
   # Test: Verify rate limiting works correctly (max 100 req/min)
   test_endpoint "GET" "/api/v1/rate-limit-test" "" "Rate limit verification"
   ```

## E2E Testing: No Mocks Policy

### Real Authentication Only
E2E tests must use real Supabase authentication - **NO MOCKS ALLOWED!**

```python
# ❌ WRONG: Mock authentication in E2E tests
await page.route("**/auth/login", mock_response)

# ✅ RIGHT: Real authentication with TestUserFactory
factory = TestUserFactory()
user = factory.create_verified_test_user(
    email=f"e2e-{uuid.uuid4().hex[:8]}@test.local",
    password="TestPassword123!"
)
# Perform real login through UI
```

### E2E Test Requirements
1. **Valid SUPABASE_SERVICE_KEY** in .env for creating test users
2. **Real JWT tokens** from actual Supabase login
3. **TestUserFactory** for consistent test user creation
4. **Complete flow validation** - no shortcuts or mocks
5. **Cleanup** - Always clean up test users after tests

### Why No Mocks in E2E?
- **E2E means End-to-End** - The entire flow must be real
- **Authentication is critical** - Mocking it defeats the purpose
- **Real bugs need real tests** - Mocks hide integration issues
- **User experience validation** - Users don't use mocks

## Resource Management in Integration Tests

### 🚨 Critical Learning: Test Design Can Break Services
**August 2025 Discovery:** 28 failing integration tests appeared to be "service performance issues" but were actually **resource exhaustion from bad test design**.

**The Problem:** Each test was creating/deleting Supabase users, causing:
- 200+ concurrent external API calls (8 workers × 28 tests)
- Database connection pool exhaustion  
- HTTP client resource leaks
- Services hanging completely (not slow responses)

**The Solution:** Session-scoped shared resources and sequential execution for resource-intensive tests.

```python
# ❌ BAD: Each test creates external resources
async def test_auth(self, user_factory):
    user = user_factory.create_verified_test_user()  # Supabase API call

# ✅ GOOD: Shared session-scoped resources  
@pytest.fixture(scope="session")
def shared_test_user():
    # Create ONCE per test session, not per test
```

**Results:** 89% reduction in test failures, 75% faster execution time.

**→ See [Integration Test Resource Management](integration-test-resource-management.md) for complete details**

### Integration Test Execution Strategy

```bash
# Resource-intensive tests (external APIs, databases)
./scripts/pytest-for-claude.sh tests/integration/test_supabase_auth.py -n 1  # Sequential

# Unit tests (fast, isolated)
./scripts/pytest-for-claude.sh tests/unit/ -n auto  # Parallel

# Mixed execution with proper resource management
python run_sequential_tests.py
```

## Async Test Execution

### Avoiding Claude Code Timeouts
Claude Code's Bash tool has a 2-minute timeout. Our test suite takes longer, so we use async execution:

```bash
# ❌ WRONG: Direct pytest (will timeout)
pytest tests/ -v

# ✅ RIGHT: Async execution
./scripts/pytest-for-claude.sh tests/ -v
./scripts/check-test-progress.sh  # Monitor progress
```

### How It Works
1. **pytest-for-claude.sh** starts tests in background
2. Output redirected to timestamped log file
3. **check-test-progress.sh** monitors test progress
4. Tests complete even if Claude Code times out

### Diagnosing Test Issues
```bash
# If tests timeout, check for resource exhaustion first:
./scripts/pytest-for-claude.sh tests/integration/failing_test.py -n 1  # Try sequential

# If passes individually but fails in parallel = resource exhaustion  
# If fails in both = actual service issue
```

## The Payoff

Following this philosophy means:
- **No lost knowledge** - Every test case is preserved
- **Faster debugging** - Reproduce issues instantly
- **Better onboarding** - New developers can understand the system
- **Regression prevention** - Old bugs don't come back
- **Living documentation** - Tests show how the system actually works
- **Real confidence** - E2E tests prove the system actually works

Remember: **If you're typing curl, you should be updating a test script instead!**