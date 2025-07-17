# Web Service Tests

This directory contains tests for the Gaia Platform web service, including authentication, chat interface, and error handling.

## Test Structure

```
tests/web/
├── __init__.py
├── test_auth_routes.py      # Unit tests for authentication routes
├── test_gateway_client.py   # Unit tests for gateway API client
├── test_auth_integration.py # Integration tests for full auth flow
├── test_error_handling.py   # Tests for error messages and user feedback
└── test_simple.py          # Basic test to verify setup
```

## Running Tests

### Prerequisites

The test environment needs FastHTML installed. To run web service tests:

1. **Option 1: Run tests inside the web service container**
   ```bash
   docker compose exec web-service pytest /app/tests/web -v
   ```

2. **Option 2: Install test dependencies**
   ```bash
   # In the test container, install FastHTML
   docker compose run test pip install python-fasthtml
   ```

### Test Commands

```bash
# Run all web tests
./scripts/test-web.sh

# Run only unit tests
./scripts/test-web.sh --unit

# Run integration tests
./scripts/test-web.sh --integration

# Run all tests with coverage
./scripts/test-web.sh --all --coverage

# Run specific test file
docker compose run test pytest tests/web/test_auth_routes.py -v

# Run specific test
docker compose run test pytest tests/web/test_error_handling.py::TestErrorHandling::test_error_message_component -v
```

## Test Categories

### Unit Tests (`pytest -m unit`)
- `test_auth_routes.py` - Tests authentication endpoints with mocked dependencies
- `test_gateway_client.py` - Tests gateway client methods
- `test_error_handling.py` - Tests error parsing and display

### Integration Tests (`pytest -m integration`)
- `test_auth_integration.py` - Tests full authentication flow with real services

## Test Coverage

The tests cover:

1. **Authentication Flow**
   - Dev user login (local development)
   - Real user login via Supabase
   - User registration
   - Logout functionality
   - Session management

2. **Error Handling**
   - Invalid email format
   - Weak passwords
   - Network errors
   - Malformed responses
   - Nested error parsing

3. **Gateway Communication**
   - Login/register API calls
   - Chat completion requests
   - JWT vs API key authentication
   - Error response handling

4. **UI Components**
   - Error message rendering
   - Success message rendering
   - HTML escaping
   - Form validation

## Mocking Strategy

Tests use mocking to isolate components:

```python
# Mock gateway client
with patch('app.services.web.utils.gateway_client.GaiaAPIClient') as mock_client:
    mock_instance = mock_client.return_value.__aenter__.return_value
    mock_instance.login.return_value = {"session": {...}, "user": {...}}
```

## Common Test Patterns

### Testing Error Messages
```python
# Simulate specific error
mock_instance.register.side_effect = Exception(
    'Service error: {"detail":"Please enter a valid email address"}'
)

# Verify error is displayed correctly
assert "Please enter a valid email address" in response.text
```

### Testing Authentication
```python
# Test successful login
response = client.post("/auth/login", data={
    "email": "test@example.com",
    "password": "password123"
})
assert response.status_code == 303  # Redirect to chat
```

## Adding New Tests

When adding new features:

1. Add unit tests for individual components
2. Add integration tests for end-to-end flows
3. Add error handling tests for edge cases
4. Mark tests appropriately (`@pytest.mark.unit` or `@pytest.mark.integration`)
5. Update this README with new test information