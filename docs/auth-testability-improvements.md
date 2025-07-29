# Authentication Testability Improvements

## Current Issues

1. **HTMX vs Regular Redirects**: The login endpoint returns 303 redirects, but HTMX expects `HX-Redirect` headers
2. **Dev Login Inconsistency**: Dev login exists but doesn't work well with HTMX
3. **No Test Mode**: No clean way to inject test sessions for browser tests
4. **Tight Coupling**: Authentication is tightly coupled to Supabase, making testing harder

## Recommended Fixes (Priority Order)

### 1. Fix HTMX Response Headers (Quick Win)

**File**: `/app/services/web/routes/auth.py`

```python
@app.post("/auth/login")
async def login(request):
    """Handle login form submission"""
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")
    
    # Check if this is an HTMX request
    is_htmx = request.headers.get("hx-request") == "true"
    
    # ... authentication logic ...
    
    # After successful authentication:
    if is_htmx:
        # HTMX expects HX-Redirect header
        return HTMLResponse(
            content="",
            status_code=200,
            headers={"HX-Redirect": "/chat"}
        )
    else:
        # Regular form submission
        return RedirectResponse(url="/chat", status_code=303)
```

### 2. Add Test Mode Support (Better Solution)

**Environment Variable**: `TEST_MODE=true`

```python
@app.on_event("startup")
async def setup_test_mode():
    """Setup test mode if enabled"""
    if os.getenv("TEST_MODE") == "true":
        logger.warning("TEST MODE ENABLED - Authentication bypassed for test users")

@app.post("/auth/test-login")
async def test_login(request):
    """Test login endpoint for browser tests"""
    if os.getenv("TEST_MODE") != "true":
        return gaia_error_message("Test mode not enabled")
    
    form_data = await request.form()
    email = form_data.get("email")
    
    # Any email ending with @test.local is allowed in test mode
    if email and email.endswith("@test.local"):
        request.session["jwt_token"] = f"test-token-{email}"
        request.session["user"] = {
            "id": f"test-{email}",
            "email": email,
            "name": f"Test User ({email})"
        }
        
        if request.headers.get("hx-request") == "true":
            return HTMLResponse("", headers={"HX-Redirect": "/chat"})
        else:
            return RedirectResponse(url="/chat", status_code=303)
    
    return gaia_error_message("Invalid test credentials")
```

### 3. Session Injection Middleware (Best for Testing)

```python
from starlette.middleware.base import BaseHTTPMiddleware

class TestSessionMiddleware(BaseHTTPMiddleware):
    """Middleware to inject test sessions in test mode"""
    
    async def dispatch(self, request, call_next):
        if os.getenv("TEST_MODE") == "true":
            # Check for test session header
            test_session = request.headers.get("X-Test-Session")
            if test_session:
                try:
                    session_data = json.loads(base64.b64decode(test_session))
                    request.session.update(session_data)
                except:
                    pass
        
        response = await call_next(request)
        return response

# Add to app startup
if os.getenv("TEST_MODE") == "true":
    app.add_middleware(TestSessionMiddleware)
```

### 4. Remove Dev Login (Security)

The current dev login with hardcoded credentials should be removed:
- Security risk if accidentally deployed
- Confusing for other developers
- Not properly integrated with HTMX

Replace with proper test mode that's explicitly enabled.

## Benefits of These Changes

1. **Easier Testing**: Browser tests can use simple mocks or test endpoints
2. **Better Security**: No hardcoded credentials in production code
3. **HTMX Compatibility**: Proper support for HTMX authentication flows
4. **Cleaner Tests**: Tests don't need complex session state tracking
5. **CI/CD Friendly**: Test mode can be enabled in CI environments

## Implementation Priority

1. **Fix HTMX headers** (1 hour) - Immediate improvement for all HTMX forms
2. **Add test mode** (2 hours) - Clean testing solution
3. **Remove dev login** (30 mins) - Security improvement
4. **Add session middleware** (2 hours) - Advanced testing capabilities

## Example Test After Fixes

```python
async def test_login_with_test_mode():
    """Simple login test with test mode enabled"""
    # No complex mocking needed!
    await page.goto(f'{WEB_SERVICE_URL}/login')
    await page.fill('input[name="email"]', 'test@test.local')
    await page.fill('input[name="password"]', 'any-password')
    await page.click('button[type="submit"]')
    
    # Just works!
    await page.wait_for_url('**/chat')
    assert page.url.endswith('/chat')
```

## Environment Configuration

```bash
# .env.test
TEST_MODE=true
DEBUG=false  # Test mode works even without debug

# docker-compose.test.yml
services:
  web-service:
    environment:
      - TEST_MODE=true
```