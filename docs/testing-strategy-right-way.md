# Testing Strategy: The Right Way

## Overview

This document outlines our three-tier testing strategy that ensures code quality while maintaining fast development cycles.

## Testing Pyramid

```
         /\
        /E2E\        <- Real users, real services, real data
       /------\
      /  INT   \     <- Service interactions, some mocking
     /----------\
    /    UNIT    \   <- Fast, isolated, heavily mocked
   /--------------\
```

## 1. Unit Tests (Base of Pyramid)

**Purpose**: Test individual components in isolation

**Characteristics**:
- Heavy mocking of dependencies
- Run in milliseconds
- Test business logic, not integration
- Run on every commit

**Example**: Testing auth validation logic
```python
def test_jwt_validation():
    """Test JWT token validation logic"""
    mock_jwt = "fake.jwt.token"
    with patch('jwt.decode') as mock_decode:
        mock_decode.return_value = {"sub": "user-123"}
        result = validate_jwt(mock_jwt)
        assert result.user_id == "user-123"
```

**When to Use**:
- Testing pure functions
- Testing business logic
- Testing error handling
- Testing edge cases

## 2. Integration Tests (Middle Layer)

**Purpose**: Test how components work together

**Characteristics**:
- Some real services, some mocked
- Run in seconds
- Test service boundaries
- Run on PR creation

**Example**: Testing gateway → auth service
```python
async def test_gateway_auth_integration():
    """Test gateway correctly calls auth service"""
    # Mock auth service response
    with patch('gateway.auth_client.validate') as mock:
        mock.return_value = {"valid": True}
        
        # Real gateway logic
        response = await gateway.validate_request(token)
        assert response.status_code == 200
```

**When to Use**:
- Testing API contracts
- Testing service communication
- Testing database operations
- Testing external API integration

## 3. End-to-End Tests (Top of Pyramid)

**Purpose**: Test complete user journeys

**Characteristics**:
- NO MOCKING - use real services
- Run in minutes
- Test like a real user
- Run before deployment

**Example**: Our Supabase E2E test
```python
async def test_real_e2e_login_with_supabase():
    """Test real login flow with actual Supabase user"""
    factory = TestUserFactory()
    user = factory.create_verified_test_user()
    
    try:
        # Real browser automation
        await page.goto("/login")
        await page.fill('input[name="email"]', user["email"])
        await page.fill('input[name="password"]', user["password"])
        await page.click('button[type="submit"]')
        
        # Verify real navigation
        await page.wait_for_url('**/chat')
        
        # Send real message
        await page.fill('input[name="message"]', "Hello!")
        await page.keyboard.press('Enter')
        
        # Wait for real AI response
        messages = await page.query_selector_all('#messages > div')
        assert len(messages) > 1
        
    finally:
        factory.cleanup_all()
```

**When to Use**:
- Testing critical user paths
- Testing before releases
- Testing after major changes
- Reproducing user-reported bugs

## Implementation Guidelines

### Unit Tests
- Use `pytest.mark.unit`
- Mock all external dependencies
- Keep under 100ms per test
- Aim for 80%+ code coverage

### Integration Tests
- Use `pytest.mark.integration`
- Mock only external services (3rd party APIs)
- Keep under 5 seconds per test
- Test service boundaries

### E2E Tests
- Use `pytest.mark.e2e`
- NO MOCKING (except for payment providers)
- Use real test data with cleanup
- Test complete user journeys

## Running Tests

```bash
# Unit tests (fast - run frequently)
pytest -m unit

# Integration tests (medium - run on commits)
pytest -m integration

# E2E tests (slow - run before deploy)
RUN_BROWSER_TESTS=true pytest -m e2e

# All tests
pytest

# Specific service tests
pytest tests/web/
pytest tests/gateway/
```

## CI/CD Pipeline

1. **On Every Commit**: Unit tests only (< 30 seconds)
2. **On PR Creation**: Unit + Integration tests (< 3 minutes)
3. **Before Merge**: All tests including E2E (< 10 minutes)
4. **Before Deploy**: Full E2E suite with multiple browsers

## Test Data Management

### Unit Tests
- Use fixtures with fake data
- No external dependencies

### Integration Tests
- Use test database with known state
- Mock external APIs
- Clean up after tests

### E2E Tests
- Create real test users (with cleanup)
- Use dedicated test accounts
- Always clean up test data

## Common Patterns

### 1. Test User Factory (E2E)
```python
factory = TestUserFactory()
user = factory.create_verified_test_user()
try:
    # Run tests
    pass
finally:
    factory.cleanup_all()
```

### 2. Mock Authentication (Unit/Integration)
```python
@patch('auth.validate_token')
def test_protected_endpoint(mock_auth):
    mock_auth.return_value = {"user_id": "123"}
    response = client.get("/protected")
    assert response.status_code == 200
```

### 3. Browser Automation (E2E)
```python
async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    # Test real user interactions
```

## Anti-Patterns to Avoid

1. **Mocking in E2E tests** - Defeats the purpose
2. **Not cleaning up test data** - Causes flaky tests
3. **Testing implementation details** - Test behavior, not internals
4. **Overly complex mocks** - Sign you need integration tests
5. **Skipping E2E tests** - "Too slow" is not an excuse

## Benefits of This Approach

1. **Fast Feedback**: Unit tests run in seconds
2. **High Confidence**: E2E tests catch real issues
3. **Maintainable**: Clear boundaries between test types
4. **Debugging**: Failed E2E test → Write unit test to isolate
5. **Documentation**: Tests show how system should work

## Conclusion

Following this three-tier approach ensures:
- Fast development cycles (unit tests)
- Component reliability (integration tests)
- User experience quality (E2E tests)

Remember: If you're mocking everything in your "E2E" tests, they're not E2E tests!