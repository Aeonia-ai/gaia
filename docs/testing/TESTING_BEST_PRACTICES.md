# Testing Best Practices

> **This document consolidates all testing patterns and best practices for the GAIA platform.**

## Table of Contents
1. [Core Testing Principles](#core-testing-principles)
2. [Unit Testing Patterns](#unit-testing-patterns)
3. [Integration Testing Patterns](#integration-testing-patterns)
4. [E2E Testing Patterns](#e2e-testing-patterns)
5. [Browser Testing Patterns](#browser-testing-patterns)
6. [Test Organization](#test-organization)
7. [Fixtures and Utilities](#fixtures-and-utilities)
8. [Common Antipatterns](#common-antipatterns)
9. [Performance Optimization](#performance-optimization)

## Core Testing Principles

### 🚨 INSTITUTIONAL KNOWLEDGE CAPTURE
**Always document test fixes and discoveries in [APPEND-ONLY-TEST-FIXES-LOG.md](../../APPEND-ONLY-TEST-FIXES-LOG.md)**
- Captures patterns that prevent future debugging sessions
- Documents framework-specific gotchas (FastHTML, HTMX, Playwright)
- Records successful fix strategies for similar failures
- NEVER overwrite - always append chronologically

### The GAIA Test Philosophy

1. **Test Behavior, Not Implementation**
   - Focus on what the code does, not how it does it
   - Tests should survive refactoring
   - Avoid testing internal implementation details

2. **Use Real Components When Appropriate**
   - E2E tests: Always use real authentication (no mocks)
   - Integration tests: Use real services and databases
   - Unit tests: Mock only external dependencies

3. **Tests as Living Documentation**
   - Test names should describe the behavior clearly
   - Tests demonstrate how to use components
   - Include edge cases and error scenarios

### 🎯 THE ULTIMATE META LESSON ON TEST FAILURES

> **Test failures are rarely about the tests themselves.** They're usually telling you about:
> - **Missing features** (e.g., auto-scroll functionality wasn't implemented)
> - **Configuration mismatches** (e.g., Docker pytest.ini had hidden `-n auto`)
> - **Timing/ordering issues** (e.g., mocking APIs after navigation already started)
> - **Environmental differences** (e.g., Docker vs local configurations)
>
> **Listen to what tests are trying to tell you.** When you find yourself fighting to make tests pass, stop and ask: "What is this test specification telling me about what the app should do?" Often, the app is incomplete, not the test.

### Critical Testing Insights

#### Verifying Features Before Claiming They're Missing
1. **Debug DOM structure first**: Use `page.content()` to see actual HTML
2. **Check different selectors**: Features may exist with different markup
3. **Look for HTMX patterns**: Dynamic content may not use traditional selectors
4. **Example**: Messages displayed as `#messages > div`, not `.message`

#### Integration Test Best Practices
- **Integration tests should use real services**, not mocks
- **Real authentication in E2E tests**: Use `TestUserFactory` with Supabase
- **Mock at boundaries only**: Mock external services, not internal ones
- **Test actual behavior**: If it's an integration test, test integration

#### Proper Test Categorization
```python
# Failing because broken (fix the test)
@pytest.mark.xfail(reason="Selector changed from .message to #messages > div")
async def test_message_display():
    ...

# Failing because feature missing (implement the feature)
@pytest.mark.xfail(reason="Auto-scroll not yet implemented")
async def test_message_auto_scroll():
    ...

# Skip temporarily (with clear reason)
@pytest.mark.skip(reason="Requires Supabase service key configuration")
async def test_real_auth_flow():
    ...
```

### The Test Pyramid

```
         /\
        /  \  E2E Tests (10-15%)
       /----\  - Real Supabase auth
      /      \  - Complete user journeys
     /--------\  Integration Tests (25-35%)
    /          \  - Service boundaries
   /------------\  - Real Docker services
  /              \  Unit Tests (50-65%)
 /                \  - Business logic
/____________________\  - Pure functions
```

### F.I.R.S.T Principles

- **Fast**: Unit tests < 100ms, Integration < 5s, E2E < 30s
- **Isolated**: No shared state between tests
- **Repeatable**: Same result every time
- **Self-validating**: Clear pass/fail
- **Timely**: Written with or before the code

## Unit Testing Patterns

### Basic Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestChatService:
    """Test the ChatService component"""
    
    @pytest.fixture
    def chat_service(self):
        """Create a fresh instance for each test"""
        return ChatService()
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock external LLM dependency"""
        return Mock()
    
    def test_process_message_returns_response(self, chat_service, mock_llm_client):
        """Test that processing a message returns a valid response"""
        # Arrange
        chat_service.llm_client = mock_llm_client
        mock_llm_client.complete.return_value = "AI response"
        
        # Act
        response = chat_service.process_message("Hello")
        
        # Assert
        assert response == "AI response"
        mock_llm_client.complete.assert_called_once_with("Hello")
```

### Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_operation(self):
    """Test asynchronous operations"""
    # Arrange
    service = AsyncService()
    
    # Act
    result = await service.fetch_data()
    
    # Assert
    assert result is not None
    assert len(result) > 0
```

### Mocking Best Practices

```python
# Good: Mock at service boundaries
@patch('app.services.external_api.ExternalAPI')
def test_with_mocked_api(self, mock_api):
    mock_api.return_value.fetch.return_value = {"status": "success"}
    
# Bad: Over-mocking internal methods
@patch('app.services.chat.ChatService._internal_method')  # Don't do this!
```

## Integration Testing Patterns

### Service Integration Tests

```python
import httpx
import pytest
from tests.fixtures.test_auth import JWTTestAuth

class TestChatAPIIntegration:
    """Test chat API with real services"""
    
    @pytest.fixture
    def jwt_auth(self):
        return JWTTestAuth()
    
    @pytest.mark.asyncio
    async def test_chat_flow_with_auth(self, jwt_auth):
        """Test complete chat flow with authentication"""
        # Arrange
        headers = jwt_auth.create_auth_headers(user_id="test-user")
        
        # Act - Create conversation
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://chat-service:8000/v1/chat",
                headers=headers,
                json={"message": "Hello"}
            )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "response" in data
```

### Database Integration Tests

```python
@pytest.mark.integration
class TestDatabaseOperations:
    """Test with real database"""
    
    @pytest.fixture
    async def db_session(self):
        """Provide clean database session"""
        async with get_test_db() as session:
            yield session
            # Cleanup happens automatically
    
    @pytest.mark.asyncio
    async def test_user_creation(self, db_session):
        """Test creating user in database"""
        # Arrange
        user_data = {"email": "test@example.com"}
        
        # Act
        user = await create_user(db_session, user_data)
        
        # Assert
        assert user.id is not None
        assert user.email == "test@example.com"
```

## E2E Testing Patterns

### Real Authentication Pattern

```python
from tests.fixtures.test_auth import TestUserFactory

class TestE2EWithRealAuth:
    """E2E tests with real Supabase authentication"""
    
    @pytest.fixture
    def user_factory(self):
        """Create real test users"""
        factory = TestUserFactory()
        yield factory
        factory.cleanup_all()  # Important!
    
    @pytest.mark.e2e
    async def test_complete_user_journey(self, user_factory):
        """Test registration → login → chat → logout"""
        # Create real user
        test_user = user_factory.create_verified_test_user()
        
        # Perform real login
        login_response = await self.login_user(
            test_user["email"], 
            test_user["password"]
        )
        token = login_response["access_token"]
        
        # Use real token for subsequent requests
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test actual functionality
        chat_response = await self.send_chat_message(headers, "Hello")
        assert chat_response.status_code == 200
```

### Never Mock in E2E Tests

```python
# ❌ BAD: Mocking in E2E tests
@pytest.mark.e2e
async def test_bad_e2e_with_mocks(self):
    with patch('app.auth.validate_token'):  # Don't do this!
        # This defeats the purpose of E2E testing
        pass

# ✅ GOOD: Use real services
@pytest.mark.e2e
async def test_good_e2e_real_services(self, user_factory):
    # Use real authentication
    real_user = user_factory.create_verified_test_user()
    # Test with actual services
```

## Browser Testing Patterns

### Authentication in Browser Tests

```python
from playwright.async_api import async_playwright
from tests.web.browser_test_base import BrowserTestBase

class TestChatUI(BrowserTestBase):
    """Test chat UI with proper authentication"""
    
    @pytest.mark.asyncio
    async def test_chat_interface(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Setup authenticated context
            context = await self.setup_authenticated_context(browser)
            page = await context.new_page()
            
            # Mock API responses
            await page.route("**/api/session", lambda route: route.fulfill(
                json={"user": {"id": "test-123", "email": "test@example.com"}}
            ))
            
            # Navigate and test
            await page.goto(f"{WEB_SERVICE_URL}/chat")
            await page.wait_for_selector("#chat-container")
            
            # Test interactions
            await page.fill("#message-input", "Hello")
            await page.click("#send-button")
            
            # Verify response appears
            await page.wait_for_selector(".message-response")
```

### Avoiding Flaky Browser Tests

```python
# Good: Wait for specific conditions
await page.wait_for_selector("#chat-loaded", state="visible")
await page.wait_for_load_state("networkidle")

# Bad: Arbitrary sleep
await page.wait_for_timeout(2000)  # Avoid this!

# Good: Retry with expect
await expect(page.locator("#message")).to_have_text("Hello", timeout=5000)

# Bad: Single assertion that might fail
assert page.locator("#message").text_content() == "Hello"  # Race condition!
```

## Test Organization

### Directory Structure

```
tests/
├── conftest.py              # Shared pytest configuration
├── fixtures/                # Reusable test utilities
│   ├── __init__.py
│   ├── test_auth.py        # Authentication helpers
│   └── test_data.py        # Test data generators
├── unit/                   # Unit tests
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/            # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_database.py
│   └── test_service_communication.py
├── e2e/                    # End-to-end tests
│   ├── test_user_flows.py
│   └── test_real_scenarios.py
└── web/                    # Browser tests
    ├── browser_test_base.py
    └── test_ui_behavior.py
```

### Naming Conventions

```python
# Test files: test_*.py or *_test.py
test_chat_service.py

# Test classes: Test<Component>
class TestChatService:
    pass

# Test methods: test_<behavior>_<condition>_<expected>
def test_send_message_with_empty_text_raises_error(self):
    pass

# Fixtures: descriptive names without "fixture" suffix
@pytest.fixture
def authenticated_user():  # Good
    pass

@pytest.fixture
def user_fixture():  # Redundant
    pass
```

## Fixtures and Utilities

### Fixture Scopes

```python
# Function scope (default) - fresh for each test
@pytest.fixture
def api_client():
    return APIClient()

# Class scope - shared within test class
@pytest.fixture(scope="class")
def database_connection():
    conn = create_connection()
    yield conn
    conn.close()

# Session scope - shared across all tests
@pytest.fixture(scope="session")
def docker_services():
    # Start services once for entire test run
    pass
```

### Fixture Composition

```python
@pytest.fixture
def user(db_session):
    """Create a test user"""
    return create_test_user(db_session)

@pytest.fixture
def authenticated_client(user):
    """Client with authenticated user"""
    client = TestClient()
    client.login(user)
    return client

@pytest.fixture
def chat_with_history(authenticated_client, user):
    """Chat with message history"""
    chat = Chat(user_id=user.id)
    chat.add_message("Previous message")
    return chat
```

## Common Antipatterns

### 1. Testing Implementation Details

```python
# ❌ Bad: Testing private methods
def test_private_method(self):
    service = Service()
    result = service._calculate_internal_state()  # Don't test this
    assert result == 42

# ✅ Good: Test public interface
def test_public_behavior(self):
    service = Service()
    result = service.process_data(input_data)
    assert result.status == "processed"
```

### 2. Shared Mutable State

```python
# ❌ Bad: Shared state between tests
class TestWithSharedState:
    shared_list = []  # This will cause test pollution!
    
    def test_one(self):
        self.shared_list.append(1)
    
    def test_two(self):
        assert len(self.shared_list) == 0  # Fails if test_one runs first!

# ✅ Good: Isolated state
class TestWithIsolatedState:
    @pytest.fixture
    def test_list(self):
        return []  # Fresh list for each test
    
    def test_one(self, test_list):
        test_list.append(1)
        assert len(test_list) == 1
```

### 3. Testing Mock Behavior

```python
# ❌ Bad: Testing that mocks work
def test_mock_behavior(self):
    mock = Mock()
    mock.method.return_value = 42
    assert mock.method() == 42  # Just testing the mock!

# ✅ Good: Testing actual behavior with mocks
def test_service_uses_client(self):
    mock_client = Mock()
    mock_client.fetch.return_value = {"data": "value"}
    
    service = Service(client=mock_client)
    result = service.get_data()
    
    assert result == "value"
    mock_client.fetch.assert_called_once()
```

## Performance Optimization

### Parallel Test Execution

```bash
# Run tests in parallel
./scripts/pytest-for-claude.sh -n auto

# Specify number of workers
./scripts/pytest-for-claude.sh -n 4
```

### Test Markers for Speed

```python
# Mark slow tests
@pytest.mark.slow
async def test_complex_e2e_flow(self):
    # This test takes >10 seconds
    pass

# Skip slow tests during development
# ./scripts/pytest-for-claude.sh -m "not slow"
```

### Database Optimization

```python
# Use transactions for faster cleanup
@pytest.fixture
async def db_session():
    async with database.transaction() as tx:
        yield tx
        await tx.rollback()  # Fast cleanup

# Reuse test data when possible
@pytest.fixture(scope="session")
def static_test_data():
    # Create once, read many times
    return load_test_fixtures()
```

### Docker Optimization

```python
# Use pytest-docker for service management
@pytest.fixture(scope="session")
def docker_services(docker_ip, docker_services):
    # Services start once per session
    docker_services.wait_until_responsive(
        timeout=30.0,
        pause=0.1,
        check=lambda: is_service_ready()
    )
    return docker_services
```

## Best Practices Summary

### Do's ✅
1. Write descriptive test names
2. Follow AAA pattern (Arrange, Act, Assert)
3. Use fixtures for common setup
4. Clean up test data
5. Test edge cases and errors
6. Use real services in E2E tests
7. Mock at service boundaries
8. Run tests in CI/CD

### Don'ts ❌
1. Don't test implementation details
2. Don't share state between tests
3. Don't use arbitrary sleeps
4. Don't mock in E2E tests
5. Don't ignore flaky tests
6. Don't test framework code
7. Don't use production credentials
8. Don't skip writing tests

## Additional Resources

- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Main testing guide
- [TEST_INFRASTRUCTURE.md](TEST_INFRASTRUCTURE.md) - Technical details
- [Tester Agent](/docs/agents/tester.md) - AI assistant for testing
- [E2E Real Auth Testing](e2e-real-auth-testing.md) - Authentication patterns

---

**Remember**: Good tests enable confidence in changes. Write tests that give you that confidence!