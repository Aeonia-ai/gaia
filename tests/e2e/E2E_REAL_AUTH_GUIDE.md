# E2E Real Authentication Guide

## Overview
All E2E tests must use real Supabase authentication. No mocks allowed!

## Converting Mock-Based Tests to Real Auth

### 1. Remove ALL Mock Routes
```python
# ❌ REMOVE THIS:
await page.route("**/auth/login", lambda route: route.fulfill(...))
await page.route("**/api/conversations", lambda route: route.fulfill(...))
await page.route("**/api/v1/chat", lambda route: route.fulfill(...))
```

### 2. Use TestUserFactory
```python
# ✅ DO THIS:
from tests.fixtures.test_auth import TestUserFactory

factory = TestUserFactory()
test_email = f"e2e-test-{uuid.uuid4().hex[:8]}@test.local"
test_password = "TestPassword123!"

user = factory.create_verified_test_user(
    email=test_email,
    password=test_password
)
```

### 3. Perform Real Login
```python
# ✅ Real login flow:
await page.goto(f'{WEB_SERVICE_URL}/login')
await page.fill('input[name="email"]', test_email)
await page.fill('input[name="password"]', test_password)
await page.click('button[type="submit"]')
await page.wait_for_url("**/chat", timeout=10000)
```

### 4. Always Cleanup
```python
# ✅ In finally block:
finally:
    await browser.close()
    factory.cleanup_test_user(user["user_id"])
```

## Common Patterns

### Pattern 1: Basic E2E Test
```python
@pytest.mark.asyncio
async def test_feature_with_real_auth(self):
    factory = TestUserFactory()
    user = factory.create_verified_test_user()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', user["email"])
            await page.fill('input[name="password"]', user["password"])
            await page.click('button[type="submit"]')
            await page.wait_for_url("**/chat")
            
            # Your test logic here
            
        finally:
            await browser.close()
            factory.cleanup_test_user(user["user_id"])
```

### Pattern 2: Multiple Users
```python
@pytest.mark.asyncio
async def test_multi_user_scenario(self):
    factory = TestUserFactory()
    users = []
    
    try:
        # Create multiple users
        for i in range(3):
            user = factory.create_verified_test_user(
                email=f"user{i}-{uuid.uuid4().hex[:8]}@test.local"
            )
            users.append(user)
        
        # Test with multiple browser contexts
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            for user in users:
                context = await browser.new_context()
                page = await context.new_page()
                
                # Login and test
                # ...
                
                await context.close()
            
            await browser.close()
    
    finally:
        # Cleanup all users
        for user in users:
            factory.cleanup_test_user(user["user_id"])
```

## What NOT to Do

### ❌ No Mock Fixtures
```python
# DON'T USE:
- mock_authenticated_page
- simple_auth_page
- authenticated_page_with_mocks
```

### ❌ No Fake Tokens
```python
# DON'T CREATE:
fake_jwt = "eyJ..."  # No!
mock_session = {"access_token": "fake"}  # No!
```

### ❌ No API Mocking
```python
# DON'T MOCK:
await page.route("**/api/**", ...)  # No mocking API calls!
```

## Debugging Tips

1. **Timeout on login?**
   - Check Supabase service key is valid
   - Verify user was created successfully
   - Check network connectivity

2. **Can't find elements?**
   - Real pages might load differently than mocked
   - Add explicit waits: `await page.wait_for_selector(...)`
   - Check for loading states

3. **Tests are slow?**
   - That's expected - real auth takes time
   - Run E2E tests separately from unit tests
   - Use parallel test execution where possible

## Environment Requirements

```bash
# Required environment variables:
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...  # Required for TestUserFactory
```

## Example Test Files
- `test_real_auth_e2e.py` - Complete examples with real auth
- `test_real_e2e_with_supabase.py` - Existing real auth tests
- `test_real_auth_browser.py` - Browser-specific real auth tests