# Testing Patterns and Best Practices

This guide documents the testing patterns, best practices, and lessons learned from improving the GAIA test infrastructure.

## Table of Contents
1. [Testing Philosophy](#testing-philosophy)
2. [Unit Testing Patterns](#unit-testing-patterns)
3. [Integration Testing Patterns](#integration-testing-patterns)
4. [Browser Testing Patterns](#browser-testing-patterns)
5. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)
6. [Test Organization](#test-organization)
7. [Performance Considerations](#performance-considerations)

## Testing Philosophy

### Core Principles
1. **Test Behavior, Not Implementation**
   - Focus on what the code does, not how it does it
   - Tests should survive refactoring
   - Avoid testing internal details

2. **Use Real Components When Possible**
   - Prefer real authentication over mocks in E2E tests
   - Use actual database operations in integration tests
   - Mock only external dependencies and slow operations

3. **Tests as Documentation**
   - Test names should describe the behavior being tested
   - Tests should demonstrate how to use the component
   - Include edge cases and error scenarios

## Unit Testing Patterns

### Basic Structure
```python
class TestComponent:
    """Test the Component functionality"""
    
    @pytest.fixture
    def component(self):
        """Create a fresh instance for each test"""
        return Component()
    
    def test_behavior_description(self, component):
        """Test that component behaves correctly when..."""
        # Arrange
        input_data = {"key": "value"}
        
        # Act
        result = component.process(input_data)
        
        # Assert
        assert result.status == "success"
        assert result.data == expected_data
```

### Async Testing
```python
@pytest.mark.asyncio
async def test_async_operation(self):
    """Test async operations properly"""
    # Use async fixtures
    async with create_async_resource() as resource:
        result = await resource.async_method()
        assert result is not None
```

### Mocking External Dependencies
```python
@patch('app.services.external.ExternalAPI')
async def test_with_mock(self, mock_api):
    """Test component with mocked external dependency"""
    # Setup mock
    mock_api.fetch_data.return_value = {"status": "ok"}
    
    # Test behavior
    result = await component.process_with_external()
    
    # Verify mock was called correctly
    mock_api.fetch_data.assert_called_once_with(expected_params)
```

### Testing Error Scenarios
```python
async def test_handles_external_failure_gracefully(self):
    """Test component handles external service failures"""
    with patch('app.services.external.API') as mock:
        mock.call.side_effect = Exception("Service unavailable")
        
        # Should not raise, but handle gracefully
        result = await component.safe_operation()
        assert result.fallback_used is True
```

## Integration Testing Patterns

### Database Testing
```python
@pytest.fixture
async def db_session():
    """Provide a test database session"""
    # Use test database or rollback transactions
    async with test_database.session() as session:
        yield session
        # Cleanup happens automatically

async def test_database_operation(db_session):
    """Test actual database operations"""
    # Create test data
    user = User(email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    
    # Test query
    result = await db_session.query(User).filter_by(email="test@example.com").first()
    assert result is not None
```

### API Testing
```python
@pytest.fixture
async def client():
    """Create test client"""
    app = create_app(testing=True)
    async with TestClient(app) as client:
        yield client

async def test_api_endpoint(client):
    """Test API endpoint behavior"""
    response = await client.post("/api/v1/resource", json={"data": "test"})
    assert response.status_code == 201
    assert response.json()["id"] is not None
```

## Browser Testing Patterns

### Authentication Setup
```python
from tests.integration.web.browser_test_base import BrowserTestBase

class TestFeature(BrowserTestBase):
    @pytest.mark.asyncio
    async def test_authenticated_feature(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # Use base class helper for auth setup
            context = await self.setup_authenticated_context(browser)
            page = await context.new_page()
            
            # Setup standard mocks
            await self.setup_auth_mocks(page)
            await self.setup_chat_page_mock(page)
            
            # Test your feature
            await self.navigate_to_chat(page)
```

### Semantic Selectors
```python
# ❌ AVOID: Brittle CSS class selectors
await page.locator('.bg-red-500').click()
await page.locator('.flex.items-center.justify-between').first

# ✅ PREFER: Semantic selectors
await page.locator('[role="alert"]').click()
await page.locator('button[aria-label="Submit"]').click()
await page.locator('[data-testid="chat-input"]').fill("Hello")
await page.locator('text="Send message"').click()
```

### Waiting Strategies
```python
# ❌ AVOID: Fixed timeouts
await page.wait_for_timeout(5000)

# ✅ PREFER: Wait for specific conditions
await page.wait_for_selector('[data-loaded="true"]')
await expect(page.locator('#spinner')).to_be_hidden()
await page.wait_for_load_state('networkidle')
```

### HTMX Testing
```python
async def handle_htmx_request(route):
    """Handle HTMX requests properly"""
    if 'hx-request' in route.request.headers:
        # HTMX expects different headers
        await route.fulfill(
            status=200,
            headers={"HX-Redirect": "/success"},
            body="<div>Success</div>"
        )
    else:
        # Regular request
        await route.fulfill(
            status=303,
            headers={"Location": "/success"}
        )
```

## Common Pitfalls and Solutions

### 1. Session-Based Authentication
**Problem**: Setting cookies doesn't work with server-side sessions
```python
# ❌ This won't work
await context.add_cookies([{"name": "session", "value": "token"}])
```

**Solution**: Mock the session validation endpoint
```python
# ✅ Mock session validation
await page.route("**/api/session", lambda route: route.fulfill(
    json={"authenticated": True, "user": {"id": "123"}}
))
```

### 2. Playwright Syntax Errors
**Problem**: Incorrect async/await usage
```python
# ❌ Wrong
element = await page.locator('.class').first
```

**Solution**: Locators don't need await
```python
# ✅ Correct
element = page.locator('.class').first
await element.click()
```

### 3. Resource Exhaustion in Parallel Tests
**Problem**: Tests fail when run in parallel due to resource limits

**Solution**: Use proper test markers and configuration
```python
# Mark resource-intensive tests
@pytest.mark.resource_intensive
async def test_heavy_operation():
    pass

# Run with limited parallelism
# pytest -n 2  # Instead of -n auto
```

### 4. Flaky Async Tests
**Problem**: Race conditions in async code

**Solution**: Proper synchronization
```python
# ❌ Race condition
asyncio.create_task(background_operation())
result = await main_operation()  # May run before background task

# ✅ Proper synchronization
task = asyncio.create_task(background_operation())
result = await main_operation()
await task  # Ensure background task completes
```

## Test Organization

### Directory Structure
```
tests/
├── unit/                    # Fast, isolated unit tests
│   ├── test_services/       # Service layer tests
│   ├── test_models/         # Model/domain tests
│   └── test_utils/          # Utility function tests
├── integration/             # Tests with real dependencies
│   ├── api/                 # API endpoint tests
│   ├── web/                 # Browser/UI tests
│   └── database/            # Database integration tests
├── e2e/                     # Full end-to-end tests
└── fixtures/                # Shared test fixtures
    ├── auth.py              # Authentication fixtures
    └── data.py              # Test data fixtures
```

### Naming Conventions
- Test files: `test_<module_name>.py`
- Test classes: `Test<ComponentName>`
- Test methods: `test_<behavior>_when_<condition>`
- Fixtures: `<resource>` or `mock_<resource>`

### Test Markers
```python
# Mark tests for easy filtering
@pytest.mark.unit          # Fast unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.e2e          # End-to-end tests
@pytest.mark.slow         # Slow tests
@pytest.mark.asyncio      # Async tests
```

## Performance Considerations

### 1. Test Execution Speed
- **Unit tests**: Should complete in milliseconds
- **Integration tests**: Should complete in seconds
- **E2E tests**: May take longer but optimize where possible

### 2. Parallel Execution
```python
# Use pytest-xdist for parallel execution
# But be aware of resource limits

# Mark tests that can't run in parallel
@pytest.mark.serial
async def test_modifies_global_state():
    pass
```

### 3. Fixture Scope
```python
# Use appropriate fixture scope
@pytest.fixture(scope="session")  # Expensive setup, shared
async def database():
    pass

@pytest.fixture(scope="function")  # Fresh for each test
def mock_service():
    pass
```

### 4. Mock vs Real Components
- **Mock**: External APIs, slow operations, non-deterministic behavior
- **Real**: Database (with transactions), internal services, fast operations

## Testing Checklist

Before committing tests:
- [ ] Tests pass locally
- [ ] Tests are independent (can run in any order)
- [ ] Tests clean up after themselves
- [ ] No hardcoded values (ports, paths, credentials)
- [ ] Appropriate use of mocks vs real components
- [ ] Clear test names that describe behavior
- [ ] Both success and failure cases covered
- [ ] No brittle selectors in browser tests
- [ ] Async operations properly handled
- [ ] Resource usage is reasonable

## Continuous Improvement

1. **Monitor Test Metrics**
   - Track test execution time
   - Monitor flaky tests
   - Measure code coverage

2. **Regular Maintenance**
   - Update deprecated patterns
   - Remove obsolete tests
   - Refactor complex test setups

3. **Team Practices**
   - Code review test changes
   - Share testing patterns
   - Document new patterns as they emerge

## Conclusion

Good tests are an investment in code quality and developer productivity. They should:
- Give confidence that the code works
- Document how to use the code
- Catch regressions early
- Enable safe refactoring

By following these patterns and avoiding common pitfalls, we can maintain a robust and reliable test suite that supports rapid development while maintaining quality.