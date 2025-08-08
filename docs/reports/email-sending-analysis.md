# Email Sending Analysis in Tests

## Summary
We're creating approximately **43+ test users** programmatically and attempting **28+ UI registrations** in our test suite, which could be sending **70+ confirmation emails** to Supabase.

## Email Sending Sources

### 1. TestUserFactory (Fixed ✅)
- **Location**: `tests/fixtures/test_auth.py`
- **Fix Applied**: Added `send_email: False` to `create_verified_test_user()`
- **Impact**: ~43 test user creations no longer send emails

### 2. Direct UI Registration (Still Sending Emails ❌)
- **Location**: Browser tests submitting to `/register` endpoint
- **Problem**: The auth service uses `supabase.auth.sign_up()` which ALWAYS sends emails
- **Files affected**:
  - `tests/e2e/test_browser_registration.py` - Submits registration form
  - `tests/e2e/test_e2e_real_auth.py` - Has registration flow tests
  - `tests/e2e/test_real_e2e_with_supabase.py` - Creates test users via UI
  - Multiple other E2E tests that fill and submit registration forms

### 3. Auth Service Registration Endpoint (Root Cause)
- **Location**: `app/services/auth/main.py::register_user()`
- **Code**:
  ```python
  user = supabase.auth.sign_up({
      "email": request.email,
      "password": request.password
  })
  ```
- **Problem**: The standard `sign_up()` method doesn't support `send_email` parameter
- **Solution Options**:
  1. Use admin API for test registrations
  2. Add a test mode flag to skip real registration
  3. Mock the registration endpoint in tests

## Recommendations

### Immediate Fix
Add environment detection to the auth service to use admin API for test environments:

```python
async def register_user(request: UserRegistrationRequest):
    supabase = get_supabase_client()
    
    # Use admin API in test environment to prevent emails
    if os.getenv("TESTING", "false").lower() == "true":
        response = supabase.auth.admin.create_user({
            "email": request.email,
            "password": request.password,
            "email_confirm": True,
            "send_email": False
        })
    else:
        # Production path - sends emails
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })
```

### Test Suite Changes
1. Set `TESTING=true` environment variable in test containers
2. Update browser tests to use TestUserFactory instead of UI registration
3. Mock registration endpoints in unit tests

## Impact
- Current: ~70+ emails per full test run
- After fix: 0 emails per test run
- Prevents Supabase email restrictions and bounces