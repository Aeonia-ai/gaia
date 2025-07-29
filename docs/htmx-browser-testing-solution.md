# HTMX Browser Testing Solution

## The Problem

The chat browser tests are timing out because the login form uses HTMX for authentication, which behaves differently from traditional form submissions:

1. **Traditional form submission**: 
   - Browser navigates to new page
   - Full page reload
   - Easy to mock with simple redirects

2. **HTMX form submission**:
   - JavaScript makes AJAX request
   - Server responds with HTML fragment or HX-Redirect header
   - Browser updates DOM or follows redirect via JavaScript
   - No full page navigation unless HX-Redirect is used

## Why Tests Were Failing

From the debug output:
```
Form attributes:
  method: None
  action: None
  hx-post: /auth/login
  hx-target: #auth-form-container
  hx-swap: outerHTML
```

The login form uses:
- `hx-post="/auth/login"` - HTMX POST to auth endpoint
- `hx-target="#auth-form-container"` - Replace this element with response
- `hx-swap="outerHTML"` - Replace entire element

When authentication succeeds, the server responds with:
- `HX-Redirect: /chat` header
- HTMX then navigates to `/chat`
- But `/chat` checks for session and redirects back to `/login` if not found

## The Solution

### 1. Mock Both Auth and Chat Endpoints

```python
# Track session state
session_active = False

async def handle_auth(route):
    nonlocal session_active
    session_active = True
    
    # HTMX requests need HX-Redirect header
    if 'hx-request' in route.request.headers:
        await route.fulfill(
            status=200,
            headers={"HX-Redirect": "/chat"},
            body=""
        )
    else:
        await route.fulfill(
            status=303,
            headers={"Location": "/chat"}
        )

async def handle_chat(route):
    # Check if session is active
    if session_active:
        await route.fulfill(
            status=200,
            content_type="text/html",
            body="""<html>...</html>"""  # Full chat page
        )
    else:
        await route.fulfill(
            status=303,
            headers={"Location": "/login"}
        )
```

### 2. Alternative: Use Session Cookies

```python
# Set cookie in context before navigation
await context.add_cookies([{
    'name': 'session',
    'value': 'test-session-token',
    'domain': 'web-service',
    'path': '/',
    'httpOnly': True
}])

# Then navigate directly to /chat
await page.goto(f'{WEB_SERVICE_URL}/chat')
```

### 3. Best Practice: Mock Minimal Required Endpoints

For chat testing, you need to mock:
1. `/auth/login` - Return HX-Redirect header
2. `/chat` - Return chat page HTML (not redirect)
3. `/api/conversations` - Return empty conversation list
4. `/api/v1/chat` - Return mock chat responses

## Working Test Pattern

See `/tests/web/test_chat_working.py` for complete working examples that:
1. Handle HTMX authentication properly
2. Maintain session state across requests
3. Mock all required endpoints
4. Verify chat functionality

## Key Learnings

1. **HTMX changes navigation patterns** - Traditional page.wait_for_url() may not work as expected
2. **Session state must be tracked** - Mocks need to maintain session state between auth and subsequent requests
3. **Mock the full flow** - Don't try to mix real pages with mocked auth
4. **Use route.fulfill() not route.continue_()** - Full control over responses is more reliable

## Running the Tests

```bash
# Run working chat tests
RUN_BROWSER_TESTS=true docker compose run --rm test pytest tests/web/test_chat_working.py -v

# Run with visible browser (for debugging)
RUN_BROWSER_TESTS=true HEADLESS=false docker compose run --rm test pytest tests/web/test_chat_working.py -v
```