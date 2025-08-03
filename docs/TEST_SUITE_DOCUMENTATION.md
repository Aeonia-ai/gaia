# Gaia Platform Test Suite - Comprehensive Documentation

## Overview

The Gaia Platform test suite is organized into three main categories: unit tests, integration tests, and end-to-end (E2E) tests. The test architecture emphasizes real-world authentication using Supabase JWTs, comprehensive API coverage, and proper test isolation.

## Test Organization

### Directory Structure
```
tests/
├── TEST_ORGANIZATION.md      # Test organization guide
├── conftest.py              # Global pytest configuration
├── fixtures/                # Shared test utilities
│   ├── test_auth.py        # Authentication test helpers
│   └── auth_helpers.py     # Additional auth utilities
├── unit/                    # Fast, isolated unit tests
├── integration/             # Service interaction tests
├── e2e/                     # End-to-end browser tests
└── web/                     # Web UI specific tests
```

### Test Categories

#### 1. Unit Tests (`tests/unit/`)
**Purpose**: Fast, isolated tests for individual components without external dependencies.

**Key Files**:
- `test_auth_flow.py` - Authentication flow tests for the web service
- `test_authentication_consistency.py` - Ensures auth config consistency across services
- `test_db_persistence.py` - Database persistence tests
- `test_error_handling.py` - Error handling and user feedback tests
- `test_ui_layout.py` - UI component and layout tests

**Characteristics**:
- Use mocked dependencies (no real Supabase/database calls)
- JWT-based authentication using `JWTTestAuth` helper
- Fast execution (< 1 second per test)
- Focus on logic validation, not integration

**Authentication Approach**:
```python
# Uses JWTTestAuth for creating test tokens
auth_manager = TestAuthManager(test_type="unit")
headers = auth_manager.get_auth_headers(
    email="test@test.local",
    role="authenticated"
)
```

#### 2. Integration Tests (`tests/integration/`)
**Purpose**: Test service interactions and API endpoints with real services.

**Key Files**:
- `test_working_endpoints.py` - Known working endpoints from manual testing
- `test_v02_chat_api.py` - v0.2 API endpoint tests
- `test_v03_api.py` - v0.3 clean API interface tests
- `test_kb_endpoints.py` - Knowledge Base service tests
- `test_provider_model_endpoints.py` - Provider/model management tests
- `test_comprehensive_suite.py` - Full system integration tests

**Characteristics**:
- Test real API endpoints through gateway
- Use Docker internal networking (http://service-name:port)
- May use real Supabase when configured
- Focus on API contracts and integration patterns

**Authentication Approach**:
- Primarily uses JWT tokens for auth
- Can use real Supabase users when `SUPABASE_SERVICE_KEY` is available
- Falls back to test JWTs when service key not available

#### 3. E2E Tests (`tests/e2e/`)
**Purpose**: Full browser-based testing with real user interactions.

**Key Files**:
- `test_real_auth_e2e.py` - Real Supabase authentication E2E tests
- `test_chat_browser.py` - Chat interface browser tests
- `test_browser_registration.py` - User registration flow tests
- Various browser configuration and helper files

**Characteristics**:
- Use Playwright for browser automation
- Create real Supabase users using service key
- Test complete user flows (login → chat → logout)
- Verify UI interactions and state management

**Authentication Approach**:
```python
# Creates real Supabase users
factory = TestUserFactory()
user = factory.create_verified_test_user(
    email=test_email,
    password=test_password
)
# Then performs real login through browser
```

## Authentication Testing Patterns

### 1. TestAuthManager
Central authentication manager that provides appropriate auth strategy based on test type:

```python
class TestAuthManager:
    def __init__(self, test_type: str = "unit"):
        # "unit" - JWT-only authentication
        # "integration" - Real Supabase if available
```

### 2. JWTTestAuth
Provides JWT-based authentication for unit tests:
- Creates valid JWT tokens without Supabase
- Configurable user attributes (email, role, user_id)
- No external dependencies

### 3. TestUserFactory
Creates real Supabase users for integration/E2E tests:
- Requires `SUPABASE_SERVICE_KEY`
- Creates users with pre-verified emails
- Automatic cleanup after tests

## Key Test Patterns

### 1. Mocking in Unit Tests
```python
@pytest.fixture
def mock_gateway_client(self):
    with patch('app.services.web.routes.auth.GaiaAPIClient') as mock:
        client = AsyncMock()
        mock.return_value.__aenter__.return_value = client
        yield client
```

### 2. Docker Network Testing
Integration tests use Docker internal URLs:
```python
gateway_url = "http://gateway:8000"
kb_url = "http://kb-service:8000"
```

### 3. Async Test Handling
```python
@pytest.mark.asyncio
async def test_async_endpoint(self):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
```

### 4. Browser Testing with Playwright
```python
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto(f'{WEB_SERVICE_URL}/login')
```

## Test Execution

### Running Tests
Due to Claude Code's 2-minute timeout limitation, tests must be run asynchronously:

```bash
# CORRECT - Use the async test runner
./scripts/pytest-for-claude.sh                    # All tests
./scripts/pytest-for-claude.sh tests/unit         # Unit tests only
./scripts/pytest-for-claude.sh tests/integration  # Integration tests
./scripts/pytest-for-claude.sh tests/e2e          # E2E tests

# INCORRECT - These will timeout
pytest                                            # Direct pytest
docker compose run test pytest                    # Direct docker pytest
```

### Test Markers
Defined in `pytest.ini`:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.browser` - Browser/E2E tests
- `@pytest.mark.host_only` - Tests requiring Docker access from host
- `@pytest.mark.container_safe` - Tests that run inside containers
- `@pytest.mark.requires_redis` - Tests needing Redis
- `@pytest.mark.requires_db` - Tests needing database

### Parallel Execution
Tests run in parallel using pytest-xdist:
- Automatically uses all CPU cores
- Significantly faster execution
- Tests must be properly isolated

## API Testing Coverage

### v0.2 API Tests
- Basic chat completion: `/api/v0.2/chat`
- Provider management: `/api/v0.2/providers`
- Model selection in requests
- Chat history management

### v1 API Tests (OpenAI-compatible)
- Chat completion with choices format: `/api/v1/chat`
- Chat status: `/api/v1/chat/status`
- History clearing: `/api/v1/chat/history`
- KB-enhanced chat: `/api/v1/chat/kb-enhanced`

### v0.3 API Tests (Clean Interface)
- Simple chat without provider details: `/api/v0.3/chat`
- Conversation management: `/api/v0.3/conversations`
- Streaming support with clean format
- No internal details exposed

### Knowledge Base Tests
- Direct KB health checks
- Search functionality: `/api/v0.2/kb/search`
- Context loading: `/api/v0.2/kb/context`
- Multitask operations: `/api/v0.2/kb/multitask`
- KB-integrated chat endpoints

## Test Dependencies and Fixtures

### Global Fixtures (`conftest.py`)
- `event_loop` - Async event loop for session
- `setup_test_environment` - Environment variable configuration

### Auth Fixtures (`fixtures/test_auth.py`)
- `TestAuthManager` - Unified auth management
- `JWTTestAuth` - JWT token generation
- `TestUserFactory` - Real user creation
- Pre-configured test users (default, admin, viewer)

### Web Test Fixtures (`web/conftest.py`)
- `client` - FastHTML test client
- `mock_gateway_client` - Mocked gateway client
- `mock_session` - Session management mocks

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Clean up created resources
- Don't rely on test execution order

### 2. Authentication Testing
- Use `TestAuthManager` for consistent auth
- Unit tests: JWT-only authentication
- Integration/E2E: Real Supabase when possible

### 3. Error Testing
- Test both success and failure paths
- Verify error messages are user-friendly
- Check proper HTTP status codes

### 4. Performance Considerations
- Set appropriate timeouts (30s for LLM calls)
- Use parallel execution for speed
- Mock expensive operations in unit tests

### 5. Docker Testing
- Use service names for internal communication
- Verify services are healthy before testing
- Handle connection errors gracefully

## Common Testing Scenarios

### 1. Testing Authentication Flow
```python
def test_login_endpoint_is_public(self, client):
    response = client.post("/auth/login", data={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code != 401  # Should not require auth
```

### 2. Testing Chat with Context
```python
async def test_conversation_context(self, gateway_url, headers):
    # Create conversation
    create_response = await client.post(
        f"{gateway_url}/api/v0.3/conversations",
        headers=headers,
        json={"title": "Test conversation"}
    )
    conversation_id = create_response.json()["conversation_id"]
    
    # Send messages with context
    # ... test context preservation
```

### 3. Testing KB Integration
```python
async def test_kb_enhanced_chat(self, gateway_url, headers):
    response = await client.post(
        f"{gateway_url}/api/v1/chat/kb-enhanced",
        headers=headers,
        json={"message": "Search KB for consciousness"}
    )
    # Verify KB tools were used
```

### 4. Testing Error Handling
```python
def test_registration_password_validation(self, client, mock_gateway_client):
    mock_gateway_client.register.side_effect = Exception(
        'Service error: {"detail": "Password must be at least 6 characters"}'
    )
    response = client.post("/auth/register", data={
        "email": "test@example.com",
        "password": "short"
    })
    assert "at least 6 characters" in response.text.lower()
```

## Debugging Failed Tests

### 1. Check Test Logs
```bash
# View test output
tail -f test-run-*.log

# Check test progress
./scripts/check-test-progress.sh
```

### 2. Run Specific Tests
```bash
# Run single test file
./scripts/pytest-for-claude.sh tests/unit/test_auth_flow.py

# Run specific test method
./scripts/pytest-for-claude.sh tests/unit/test_auth_flow.py::TestAuthenticationFlow::test_login_endpoint_is_public
```

### 3. Common Issues
- **Timeout errors**: Increase timeout in httpx.AsyncClient
- **Auth failures**: Check if API_KEY or JWT_SECRET is set
- **Connection errors**: Verify services are running
- **Import errors**: Check if running in correct container

## Future Improvements

1. **Coverage Analysis**: Add test coverage reporting
2. **Performance Testing**: Add dedicated performance test suite
3. **Load Testing**: Test system under concurrent load
4. **Security Testing**: Add security-focused test scenarios
5. **Visual Regression**: Add screenshot comparison for UI