# Browser Test Authentication Patterns

## Overview
This document explains the correct patterns for browser tests with session-based authentication in GAIA.

## Key Discovery
The root cause of most browser test failures was incorrect authentication mocking. The web service uses Starlette's SessionMiddleware which stores sessions server-side. Simply setting cookies in the browser doesn't work - you must also mock the session validation endpoint.

## Correct Authentication Pattern

### 1. Base Test Class (Recommended)
Create a base class that handles authentication setup:

```python
from .browser_test_base import BrowserTestBase

class TestYourFeature(BrowserTestBase):
    @pytest.mark.asyncio
    async def test_authenticated_feature(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await self.setup_authenticated_context(browser)
            page = await context.new_page()
            
            # Setup mocks
            await self.setup_auth_mocks(page)
            await self.setup_chat_page_mock(page)
            
            # Navigate directly to protected page
            await self.navigate_to_chat(page)
            
            # Your test logic here
```

### 2. Manual Setup Pattern
If you need custom setup:

```python
# Step 1: Add session cookie to context
context = await browser.new_context()
await context.add_cookies([{
    "name": "session",
    "value": "test-session-token",
    "domain": "web-service",
    "path": "/",
    "httpOnly": True
}])

# Step 2: Mock session validation endpoint
await page.route("**/api/session", lambda route: route.fulfill(
    status=200,
    json={
        "authenticated": True,
        "user": {
            "id": "test-user-123",
            "email": "test@test.local"
        },
        "jwt_token": "mock-jwt-token"
    }
))

# Step 3: Mock auth endpoints with HTMX support
async def handle_auth(route):
    if 'hx-request' in route.request.headers:
        await route.fulfill(
            status=200,
            headers={"HX-Redirect": "/chat"},
            body=""
        )
    else:
        await route.fulfill(
            status=303,
            headers={"Location": "/chat"},
            body=""
        )

await page.route("**/auth/login", handle_auth)
```

## Common Mistakes to Avoid

### 1. ❌ Setting cookies without session validation
```python
# WRONG - This alone won't work
await page.context.add_cookies([{"name": "session", "value": "token"}])
await page.goto("/chat")  # Will redirect to login
```

### 2. ❌ Not handling HTMX requests
```python
# WRONG - Missing HX-Redirect header
await page.route("**/auth/login", lambda route: route.fulfill(
    status=303,
    headers={"Location": "/chat"}
))
```

### 3. ❌ Navigating to login when already authenticated
```python
# WRONG - Unnecessary login flow
await page.goto("/login")
await page.fill('input[name="email"]', 'test@test.local')
await page.click('button[type="submit"]')

# RIGHT - Navigate directly
await self.navigate_to_chat(page)
```

## Playwright Syntax Updates

### 1. Locator API (Modern)
```python
# ✅ CORRECT - Use locator API
message_input = page.locator('input[name="message"]')
await expect(message_input).to_be_visible()
await message_input.fill("Hello")

# ❌ WRONG - Old query_selector API
message_input = await page.query_selector('input[name="message"]')
assert message_input, "Input should exist"
```

### 2. No await on locator()
```python
# ✅ CORRECT
button = page.locator('button').first

# ❌ WRONG
button = await page.locator('button').first
```

### 3. Python keyword arguments
```python
# ✅ CORRECT
await input.type('text', delay=100)

# ❌ WRONG - JavaScript syntax
await input.type('text', {delay: 100})
```

## Semantic Selectors

### 1. Prefer semantic selectors over classes
```python
# ✅ GOOD - Semantic, won't break with style changes
await page.locator('[role="alert"]')
await page.locator('button:has-text("Send")')
await page.locator('text=/error|failed/i')

# ❌ BRITTLE - Will break with style changes
await page.locator('.bg-red-500')
await page.locator('.flex.items-center.justify-between')
```

### 2. Use data attributes for test-specific selectors
```python
# ✅ GOOD - Explicit test hooks
await page.locator('[data-testid="chat-input"]')
await page.locator('[data-role="assistant"]')

# ❌ BRITTLE - Implementation detail
await page.locator('#__next > div > div:nth-child(2)')
```

## Files Updated

### Core Infrastructure
- **browser_test_base.py** - Base class with auth setup helpers
- **test_chat_auth_fixed.py** - Reference implementation showing patterns

### Updated Tests
- **test_chat_browser.py** - Main chat functionality tests
- **test_browser_edge_cases.py** - Edge case and race condition tests
- **test_chat_browser_improved.py** - Behavior-focused tests
- **test_chat_browser_fixed.py** - Clean example using base class

### Patterns Applied
1. Session cookie + validation endpoint mocking
2. HTMX-aware auth responses
3. Direct navigation (skip login when authenticated)
4. Modern Playwright locator API
5. Semantic selectors over brittle CSS
6. Proper error handling expectations

## Running the Tests

```bash
# Run all browser tests
./scripts/pytest-for-claude.sh tests/integration/web/ -v

# Run specific test file
./scripts/pytest-for-claude.sh tests/integration/web/test_chat_browser_fixed.py -v

# Run with visible browser (debugging)
HEADLESS=false ./scripts/pytest-for-claude.sh tests/integration/web/ -v
```

## Next Steps
1. Apply these patterns to any remaining browser tests
2. Remove redundant login flows from authenticated tests
3. Update selectors to be more semantic and less brittle
4. Consider adding more edge case tests using the base class