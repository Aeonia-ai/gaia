# Unit Test Best Practices for Gaia Platform Microservices

## Overview

Unit tests in the Gaia Platform should focus on testing individual components in isolation, without external dependencies. This guide aligns with our [Testing Philosophy](../current/development/testing-philosophy.md) and complements our [Comprehensive Service Testing Strategy](../current/development/comprehensive-service-testing-strategy.md).

## Core Testing Principles

### 🎯 Gaia Testing Philosophy
- **Automated tests over manual curl commands** - Knowledge lives in tests
- **No mocks in E2E tests** - Real authentication with TestUserFactory only
- **Use pytest-for-claude.sh** - Avoids 2-minute timeout in Claude Code
- **Security-first testing** - OWASP Top 10 compliance required

## The Test Pyramid for Gaia Platform

```
         /\
        /  \  E2E Tests (10-15%)
       /----\  - Real Supabase auth (NO MOCKS!)
      /      \  - Full user journeys
     /--------\  - Browser testing (Playwright)
    /          \  Integration Tests (25-35%)
   /------------\  - Service boundaries
  /              \  - Docker networking
 /                \  - Real databases
/                  \  Unit Tests (50-65%)
/____________________\  - Pure functions
                        - Business logic
                        - No external calls
```

### Test Execution Architecture
```
All tests run in Docker containers via:
./scripts/pytest-for-claude.sh → docker compose run --rm test → pytest

This provides:
- Consistent environment
- Service access (gateway:8000, auth-service:8000, etc.)
- Proper dependencies (Playwright, Redis, PostgreSQL)
```

## What Makes a Good Unit Test?

### F.I.R.S.T Principles

- **Fast**: <100ms per test
- **Isolated**: No external dependencies
- **Repeatable**: Same result every time
- **Self-validating**: Pass/fail without manual inspection
- **Timely**: Written with or before the code

## Unit Testing Guidelines for Gaia Microservices

### ✅ DO Unit Test

1. **Pure Business Logic (Chat Service Example)**
   ```python
   # app/services/chat/utils.py
   def calculate_token_cost(tokens: int, model: str) -> float:
       rates = {"gpt-4": 0.03, "claude-3": 0.025, "gpt-3.5": 0.002}
       return (tokens / 1000) * rates.get(model, 0.002)
   
   # tests/unit/test_chat_utils.py
   def test_calculate_token_cost():
       assert calculate_token_cost(1000, "gpt-4") == 0.03
       assert calculate_token_cost(500, "claude-3") == 0.0125
       assert calculate_token_cost(2000, "unknown") == 0.004  # default rate
   ```

2. **Data Validation (Auth Service Example)**
   ```python
   # app/services/auth/validators.py
   def validate_password_strength(password: str) -> tuple[bool, str]:
       if len(password) < 8:
           return False, "Password must be at least 8 characters"
       if not any(c.isupper() for c in password):
           return False, "Password must contain uppercase letter"
       if not any(c.isdigit() for c in password):
           return False, "Password must contain a number"
       return True, "Password is strong"
   
   # tests/unit/test_auth_validators.py
   def test_password_validation():
       assert validate_password_strength("weak")[0] == False
       assert validate_password_strength("WeakPass")[0] == False
       assert validate_password_strength("StrongPass123")[0] == True
   ```

3. **Error Response Formatting (Gateway Example)**
   ```python
   # app/services/gateway/errors.py
   def format_gateway_error(service: str, error: Exception) -> dict:
       return {
           "error": {
               "type": type(error).__name__,
               "message": str(error),
               "service": service,
               "timestamp": datetime.utcnow().isoformat()
           }
       }
   
   # tests/unit/test_gateway_errors.py
   def test_error_formatting():
       error = ValueError("Invalid request")
       response = format_gateway_error("chat-service", error)
       assert response["error"]["type"] == "ValueError"
       assert response["error"]["service"] == "chat-service"
       assert "timestamp" in response["error"]
   ```

4. **KB Path Sanitization (KB Service Example)**
   ```python
   # app/services/kb/utils.py
   def sanitize_file_path(path: str) -> str:
       # Remove directory traversal attempts
       path = path.replace("../", "").replace("..\\", "")
       # Remove null bytes
       path = path.replace("\x00", "")
       # Ensure relative path
       return path.lstrip("/")
   
   # tests/unit/test_kb_utils.py
   def test_path_sanitization():
       assert sanitize_file_path("../../../etc/passwd") == "etc/passwd"
       assert sanitize_file_path("/absolute/path/file.txt") == "absolute/path/file.txt"
       assert sanitize_file_path("file\x00.txt") == "file.txt"
   ```

5. **Service Discovery (Configuration Example)**
   ```python
   # app/shared/config.py
   def get_service_url(service_name: str, environment: str = "dev") -> str:
       if environment == "local":
           ports = {"auth": 8001, "chat": 8002, "kb": 8003}
           return f"http://{service_name}-service:{ports.get(service_name, 8000)}"
       return f"https://gaia-{service_name}-{environment}.fly.dev"
   
   # tests/unit/test_service_discovery.py
   def test_service_url_generation():
       assert get_service_url("auth", "local") == "http://auth-service:8001"
       assert get_service_url("chat", "dev") == "https://gaia-chat-dev.fly.dev"
       assert get_service_url("kb", "prod") == "https://gaia-kb-prod.fly.dev"
   ```

### ❌ DON'T Unit Test (These Belong in Integration/E2E)

1. **Supabase Authentication Operations**
   ```python
   # This belongs in integration tests - requires real Supabase
   async def test_supabase_user_creation():
       supabase = get_supabase_client()
       user = await supabase.auth.sign_up({
           "email": "test@example.com",
           "password": "TestPass123!"
       })
       assert user.id is not None
   ```

2. **Inter-Service API Calls**
   ```python
   # This belongs in integration tests - requires service networking
   async def test_gateway_auth_coordination():
       async with httpx.AsyncClient() as client:
           response = await client.post(
               "http://gateway:8000/api/v0.2/auth/validate",
               headers={"X-API-Key": "test-key"}
           )
           assert response.status_code == 200
   ```

3. **Redis Cache Operations**
   ```python
   # This belongs in integration tests - requires Redis
   async def test_chat_history_caching():
       redis_client = await get_redis_client()
       await redis_client.set("chat:123", json.dumps({"messages": []}))
       cached = await redis_client.get("chat:123")
       assert cached is not None
   ```

4. **KB Git Sync Operations**
   ```python
   # This belongs in integration tests - requires Git repo
   async def test_kb_git_pull():
       kb_service = KBService()
       result = await kb_service.sync_from_git()
       assert result.files_updated > 0
   ```

5. **Real LLM Provider Calls**
   ```python
   # This belongs in integration tests - requires API keys & network
   async def test_openai_completion():
       response = await openai.ChatCompletion.create(
           model="gpt-3.5-turbo",
           messages=[{"role": "user", "content": "Hello"}]
       )
       assert response.choices[0].message.content is not None
   ```

## Mocking Strategies for Gaia Services

### 1. Mock Supabase Client (Auth Service)
```python
# tests/unit/conftest.py
@pytest.fixture
def mock_supabase():
    with patch('app.services.auth.get_supabase_client') as mock:
        client = MagicMock()
        client.auth.sign_in_with_password.return_value = {
            "user": {"id": "test-user-123", "email": "test@example.com"},
            "session": {"access_token": "test-jwt-token"}
        }
        mock.return_value = client
        yield client

# tests/unit/test_auth_logic.py
def test_login_success_handling(mock_supabase):
    # Test business logic without real Supabase
    result = handle_login_response("test@example.com", "password")
    assert result.user_id == "test-user-123"
    assert result.token == "test-jwt-token"
```

### 2. Mock LLM Providers (Chat Service)
```python
@pytest.fixture
def mock_openai():
    with patch('app.services.chat.providers.openai_client') as mock:
        mock.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Mocked response"))]
        )
        yield mock

def test_chat_response_formatting(mock_openai):
    # Test response formatting without real API calls
    formatted = format_llm_response("user prompt")
    assert formatted["role"] == "assistant"
    assert formatted["content"] == "Mocked response"
```

### 3. Mock Redis for Caching Logic
```python
@pytest.fixture
def mock_redis():
    with patch('app.shared.cache.get_redis_client') as mock:
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None  # Cache miss
        redis_mock.set.return_value = True
        mock.return_value = redis_mock
        yield redis_mock

async def test_cache_key_generation(mock_redis):
    # Test cache key logic without Redis
    key = generate_cache_key("chat", "user123", "prompt456")
    assert key == "gaia:chat:user123:prompt456"
    
    # Test cache miss handling
    result = await get_cached_response(key)
    assert result is None
    mock_redis.get.assert_called_once_with(key)
```

### 4. Mock Git Operations (KB Service)
```python
@pytest.fixture
def mock_git_repo():
    with patch('app.services.kb.git_sync.Repo') as mock:
        repo = MagicMock()
        repo.remotes.origin.pull.return_value = [
            MagicMock(note="Updated 3 files")
        ]
        mock.return_value = repo
        yield repo

def test_git_sync_status_parsing(mock_git_repo):
    # Test sync logic without real Git
    status = parse_git_sync_result()
    assert status.files_updated == 3
    assert status.success == True
```

### 5. Mock Time for JWT Expiration
```python
@pytest.fixture
def fixed_time():
    with freeze_time("2024-01-01 12:00:00"):
        yield

def test_jwt_expiration_calculation(fixed_time):
    # Test token expiration logic with fixed time
    token_data = create_jwt_payload(user_id="123", expires_in=3600)
    assert token_data["exp"] == 1704114000  # 2024-01-01 13:00:00 UTC
    assert token_data["iat"] == 1704110400  # 2024-01-01 12:00:00 UTC
```

## Gaia Test Directory Structure

```
tests/
├── unit/                           # Fast, isolated component tests
│   ├── test_auth_validators.py     # Password, email validation
│   ├── test_chat_utils.py          # Token calculation, formatting
│   ├── test_kb_sanitization.py     # Path sanitization, RBAC logic
│   ├── test_gateway_routing.py     # Route parsing, error formatting
│   └── test_shared_config.py       # Service discovery, config
├── integration/                    # Service interaction tests
│   ├── test_auth_integration.py    # Supabase auth flows
│   ├── test_chat_providers.py      # LLM provider integration
│   ├── test_kb_git_sync.py         # Git operations
│   ├── test_gateway_services.py    # Service coordination
│   └── test_redis_caching.py       # Cache operations
├── e2e/                           # Full user journey tests (NO MOCKS!)
│   ├── test_real_auth_e2e.py      # Real Supabase authentication
│   ├── test_chat_browser.py        # Playwright UI tests
│   └── test_full_workflow.py       # Complete user scenarios
├── security/                       # Security-focused tests
│   ├── test_sql_injection.py       # SQL injection prevention
│   ├── test_xss_prevention.py      # XSS attack prevention
│   ├── test_auth_boundaries.py     # RBAC enforcement
│   └── test_rate_limiting.py       # DDoS protection
├── performance/                    # Load and performance tests
│   ├── test_response_times.py      # <200ms p95 requirement
│   └── test_concurrent_users.py    # Concurrent access
├── fixtures/                       # Shared test utilities
│   ├── auth.py                    # TestUserFactory
│   ├── screenshot_cleanup.py      # Browser test cleanup
│   └── mock_providers.py          # Common mocks
└── conftest.py                    # Pytest configuration
```

## Common Anti-Patterns to Avoid in Gaia

### 1. Testing FastAPI Framework Internals
```python
# ❌ Bad - Testing FastAPI routing setup
def test_gateway_routes_exist():
    from app.services.gateway.main import app
    assert any(route.path == "/api/v0.2/chat" for route in app.routes)

# ✅ Good - Test route handler logic
def test_chat_route_validation():
    # Test the validation logic, not the framework
    valid = validate_chat_request({"messages": [{"role": "user", "content": "Hi"}]})
    assert valid == True
    
    invalid = validate_chat_request({"messages": []})
    assert invalid == False
```

### 2. Testing Supabase SDK Behavior
```python
# ❌ Bad - Testing that Supabase SDK works
def test_supabase_client_creation():
    client = create_supabase_client(url="...", key="...")
    assert client is not None
    assert hasattr(client, "auth")

# ✅ Good - Test your auth logic
def test_jwt_token_extraction():
    # Test your business logic around auth
    token_data = extract_user_from_jwt("mock.jwt.token")
    assert token_data["user_id"] == "expected-id"
```

### 3. Overuse of Docker in Unit Tests
```python
# ❌ Bad - Spinning up containers for unit tests
@pytest.mark.unit
async def test_with_real_redis():
    # This is an integration test!
    redis = await start_redis_container()
    await redis.set("key", "value")
    assert await redis.get("key") == "value"

# ✅ Good - Mock external dependencies
@pytest.mark.unit
async def test_cache_key_logic(mock_redis):
    # Test the logic, not the infrastructure
    key = build_cache_key("user", "123", "action")
    assert key == "gaia:user:123:action"
```

### 4. Testing Database Queries in Unit Tests
```python
# ❌ Bad - Real database queries in unit tests
def test_user_query():
    with get_db() as session:
        user = session.query(User).filter_by(email="test@example.com").first()
        assert user is not None

# ✅ Good - Test query building logic
def test_build_user_filter():
    # Test the logic that builds queries
    filters = build_user_filters(email="test@example.com", active=True)
    assert filters["email"] == "test@example.com"
    assert filters["is_active"] == True
```

## Security Considerations in Unit Tests

### Testing Input Validation
```python
# tests/unit/test_security_validators.py
def test_sql_injection_prevention():
    """Ensure malicious inputs are sanitized"""
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "../../../etc/passwd"
    ]
    
    for input_str in malicious_inputs:
        sanitized = sanitize_user_input(input_str)
        assert "DROP TABLE" not in sanitized
        assert ".." not in sanitized
        assert sanitized != input_str

def test_xss_prevention():
    """Ensure XSS payloads are escaped"""
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>"
    ]
    
    for payload in xss_payloads:
        escaped = escape_html_content(payload)
        assert "<script>" not in escaped
        assert "javascript:" not in escaped
        assert "onerror=" not in escaped
```

### Testing RBAC Logic
```python
def test_permission_checking():
    """Test role-based access control logic"""
    # Test permission matrix
    assert check_permission("reader", "kb:read") == True
    assert check_permission("reader", "kb:write") == False
    assert check_permission("editor", "kb:write") == True
    assert check_permission("admin", "system:config") == True

def test_scope_validation():
    """Test API key scope validation"""
    api_key_scopes = ["chat:read", "kb:read"]
    
    assert validate_scope(api_key_scopes, "chat:read") == True
    assert validate_scope(api_key_scopes, "chat:write") == False
    assert validate_scope(api_key_scopes, "kb:write") == False
```

## Migration Strategy for Existing Tests

1. **Identify Misplaced Tests**
   ```bash
   # Find integration tests in unit directory
   grep -r "httpx\|requests\|asyncio\|database" tests/unit/
   ```

2. **Create Proper Structure**
   ```bash
   mkdir -p tests/integration/auth
   mkdir -p tests/integration/database
   ```

3. **Move Tests**
   ```bash
   # Move integration tests
   mv tests/unit/test_auth_integration.py tests/integration/auth/
   ```

4. **Add Appropriate Markers**
   ```python
   # In integration tests
   @pytest.mark.integration
   @pytest.mark.requires_db
   async def test_user_persistence():
       ...
   ```

5. **Update CI/CD**
   ```yaml
   # Run unit tests on every commit
   - run: pytest tests/unit -v
   
   # Run integration tests less frequently
   - run: pytest tests/integration -v -m "not slow"
   ```

## Performance Targets & Coverage Requirements

### Execution Time Goals
- **Unit test suite**: < 30 seconds total
- **Single unit test**: < 100ms  
- **Test file**: < 5 seconds
- **Feedback loop**: < 1 minute (save → test → result)

### Coverage Requirements (Per Service)
- **Overall**: 80% minimum
- **Critical paths** (auth, payments): 95% minimum
- **New code**: 90% minimum
- **Security code**: 100% required

### Service-Specific Coverage Goals
```
Gateway Service: 85% ✅ (Target: 90%)
Auth Service:    90% ✅ (Target: 95%)
Chat Service:    75% ⚠️ (Target: 85%)
KB Service:      40% ❌ (Target: 80%)
Asset Service:   60% ⚠️ (Target: 80%)
Web Service:     80% ✅ (Target: 85%)
```

## Running Unit Tests in Gaia

### Using pytest-for-claude.sh (Recommended)
```bash
# Run all unit tests (avoids Claude Code 2-minute timeout)
./scripts/pytest-for-claude.sh tests/unit/ -v

# Run specific service unit tests
./scripts/pytest-for-claude.sh tests/unit/test_auth_validators.py -v

# Run with coverage report
./scripts/pytest-for-claude.sh tests/unit/ --cov=app --cov-report=html

# Monitor test progress
./scripts/check-test-progress.sh
```

### Direct pytest (Only for Quick Tests)
```bash
# Only use for single, fast tests that complete in <2 minutes
docker compose run --rm test pytest tests/unit/test_auth_validators.py::test_password_validation -v
```

### Coverage Reporting
```bash
# Generate HTML coverage report
./scripts/pytest-for-claude.sh tests/unit/ --cov=app --cov-report=html
open htmlcov/index.html

# Terminal coverage summary
./scripts/pytest-for-claude.sh tests/unit/ --cov=app --cov-report=term-missing
```

## Tools and Libraries

### Essential for Gaia
- `pytest` - Test framework
- `pytest-asyncio` - Async test support (required for services)
- `pytest-mock` - Mocking utilities
- `freezegun` - Time mocking (JWT testing)
- `pytest-cov` - Coverage reporting
- `pytest-xdist` - Parallel test execution

### Security Testing
- `bandit` - Python security linting
- `safety` - Dependency vulnerability scanning

### Gaia-Specific Fixtures
- `TestUserFactory` - Consistent test user creation
- `mock_supabase` - Supabase client mocking
- `mock_redis` - Redis client mocking
- `screenshot_cleanup` - Playwright test cleanup

## Summary: Unit Testing in Gaia

### Key Takeaways
1. **Unit tests should be FAST and ISOLATED** - No external dependencies
2. **Use pytest-for-claude.sh** - Avoids timeouts in Claude Code
3. **Mock external services** - Supabase, Redis, LLMs, Git
4. **Test business logic** - Not framework code or infrastructure
5. **Security matters** - Validate and sanitize in unit tests
6. **Coverage goals** - 80% overall, 95% for critical paths

### Quick Decision Guide
```
Is it a unit test?
├─ Does it need a database? → Integration test
├─ Does it call external APIs? → Integration test  
├─ Does it need Docker networking? → Integration test
├─ Does it test pure logic? → ✅ Unit test
├─ Does it validate/transform data? → ✅ Unit test
└─ Does it format responses? → ✅ Unit test
```

### Common Commands
```bash
# Run unit tests for a service
./scripts/pytest-for-claude.sh tests/unit/test_auth_*.py -v

# Check coverage for a service
./scripts/pytest-for-claude.sh tests/unit/ --cov=app.services.auth

# Run security-focused unit tests
./scripts/pytest-for-claude.sh tests/unit/ -k "injection or xss or rbac"
```

## Related Documentation

- [Testing Philosophy](../current/development/testing-philosophy.md) - Overall testing approach
- [E2E Real Auth Testing](../current/development/e2e-real-auth-testing.md) - E2E test requirements
- [Comprehensive Service Testing](../current/development/comprehensive-service-testing-strategy.md) - Service-specific patterns
- [Security Testing Strategy](../current/development/security-testing-strategy.md) - Security test requirements
- [Testing and Quality Assurance](../current/development/testing-and-quality-assurance.md) - Quality standards

---

**Last Updated**: January 2025  
**Applies To**: All Gaia Platform microservices  
**Status**: Active best practices guide