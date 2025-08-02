# Test Patterns and Examples

This document provides detailed examples of test patterns used in the Gaia Platform, showing exactly how different types of tests are structured.

## Unit Test Patterns

### Mocking External Services

```python
# From test_auth_flow.py
@pytest.fixture
def mock_gateway_client():
    """Mock the gateway client for auth tests"""
    with patch('app.services.web.routes.auth.GaiaAPIClient') as mock:
        client = AsyncMock()
        mock.return_value.__aenter__.return_value = client
        yield client

async def test_login_with_valid_credentials(mock_gateway_client):
    # Configure mock response
    mock_gateway_client.login.return_value = {
        "access_token": "fake-jwt-token",
        "user": {"email": "test@example.com"}
    }
    
    # Test login flow
    response = await client.post("/login", 
        data={"email": "test@example.com", "password": "password"})
    
    assert response.status_code == 303  # Redirect after login
```

### Testing Error Handling

```python
# From test_error_handling.py
def test_create_error_response():
    response = create_error_response("Test error", 400)
    assert response.status_code == 400
    assert response.json()["error"] == "Test error"
    assert "timestamp" in response.json()
```

## Integration Test Patterns

### Testing Real API Endpoints

```python
# From test_working_endpoints.py
class TestWorkingEndpoints:
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"  # Docker internal network
    
    @pytest.fixture
    def headers(self, api_key):
        return {"X-API-Key": api_key}
    
    async def test_v02_chat_completion(self, gateway_url, headers):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat/completions",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "claude-3-5-haiku-20241022"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "choices" in data
            assert len(data["choices"]) > 0
```

### Testing Streaming Responses

```python
# From test_v02_chat_api.py
async def test_streaming_chat(self, gateway_url, headers):
    messages = []
    
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{gateway_url}/api/v0.2/chat/completions",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "Count to 3"}],
                "model": "claude-3-5-haiku-20241022",
                "stream": True
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    messages.append(line[6:])
    
    assert len(messages) > 0
    assert any("[DONE]" in msg for msg in messages)
```

### Testing Knowledge Base Operations

```python
# From test_kb_endpoints.py
async def test_kb_search(self, gateway_url, headers):
    # First, ensure KB is initialized
    health_response = await client.get(
        f"{gateway_url}/api/v1/kb/health",
        headers=headers
    )
    
    if health_response.status_code == 200:
        # Perform search
        response = await client.post(
            f"{gateway_url}/api/v0.2/kb/search",
            headers=headers,
            json={"message": "test query"}
        )
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "results" in data or "response" in data
```

## E2E Test Patterns

### Real Authentication with TestUserFactory

```python
# From test_real_auth_e2e.py
from tests.utils.auth import TestUserFactory

async def test_real_login_and_logout():
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
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navigate to login
            await page.goto("http://web-service:8669/login")
            
            # Fill login form
            await page.fill('input[name="email"]', test_email)
            await page.fill('input[name="password"]', test_password)
            
            # Submit and wait for redirect
            await page.click('button[type="submit"]')
            await page.wait_for_url("**/chat")
            
            # Verify logged in
            assert "/chat" in page.url
            
            # Test logout
            await page.click('button:has-text("Logout")')
            await page.wait_for_url("**/login")
            
            await browser.close()
            
    finally:
        # Always clean up test users
        factory.cleanup()
```

### Testing Chat Functionality

```python
# From test_chat_browser_auth.py
async def test_send_and_receive_message():
    factory = TestUserFactory()
    user = factory.create_verified_test_user()
    
    try:
        # ... login code ...
        
        # Send message
        await page.fill('input[name="message"]', "Hello AI")
        await page.click('button[type="submit"]')
        
        # Wait for response
        await page.wait_for_selector(
            "#messages div:last-child",
            state="visible",
            timeout=10000
        )
        
        # Verify message appeared
        messages = await page.query_selector_all("#messages div")
        assert len(messages) >= 2  # User message + AI response
        
    finally:
        factory.cleanup()
```

### Testing Edge Cases

```python
# From test_browser_edge_cases.py
async def test_console_errors():
    console_errors = []
    
    # Monitor console
    page.on("console", lambda msg: 
        console_errors.append(msg) if msg.type == "error" else None
    )
    
    # Perform actions that might cause errors
    await page.goto("http://web-service:8669/login")
    await page.fill('input[name="email"]', "invalid-email")
    await page.click('button[type="submit"]')
    
    # Should have client-side validation, no console errors
    assert len(console_errors) == 0
```

## Authentication Testing Patterns

### Unit Test Authentication (Mocked)

```python
# Fast, no external dependencies
def mock_jwt_token():
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock.token"

async def test_protected_endpoint(mock_jwt_token):
    headers = {"Authorization": f"Bearer {mock_jwt_token}"}
    # Test with mocked auth
```

### Integration Test Authentication (API Key)

```python
# Uses real API key from environment
@pytest.fixture
def api_key():
    key = os.getenv("TEST_API_KEY", os.getenv("API_KEY"))
    if not key:
        pytest.skip("No API key available")
    return key

async def test_with_api_key(api_key):
    headers = {"X-API-Key": api_key}
    # Test with real API key
```

### E2E Test Authentication (Real Supabase)

```python
# Creates real users in Supabase
factory = TestUserFactory()
user = factory.create_verified_test_user()
# Perform real login through UI
# No mocks, no shortcuts
```

## Performance Testing Patterns

```python
# From test_comprehensive_suite.py
async def test_performance_monitoring(self, gateway_url, headers):
    """Test that responses meet performance targets"""
    timings = []
    
    for _ in range(5):
        start = time.time()
        response = await client.post(
            f"{gateway_url}/api/v0.2/chat/completions",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 50
            }
        )
        timings.append(time.time() - start)
    
    avg_time = sum(timings) / len(timings)
    assert avg_time < 3.0  # Should respond within 3 seconds
    
    logger.info(f"Average response time: {avg_time:.2f}s")
```

## Parallel Testing Patterns

```python
# From test_comprehensive_suite.py
async def test_concurrent_operations(self, gateway_url, headers):
    """Test system handles concurrent requests"""
    
    async def make_request(session_id):
        response = await client.post(
            f"{gateway_url}/api/v0.2/chat/completions",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": f"Request {session_id}"}],
                "conversation_id": f"test-concurrent-{session_id}"
            }
        )
        return response
    
    # Launch 5 concurrent requests
    tasks = [make_request(i) for i in range(5)]
    responses = await asyncio.gather(*tasks)
    
    # All should succeed
    assert all(r.status_code == 200 for r in responses)
```

## Test Data Management

### Fixtures for Test Data

```python
@pytest.fixture
def test_messages():
    return [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ]

@pytest.fixture
def test_conversation_id():
    return f"test-conv-{uuid.uuid4().hex[:8]}"
```

### Cleanup Patterns

```python
@pytest.fixture
async def cleanup_test_data():
    created_ids = []
    
    yield created_ids  # Test adds IDs to this list
    
    # Cleanup after test
    for item_id in created_ids:
        try:
            await delete_test_item(item_id)
        except Exception:
            pass  # Best effort cleanup
```

## Key Takeaways

1. **Unit Tests**: Mock everything, test fast
2. **Integration Tests**: Real services, Docker networking
3. **E2E Tests**: Real users, real browser, no mocks
4. **Authentication**: Match test type to auth approach
5. **Cleanup**: Always clean up test data
6. **Performance**: Monitor and assert on timing
7. **Debugging**: Capture logs and screenshots on failure