# E2E Test Findings and Recommendations



## Executive Summary

Investigation revealed that E2E test hanging was caused by authentication failures with hardcoded credentials. Tests using the proper `TestUserFactory` with real Supabase authentication work correctly.

## Key Findings

### 1. Root Cause of Hanging Tests

**Problem**: E2E tests were hanging at 18% completion
**Cause**: Tests using hardcoded credentials (`dev@gaia.local` / `testtest`) that don't exist in Supabase
**Impact**: Tests timeout waiting for navigation to `/chat` after failed login attempts

### 2. Working Test Infrastructure

The project has proper E2E test infrastructure with `TestUserFactory`:

```python
# tests/fixtures/test_auth.py
class TestUserFactory:
    """Creates test users with email pre-verified using Supabase service key."""
    
    def create_verified_test_user(self, email=None, password=None, role="user"):
        # Creates real Supabase user with email pre-verified
        # Tracks created users for cleanup
        
    def cleanup_all(self):
        # Deletes all test users created by this factory
```

### 3. E2E Test Results

#### ❌ Failing Tests (hardcoded credentials)
- `test_e2e_real_auth.py::test_real_login_flow` - Uses `dev@gaia.local`
- `test_e2e_real_auth.py::test_real_registration_flow` - Uses `dev@gaia.local`
- `test_e2e_real_auth.py::test_logout_flow` - Uses `dev@gaia.local`

#### ✅ Working Tests (TestUserFactory)
- `test_real_e2e_with_supabase.py::test_real_e2e_login_and_chat` - PASSED
- `test_real_e2e_with_supabase.py::test_concurrent_users` - PASSED
- `test_real_e2e_with_supabase.py::test_real_e2e_registration_and_login` - FAILED (email validation)

The registration test fails due to client-side email validation rejecting `@test.local` domain, not infrastructure issues.

## Recommendations

### 1. Fix Hardcoded Credential Tests

Update `test_e2e_real_auth.py` to use `TestUserFactory`:

```python
@pytest.fixture
async def test_user(test_user_factory):
    """Create a test user for E2E tests"""
    user = test_user_factory.create_verified_test_user()
    yield user
    test_user_factory.cleanup_test_user(user["user_id"])

async def test_real_login_flow(test_user):
    # Use test_user["email"] and test_user["password"]
```

### 2. Skip Tests Without Proper Setup

Add proper skip decorators:

```python
@pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_KEY"),
    reason="Requires SUPABASE_SERVICE_KEY for real user creation"
)
```

### 3. Use Sequential Execution for E2E Tests

As documented in test execution strategy:
- Run E2E tests with `-n 1` to prevent resource exhaustion
- Browser tests consume significant memory/CPU when run in parallel

### 4. Test Organization

Separate E2E tests into categories:
- **auth_e2e/** - Authentication flows (login, register, logout)
- **chat_e2e/** - Chat functionality with authenticated users
- **browser_e2e/** - General browser UI tests

## Current E2E Test Health

| Test File | Status | Issue | Fix Required |
|-----------|--------|-------|--------------|
| `test_bare_minimum.py` | ✅ PASS | None | None |
| `test_browser_registration.py` | ✅ PASS | None | None |
| `test_e2e_real_auth.py` | ❌ FAIL | Hardcoded credentials | Use TestUserFactory |
| `test_real_e2e_with_supabase.py` | ⚠️ 2/3 PASS | Email validation | Use valid test domain |
| `test_example_with_screenshot_cleanup.py` | ❌ HANG | Unknown | Investigate timeouts |

## Implementation Priority

1. **Immediate**: Update `test_e2e_real_auth.py` to use TestUserFactory
2. **Short-term**: Fix email validation in registration tests
3. **Medium-term**: Investigate screenshot test hanging issues
4. **Long-term**: Consolidate duplicate E2E test patterns

## Test User Management Best Practices

1. **Always use TestUserFactory** for creating test users
2. **Cleanup in fixtures** using yield pattern
3. **Unique emails** using UUID: `f"test-{uuid.uuid4().hex[:8]}@test.local"`
4. **Service key required** for bypassing email verification
5. **Track all users** for guaranteed cleanup

## Conclusion

The E2E test infrastructure is fundamentally sound. Issues stem from:
1. Some tests using outdated hardcoded credentials
2. Resource exhaustion from parallel browser execution
3. Email validation on certain test domains

With the fixes outlined above, E2E tests should achieve >90% pass rate.