# E2E Real Authentication Testing Guide

## Overview

End-to-End (E2E) tests in the Gaia Platform **MUST** use real Supabase authentication. This guide explains why and how to implement E2E tests with real authentication.

## Why Real Authentication?

### The Problem with Mocks
- **E2E means End-to-End**: The entire user journey must be tested
- **Authentication is critical**: It's the gateway to all functionality
- **Integration bugs**: Mocks hide real integration issues
- **User experience**: Users don't experience mocks, they experience the real system

### What We Test
- Real Supabase authentication flow
- JWT token generation and validation
- Session management and persistence
- Error handling and edge cases
- Complete user journeys

## Prerequisites

### 1. Valid Supabase Service Key
```bash
# In your .env file
SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

To verify your key:
```bash
python test_supabase_keys.py
```

### 2. Test User Factory
All E2E tests use the `TestUserFactory` for consistent user management:

```python
from tests.utils.auth import TestUserFactory
```

## Writing E2E Tests

### Basic Pattern
```python
import uuid
from playwright.async_api import async_playwright
from tests.utils.auth import TestUserFactory

async def test_real_login_and_chat():
    """Test complete user journey with real authentication."""
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
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Real login through UI
            await page.goto("http://localhost:8669/login")
            await page.fill('input[name="email"]', test_email)
            await page.fill('input[name="password"]', test_password)
            await page.click('button[type="submit"]')
            
            # Wait for redirect to chat
            await page.wait_for_url("**/chat")
            
            # Test authenticated functionality
            await page.fill('input[name="message"]', "Hello from E2E test")
            await page.click('button[type="submit"]')
            
            # Verify response
            await page.wait_for_selector("#messages div", state="visible")
            
            await browser.close()
            
    finally:
        # Always clean up test users
        factory.cleanup()
```

### Advanced Patterns

#### Multiple User Sessions
```python
async def test_multi_user_chat():
    """Test chat between multiple real users."""
    factory1 = TestUserFactory()
    factory2 = TestUserFactory()
    
    try:
        # Create two users
        user1 = factory1.create_verified_test_user(
            email=f"user1-{uuid.uuid4().hex[:8]}@test.local"
        )
        user2 = factory2.create_verified_test_user(
            email=f"user2-{uuid.uuid4().hex[:8]}@test.local"
        )
        
        # Test interaction between users...
        
    finally:
        factory1.cleanup()
        factory2.cleanup()
```

#### Session Persistence
```python
async def test_session_persistence():
    """Test that sessions persist across page reloads."""
    factory = TestUserFactory()
    user = factory.create_verified_test_user()
    
    try:
        # Login
        await page.goto("http://localhost:8669/login")
        # ... perform login
        
        # Reload page
        await page.reload()
        
        # Should still be logged in
        await page.wait_for_url("**/chat")
        
    finally:
        factory.cleanup()
```

## Common Patterns

### 1. Always Use Unique Emails
```python
# ✅ Good: Unique email prevents conflicts
test_email = f"e2e-{uuid.uuid4().hex[:8]}@test.local"

# ❌ Bad: Fixed email causes conflicts
test_email = "test@example.com"
```

### 2. Always Clean Up
```python
try:
    # Run tests
    pass
finally:
    # Always clean up, even if test fails
    factory.cleanup()
```

### 3. Wait for Elements
```python
# ✅ Good: Wait for specific conditions
await page.wait_for_selector("#messages div")
await page.wait_for_url("**/chat")

# ❌ Bad: Arbitrary timeouts
await page.wait_for_timeout(2000)
```

### 4. Handle Async Operations
```python
# Chat responses are async - wait for them
await page.fill('input[name="message"]', "Test message")
await page.click('button[type="submit"]')
await page.wait_for_selector("#messages div:last-child")
```

## Running E2E Tests

### Single Test
```bash
./scripts/pytest-for-claude.sh tests/e2e/test_real_auth_e2e.py::test_real_login -v
```

### All E2E Tests
```bash
./scripts/pytest-for-claude.sh tests/e2e -v
./scripts/check-test-progress.sh  # Monitor progress
```

### With Debugging
```bash
# Run with visible browser
PWDEBUG=1 ./scripts/pytest-for-claude.sh tests/e2e/test_real_auth_e2e.py -v -s
```

## Troubleshooting

### Invalid API Key Error
**Problem**: Tests fail with "Invalid API key"
**Solution**: 
1. Check SUPABASE_SERVICE_KEY in .env
2. Run `python test_supabase_keys.py` to verify
3. Get service key from Supabase dashboard

### User Already Exists
**Problem**: Test fails because email already exists
**Solution**: Always use unique emails with UUID

### Timeout Errors
**Problem**: Tests timeout waiting for elements
**Solution**: 
1. Increase timeouts for slow operations
2. Ensure services are running: `docker compose ps`
3. Check service logs: `docker compose logs web-service`

### Session Not Persisting
**Problem**: User logged out after navigation
**Solution**: Check cookie configuration and session handling

## Best Practices

1. **No Mocks in E2E**: If you're mocking auth, it's not E2E
2. **Real User Journeys**: Test what users actually do
3. **Unique Test Data**: Prevent conflicts with UUIDs
4. **Proper Cleanup**: Always clean up test data
5. **Explicit Waits**: Wait for specific conditions, not timeouts
6. **Error Screenshots**: Capture screenshots on failure
7. **Parallel Safety**: Design tests to run in parallel

## Example Test Suite

See `/tests/e2e/test_real_auth_e2e.py` for complete examples:
- Login and logout flows
- Chat functionality with auth
- Session persistence
- Multi-user scenarios
- Error handling

## Migration from Mock Tests

If you have existing tests with mock authentication:

```python
# ❌ OLD: Mock auth
await page.route("**/auth/login", lambda route: route.fulfill(
    status=303,
    headers={"Location": "/chat"}
))

# ✅ NEW: Real auth
factory = TestUserFactory()
user = factory.create_verified_test_user()
# Perform real login through UI
```

## Key Takeaways

1. **E2E = Real Everything**: No mocks, no shortcuts
2. **TestUserFactory is Your Friend**: Consistent user management
3. **Clean Up Always**: Prevent test pollution
4. **Wait Smart**: Use explicit waits, not timeouts
5. **Test User Journeys**: Not just individual features

Remember: If your E2E test has mocks, it's not really E2E!