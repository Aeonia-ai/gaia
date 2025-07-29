# Browser Testing Strategy

This document outlines our comprehensive browser testing approach for the Gaia web service, explaining why browser tests are crucial and how to use them effectively.

## Why Browser Tests Matter

URL-based tests (using TestClient) miss many real-world issues:

1. **JavaScript Execution**: URL tests don't run JavaScript, missing client-side logic errors
2. **HTMX Behavior**: HTMX partial updates and dynamic content swapping need real browser testing
3. **Race Conditions**: Timing issues between UI updates only appear in real browsers
4. **WebSocket Connections**: Real-time features require actual browser WebSocket support
5. **Browser Quirks**: Different browsers handle things differently (autofill, back button, etc.)
6. **Memory Leaks**: JavaScript memory leaks only show up in long-running browser sessions
7. **Console Errors**: JavaScript errors that don't break functionality but indicate problems

## Test Categories

### 1. Authentication Tests (`test_authenticated_browser.py`)
- Mock authentication for fast unit tests
- Real Supabase authentication for integration tests
- Session injection for testing authenticated states
- Multi-user scenarios

### 2. Full Web Functionality (`test_full_web_browser.py`)
- HTMX form submissions without page reloads
- Loading indicators and dynamic UI updates
- Client-side validation
- Responsive design behavior
- Accessibility features
- WebSocket connections

### 3. Edge Cases (`test_browser_edge_cases.py`)
- Console error monitoring
- Race condition detection
- Memory leak testing
- Browser-specific behaviors
- Form state persistence
- Double-submit prevention

### 4. Chat-Specific Tests (`test_chat_browser_auth.py`)
- Message sending and receiving
- Conversation persistence
- Auto-scrolling behavior
- Real-time updates

## Running Browser Tests

### Quick Start

```bash
# Run all browser tests (fast, mocked)
./scripts/run-browser-tests.sh

# Run specific category
./scripts/run-browser-tests.sh -t auth

# Debug mode (visible browser, slow)
./scripts/run-browser-tests.sh -d

# Integration tests with real backend
./scripts/run-browser-tests.sh -m integration

# Record videos of test runs
./scripts/run-browser-tests.sh -r
```

### Docker Compose

```bash
# Run all browser tests
RUN_BROWSER_TESTS=true docker compose run --rm test pytest tests/web/test_*browser*.py -v

# Run specific test
RUN_BROWSER_TESTS=true docker compose run --rm test pytest tests/web/test_authenticated_browser.py::TestAuthenticatedChat::test_chat_with_mocked_auth -v
```

## Authentication Strategies

### 1. Mock Authentication (Fastest)
```python
await page.route("**/auth/login", lambda route: route.fulfill(
    status=303,
    headers={"Location": "/chat"},
    body=""
))
```

### 2. Real Authentication (Integration)
```python
factory = TestUserFactory()
user = factory.create_verified_test_user(
    email="test@test.local",
    password="Test123!@#"
)
# ... perform real login
```

### 3. Session Injection (Hybrid)
```python
await context.add_cookies([{
    'name': 'session',
    'value': jwt_token,
    'domain': 'web-service',
    'path': '/'
}])
```

## Best Practices

### 1. Use Page Objects for Complex Flows
```python
class LoginPage:
    def __init__(self, page):
        self.page = page
    
    async def login(self, email, password):
        await self.page.fill('input[name="email"]', email)
        await self.page.fill('input[name="password"]', password)
        await self.page.click('button[type="submit"]')
```

### 2. Monitor Console Errors
```python
console_errors = []
page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
# ... run test
assert len(console_errors) == 0
```

### 3. Test at Multiple Viewports
```python
viewports = [
    {"width": 375, "height": 667},   # Mobile
    {"width": 768, "height": 1024},  # Tablet
    {"width": 1920, "height": 1080}  # Desktop
]
```

### 4. Handle Timing Issues
```python
# Wait for specific conditions, not arbitrary timeouts
await page.wait_for_selector('#chat-form')
await page.wait_for_load_state('networkidle')
```

### 5. Clean Up Test Data
```python
try:
    # Run test
    pass
finally:
    factory.cleanup()  # Always clean up test users
```

## Performance Considerations

- **Mock tests**: ~50-100ms per test
- **Real auth tests**: ~500-1000ms per test
- **Full E2E tests**: ~2000-3000ms per test
- **Visual tests**: ~1000-2000ms per test

## Debugging Failed Tests

### 1. Run in Debug Mode
```bash
./scripts/run-browser-tests.sh -d -s test_name
```

### 2. Check Screenshots
Failed tests save screenshots to `tests/web/screenshots/failures/`

### 3. Review Videos
With `-r` flag, videos are saved to `tests/web/videos/`

### 4. Check Console Output
Use `-v` for verbose output including console logs

### 5. Use Browser DevTools
In debug mode, you can pause tests and use browser DevTools

## Common Issues and Solutions

### Issue: Tests timeout
**Solution**: Increase timeout or check if services are running
```python
await page.wait_for_url("**/chat", timeout=10000)  # 10 seconds
```

### Issue: Element not found
**Solution**: Wait for element to appear
```python
await page.wait_for_selector('button[type="submit"]')
```

### Issue: Flaky tests
**Solution**: Add proper wait conditions
```python
await page.wait_for_load_state('networkidle')
```

### Issue: Different behavior in CI
**Solution**: Ensure same browser versions and viewport sizes

## Environment Variables

- `BROWSER_TEST_MODE`: unit, integration, e2e, visual
- `BROWSER_HEADLESS`: true/false
- `BROWSER_RECORD_VIDEO`: true/false
- `BROWSER_SLOW_MO`: Milliseconds to slow down operations
- `RUN_BROWSER_TESTS`: Must be true to run browser tests

## Future Enhancements

1. **Visual Regression Testing**: Automated screenshot comparison
2. **Performance Budgets**: Fail tests if pages load too slowly
3. **Cross-Browser Testing**: Test on Firefox, Safari, Edge
4. **Accessibility Audits**: Automated a11y testing
5. **Network Condition Testing**: Slow 3G, offline scenarios
6. **Security Testing**: XSS, CSRF protection verification

## HTMX Considerations

When testing HTMX-powered applications:
1. **HTMX uses AJAX** - Page navigations happen via JavaScript, not browser navigation
2. **Mock HX-Redirect headers** - HTMX follows these headers to navigate
3. **Track session state** - Maintain authentication state between mocked requests
4. **Mock the full flow** - Don't mix real pages with mocked authentication

See [HTMX Browser Testing Solution](htmx-browser-testing-solution.md) for detailed guidance on handling HTMX authentication forms.

## Conclusion

Browser tests are essential for catching issues that URL-based tests miss. They should be run:
- On every PR (fast mock tests)
- Before releases (full integration tests)
- After major changes (complete test suite)
- When debugging user-reported issues

The investment in browser testing pays off by catching bugs before users do.