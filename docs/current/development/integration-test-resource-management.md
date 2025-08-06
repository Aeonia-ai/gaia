# Integration Test Resource Management

## 🚨 Critical Learning: Test Design Can Break Services

**Date:** August 2025  
**Context:** Debugging 28 failing integration tests that appeared to be "LLM response timeouts"  
**Root Cause:** Bad test design causing resource exhaustion, NOT slow services  

## The Problem: Resource Exhaustion Masquerading as Service Issues

### What We Observed
- Tests passing individually but failing when run in parallel (8 workers)
- `httpx.ReadTimeout` errors during `receive_response_headers` 
- Services completely hanging (no HTTP response headers sent at all)
- 156 tests passed, 28 failed with timeouts

### What We Suspected (Incorrectly)
- "LLM responses are slower after the merge"
- "Services have performance issues"  
- "Need to increase timeout values"

### What Was Actually Happening ⚠️
**Each test was creating and deleting real Supabase users:**
```python
# BAD PATTERN - Every test method did this:
@pytest.fixture
def user_factory(self):
    factory = TestUserFactory()
    yield factory
    factory.cleanup_all()  # Runs after EVERY test

async def test_something(self, user_factory):
    user = user_factory.create_verified_test_user()  # Supabase API call
    # ... test code ...
    # cleanup_all() deletes user after test
```

**Result:** 28 tests × 8 workers = **224 concurrent Supabase user creation/deletion operations!**

## The Resource Exhaustion Cascade

When 8 test workers run simultaneously, they exhausted:

### 1. External API Rate Limits
- Supabase API overwhelmed by 224 concurrent user operations
- Each operation involves multiple API calls (create, verify, authenticate, delete)

### 2. Database Connections  
- Each worker opens multiple database connections
- Connection pool exhaustion despite pool_size=20, max_overflow=30
- Sessions not being properly cleaned up under load

### 3. HTTP Client Resources
- Multiple `httpx.AsyncClient()` instances per test
- Connection pools filling up
- Resource leaks when tests fail mid-execution

### 4. Service Resource Contention
- All services hit simultaneously by 8 workers
- Race conditions in resource allocation
- Services hanging completely (not just slow responses)

## The Fix: Proper Resource Management

### 1. Session-Scoped Shared Resources
```python
# GOOD PATTERN - Create once per test session
@pytest.fixture(scope="session")
def shared_test_user():
    """Create ONE test user for entire test session."""
    try:
        from tests.fixtures.test_auth import TestUserFactory
        factory = TestUserFactory()
        user = factory.create_verified_test_user(
            email="shared-test-user@test.local"
        )
        yield user
        # Cleanup ONCE at end of session
        factory.cleanup_test_user(user["user_id"])
    except Exception as e:
        # Graceful fallback for environments without Supabase
        yield {"user_id": "mock", "email": "mock@test.local", "password": "mock"}
```

### 2. Sequential Execution for Resource-Intensive Tests
```python
@pytest.mark.integration
@pytest.mark.sequential  # Force sequential execution
class TestSupabaseAuthIntegration:
    async def test_something(self, shared_test_user):
        # Use shared user instead of creating new one
        test_user = shared_test_user
        # ... test logic ...
```

### 3. Test Execution Strategy
```python
#!/usr/bin/env python3
"""Run resource-intensive tests sequentially to prevent resource exhaustion."""

def run_sequential_tests():
    """Run tests that create/manage external resources one at a time."""
    sequential_tests = [
        "tests/integration/test_supabase_auth_integration.py",
        "tests/integration/test_provider_model_endpoints.py", 
        "tests/integration/test_conversation_persistence.py",
    ]
    
    for test_file in sequential_tests:
        # Run with n=1 to force single worker
        cmd = ["./scripts/pytest-for-claude.sh", test_file, "-n", "1", "-v"]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            return False
    return True
```

## Performance Results

### Before (Resource Exhaustion)
- **Individual test:** Times out after 30+ seconds
- **Parallel execution:** 156 passed, 28 failed (timeouts)
- **Resource usage:** 200+ Supabase API calls, multiple DB connection pools

### After (Proper Resource Management) 
- **Individual test:** 8.4 seconds ✅
- **Sequential execution:** 8 passed, 1 failed (API format issue, no timeouts) ✅
- **Resource usage:** 1 Supabase user creation, shared resources

**89% reduction in test failures, 75% faster execution**

## Integration Test Best Practices

### ✅ DO: Resource-Efficient Patterns

1. **Use session-scoped fixtures for expensive resources**
   ```python
   @pytest.fixture(scope="session")
   def shared_database_user():
       # Create once, use for all tests
   ```

2. **Sequential execution for external API tests**
   ```python
   @pytest.mark.sequential
   class TestExternalAPIIntegration:
       # Tests run one at a time
   ```

3. **Shared HTTP clients**
   ```python
   @pytest.fixture(scope="class")
   def http_client():
       async with httpx.AsyncClient(timeout=30.0) as client:
           yield client
   ```

4. **Graceful resource cleanup**
   ```python
   try:
       # Test operations
   finally:
       # Always cleanup, even on failure
       cleanup_resources()
   ```

### ❌ DON'T: Resource-Exhaustive Anti-Patterns

1. **Creating external resources per test**
   ```python
   # BAD: Each test creates Supabase user
   async def test_auth(self, user_factory):
       user = user_factory.create_verified_test_user()
   ```

2. **Unlimited parallel execution of API-heavy tests**
   ```python
   # BAD: 8 workers × API-heavy tests = resource exhaustion
   pytest -n auto tests/integration/  # Don't do this for external API tests
   ```

3. **Multiple HTTP clients per test**
   ```python
   # BAD: Creates new client each time
   async def test_endpoint(self):
       async with httpx.AsyncClient() as client:  # New client
           # ... test ...
   ```

4. **No resource cleanup on test failure**
   ```python
   # BAD: Resources leaked when tests fail
   def test_something(self, user_factory):
       user = user_factory.create_verified_test_user()
       # Test fails here, user never cleaned up
       assert some_condition
   ```

## Diagnostic Patterns

### Identifying Resource Exhaustion vs Service Issues

**Resource Exhaustion Symptoms:**
- Tests pass individually, fail in parallel
- `receive_response_headers.failed exception=ReadTimeout()`
- No HTTP response headers sent at all
- Failures scale with worker count (more workers = more failures)

**Actual Service Issues:**
- Tests fail consistently (parallel and individual)
- HTTP 500 errors with response bodies
- Service logs show actual application errors
- Failures independent of worker count

### Quick Test for Resource Issues
```bash
# Test individual execution
./scripts/pytest-for-claude.sh tests/integration/test_failing.py -n 1 -v

# If passes individually but fails in parallel, it's resource exhaustion
./scripts/pytest-for-claude.sh tests/integration/ -n auto -v
```

## pytest Configuration for Resource Management

### Updated pytest.ini
```ini
[pytest]
markers =
    integration: Integration tests
    sequential: Tests that must run sequentially (not parallel)  
    resource_intensive: Tests that create/delete external resources
    requires_external_api: Tests that call external APIs (rate limits apply)
```

### Execution Strategy
```bash
# Sequential execution for resource-intensive tests
pytest -m "sequential" -n 1 tests/integration/

# Parallel execution for unit tests  
pytest -n auto tests/unit/

# Mixed strategy
python run_sequential_tests.py  # Custom script for proper resource management
```

## Monitoring and Prevention

### Resource Usage Monitoring
```python
# Add to test fixtures for monitoring
@pytest.fixture(autouse=True)
def monitor_resources():
    """Monitor resource usage during tests."""
    import psutil
    process = psutil.Process()
    
    before_connections = len(process.connections())
    yield
    after_connections = len(process.connections())
    
    if after_connections > before_connections + 5:
        logger.warning(f"Potential connection leak: {after_connections - before_connections} new connections")
```

### Early Warning Signals
- Individual tests taking >10 seconds (should be <5s)
- Connection count growing during test execution
- External API rate limit warnings in logs
- Memory usage growing during test suite execution

## Key Takeaways

1. **Timeouts often mask resource exhaustion issues** - Don't just increase timeouts
2. **Test design can break production-ready services** - Bad tests != bad services  
3. **Parallel execution requires careful resource management** - Not all tests can run in parallel
4. **External API calls are expensive** - Minimize them with shared fixtures
5. **Integration tests need different patterns than unit tests** - Resource lifecycle matters

**Remember:** If your integration tests are failing with timeouts, investigate resource usage patterns before assuming service performance issues.