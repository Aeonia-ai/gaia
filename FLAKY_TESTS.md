# Flaky Test Analysis

## Permanently Skipped Tests (Need Removal/Update)

### 1. test_working_endpoints.py
```python
@pytest.mark.skip(reason="Chat status endpoint deprecated - system uses conversation-based storage")
async def test_v1_chat_status(...)

@pytest.mark.skip(reason="Clear history endpoint deprecated - was scaffolding for persona development")  
async def test_clear_v1_chat_history(...)
```
**Action**: Remove these tests as they test deprecated functionality

### 2. test_authenticated_browser.py
```python
@pytest.mark.skip(reason="Requires TestUserFactory import fix")
async def test_authenticated_browser_session(...)
```
**Action**: Fix the import or remove if redundant

## Conditionally Skipped Tests (Environment-Dependent)

### Browser Tests (Skip when RUN_BROWSER_TESTS != "true")
- test_auth_integration.py
- test_chat_browser.py
- test_chat_browser_auth.py
- test_real_e2e_with_supabase.py
- test_real_auth_browser.py
- test_manual_auth_browser.py

**Pattern**:
```python
@pytest.mark.skipif(
    os.getenv("RUN_BROWSER_TESTS") != "true",
    reason="Browser tests disabled"
)
```

### Layout Tests (Skip when utilities unavailable)
- test_layout_integrity.py

**Pattern**:
```python
@pytest.mark.skipif(not LAYOUT_UTILS_AVAILABLE, reason="Layout isolation utilities not available")
```

## Known Flaky Tests (Intermittent Failures)

### 1. High Flakiness 🔴

#### test_comprehensive_suite.py::TestSystemIntegration::test_end_to_end_conversation
**Issues**:
- Context validation fails intermittently
- Timing issues with conversation flow
- AI responses vary, breaking assertions

**Fix**:
```python
@pytest.mark.flaky(reruns=3, reruns_delay=2)
async def test_end_to_end_conversation(...):
    # More flexible assertions
    assert any(term in response.lower() for term in ["alex", "don't know", "no access"])
```

#### test_integration.py::test_kb_chat_integration
**Issues**:
- KB service not ready when test runs
- Git sync timing issues
- File system race conditions

**Fix**:
```python
# Add proper wait condition
async def wait_for_kb_ready(kb_url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = await client.get(f"{kb_url}/health")
            if response.json()["status"] == "healthy":
                return True
        except:
            pass
        await asyncio.sleep(1)
    return False
```

### 2. Medium Flakiness ⚠️

#### test_api_endpoints_comprehensive.py::TestComprehensiveAPIEndpoints
**Issues**:
- Service health checks report "degraded" intermittently
- Model endpoint timeouts
- Provider availability varies

**Fix**:
- Add retry logic for health checks
- Mock external provider calls
- Increase timeouts for model operations

#### test_provider_model_endpoints.py
**Issues**:
- External API rate limits
- Network timeouts
- Provider service availability

**Fix**:
- Cache provider responses
- Add retry with exponential backoff
- Mock for unit test mode

### 3. Low/Sporadic Flakiness 🟡

#### Browser Tests (all)
**Issues**:
- Element not ready for interaction
- Page load timing
- JavaScript execution delays

**Fix**:
```python
# Better wait strategies
await page.wait_for_selector("#element", state="visible")
await page.wait_for_load_state("networkidle")
```

## Timeout-Related Flakiness

### Current Timeout Issues:
1. Default 30s timeout insufficient for:
   - Multi-agent orchestration tests
   - KB search with large repos
   - Complex chat conversations

2. No timeout configuration:
   ```python
   # Current (hardcoded)
   async with httpx.AsyncClient(timeout=30.0) as client:
   
   # Recommended (configurable)
   timeout = float(os.getenv("TEST_TIMEOUT", "30"))
   async with httpx.AsyncClient(timeout=timeout) as client:
   ```

## Recommendations for Immediate Action

### 1. Add flaky markers to known flaky tests:
```python
# Add to conftest.py or test file
pytest_plugins = ["pytest-rerunfailures"]
```

### 2. Create flaky test quarantine:
```python
# tests/quarantine/README.md
# Tests moved here are flaky and need fixing before returning to main suite
```

### 3. Implement standard retry decorator:
```python
# tests/shared/retry.py
def retry_flaky_test(retries=3, delay=2):
    def decorator(test_func):
        @pytest.mark.flaky(reruns=retries, reruns_delay=delay)
        @functools.wraps(test_func)
        async def wrapper(*args, **kwargs):
            return await test_func(*args, **kwargs)
        return wrapper
    return decorator
```

### 4. Add flaky test monitoring:
```bash
# Track flaky test occurrences
pytest --report-log=test-results.json
# Parse results to identify flaky patterns
```

## Priority Order for Fixes

1. **Remove permanently skipped tests** (2 tests)
2. **Fix high flakiness tests** (2-3 tests)  
3. **Add retry logic to medium flaky tests** (5-10 tests)
4. **Standardize timeouts** (all tests)
5. **Improve browser test stability** (27 test files)