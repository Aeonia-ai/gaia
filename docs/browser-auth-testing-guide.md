# Browser Authentication Testing Guide

This guide explains different approaches for testing authenticated flows in browser tests using Playwright.

## Authentication Testing Strategies

### 1. Mock Authentication (Fastest, Most Reliable)

**When to use**: Unit tests, fast feedback loops, CI/CD pipelines

```python
@pytest.mark.asyncio
async def test_authenticated_chat_with_mock(page):
    """Test chat interface with mocked authentication"""
    # Setup auth mock before navigation
    await page.route("**/auth/login", lambda route: route.fulfill(
        status=303,
        headers={"Location": "/chat"},
        body=""
    ))
    
    # Perform login
    await page.goto("/login")
    await page.fill('input[name="email"]', 'test@test.local')
    await page.fill('input[name="password"]', 'test-password')
    await page.click('button[type="submit"]')
    
    # Wait for chat page
    await page.wait_for_url("**/chat")
    
    # Now test authenticated features
    assert await page.query_selector("#chat-form")
```

### 2. Real Authentication with Test Users (Integration Testing)

**When to use**: Integration tests, end-to-end flows, verifying real auth behavior

```python
from tests.fixtures.test_auth import TestUserFactory

@pytest.fixture
async def real_test_user():
    """Create a real test user in Supabase"""
    factory = TestUserFactory()
    user = factory.create_verified_test_user(
        email=f"test-{uuid.uuid4()}@test.local",
        password="Test123!@#"
    )
    yield user
    # Cleanup
    factory.cleanup()

@pytest.mark.asyncio
async def test_real_authentication_flow(page, real_test_user):
    """Test with real Supabase authentication"""
    await page.goto("/login")
    await page.fill('input[name="email"]', real_test_user['email'])
    await page.fill('input[name="password"]', real_test_user['password'])
    await page.click('button[type="submit"]')
    
    # This will actually hit Supabase and create a real session
    await page.wait_for_url("**/chat")
    
    # Verify session is real
    cookies = await page.context.cookies()
    session_cookie = next((c for c in cookies if c['name'] == 'session'), None)
    assert session_cookie is not None
```

### 3. Session Cookie Injection (Fast, Requires Valid Token)

**When to use**: When you need a real session but want to skip login UI

```python
from tests.fixtures.test_auth import JWTTestAuth

@pytest.fixture
async def authenticated_browser_context(browser):
    """Create browser context with pre-injected auth session"""
    context = await browser.new_context()
    
    # Create JWT token
    jwt_auth = JWTTestAuth()
    token = jwt_auth.create_token(
        user_id="test-user-123",
        email="test@example.com"
    )
    
    # Inject session cookie
    await context.add_cookies([{
        'name': 'session',
        'value': token,
        'domain': 'web-service',
        'path': '/',
        'httpOnly': True,
        'secure': False  # Set to True in production
    }])
    
    yield context
    await context.close()

@pytest.mark.asyncio
async def test_with_injected_session(authenticated_browser_context):
    """Test starting with authenticated session"""
    page = await authenticated_browser_context.new_page()
    
    # Navigate directly to protected route
    await page.goto("/chat")
    
    # Should not redirect to login
    assert page.url.endswith("/chat")
```

### 4. API-First Authentication (Hybrid Approach)

**When to use**: Complex test scenarios, need to test both API and UI

```python
import httpx

@pytest.fixture
async def api_authenticated_page(page):
    """Authenticate via API, then use session in browser"""
    async with httpx.AsyncClient(base_url="http://gateway:8000") as client:
        # Login via API
        response = await client.post("/auth/login", json={
            "email": "test@test.local",
            "password": "test-password"
        })
        
        # Extract session token
        session_token = response.json().get("access_token")
        
        # Inject into browser
        await page.context.add_cookies([{
            'name': 'auth-token',
            'value': session_token,
            'domain': 'web-service',
            'path': '/'
        }])
    
    yield page
```

### 5. Full E2E Testing with Email Verification

**When to use**: Testing complete registration flows including email verification

```python
@pytest.mark.asyncio
async def test_full_registration_with_email(page, mailhog_client):
    """Test registration including email verification"""
    test_email = f"test-{uuid.uuid4()}@example.com"
    
    # Register
    await page.goto("/register")
    await page.fill('input[name="email"]', test_email)
    await page.fill('input[name="password"]', 'Test123!@#')
    await page.click('button[type="submit"]')
    
    # Check for verification message
    await page.wait_for_selector('text="Check Your Email"')
    
    # Get verification link from email (requires email testing service)
    verification_link = await mailhog_client.get_verification_link(test_email)
    
    # Visit verification link
    await page.goto(verification_link)
    
    # Should redirect to login with success message
    await page.wait_for_selector('text="Email verified successfully"')
```

## Best Practices

### 1. Use Page Objects for Complex Auth Flows

```python
class LoginPage:
    def __init__(self, page):
        self.page = page
        self.email_input = 'input[name="email"]'
        self.password_input = 'input[name="password"]'
        self.submit_button = 'button[type="submit"]'
    
    async def login(self, email: str, password: str):
        await self.page.goto("/login")
        await self.page.fill(self.email_input, email)
        await self.page.fill(self.password_input, password)
        await self.page.click(self.submit_button)
        await self.page.wait_for_url("**/chat")
```

### 2. Parallel Test Execution with Isolated Users

```python
@pytest.fixture
async def unique_test_user():
    """Create unique user for parallel test execution"""
    factory = TestUserFactory()
    user = factory.create_verified_test_user(
        email=f"test-{uuid.uuid4()}-{datetime.now().timestamp()}@test.local"
    )
    yield user
    factory.cleanup()
```

### 3. Environment-Specific Authentication

```python
@pytest.fixture
async def authenticated_page(page):
    """Use different auth strategies based on environment"""
    if os.getenv("USE_REAL_AUTH") == "true":
        # Real authentication for staging/integration tests
        await real_login(page)
    else:
        # Mock authentication for unit tests
        await mock_login(page)
    
    yield page
```

### 4. Debugging Authentication Issues

```python
# Enable verbose logging
page.on("console", lambda msg: print(f"Browser: {msg.text}"))
page.on("request", lambda req: print(f"Request: {req.url}"))
page.on("response", lambda res: print(f"Response: {res.url} - {res.status}"))

# Take screenshots on failure
try:
    await page.click("#non-existent")
except Exception:
    await page.screenshot(path="auth-failure.png")
    raise
```

## Performance Considerations

1. **Mock auth for unit tests**: ~50ms per test
2. **Real auth for integration**: ~500-1000ms per test
3. **Session injection**: ~100ms per test
4. **Full E2E with email**: ~2000-3000ms per test

## Security Considerations

1. **Never commit real credentials**
2. **Use service keys only in CI/CD with secrets**
3. **Clean up test users after tests**
4. **Use unique emails to avoid conflicts**
5. **Rotate test credentials regularly**

## Example Test Suite Structure

```python
class TestAuthenticatedFeatures:
    """Tests requiring authentication"""
    
    @pytest.mark.unit
    async def test_chat_ui_with_mock_auth(self, page):
        """Fast unit test with mocked auth"""
        # Use mock authentication
        pass
    
    @pytest.mark.integration
    async def test_chat_api_with_real_auth(self, page, real_test_user):
        """Integration test with real Supabase"""
        # Use real authentication
        pass
    
    @pytest.mark.e2e
    async def test_full_user_journey(self, page, mailhog_client):
        """Full E2E test including email verification"""
        # Complete user journey
        pass
```

## Troubleshooting

### Common Issues

1. **Session not persisting**: Check cookie domain and path
2. **Redirect loops**: Ensure auth mock is set up before navigation
3. **Timeout on wait_for_url**: Increase timeout or check for errors
4. **Cookie rejection**: Verify secure/httpOnly settings match environment

### Debug Helpers

```python
# Print all cookies
cookies = await page.context.cookies()
print("Cookies:", cookies)

# Check localStorage
storage = await page.evaluate("() => Object.entries(localStorage)")
print("LocalStorage:", storage)

# Verify session endpoint
response = await page.request.get("/api/auth/session")
print("Session:", await response.json())
```