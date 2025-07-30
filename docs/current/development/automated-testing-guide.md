# Automated Testing Guide

This guide covers the comprehensive automated test suite for the Gaia Platform, which replaces manual testing scripts with robust, automated testing.

## Overview

The Gaia Platform uses a **pytest-based automated test suite** that provides:
- **Consistent, repeatable results** across all environments
- **Comprehensive coverage** of all major functionality  
- **CI/CD integration** for automated validation
- **Fast feedback** during development
- **Regression prevention** through continuous testing

## Quick Start

### Run All Tests
```bash
./scripts/test-automated.py all
```

### Common Test Categories
```bash
./scripts/test-automated.py health         # System health checks
./scripts/test-automated.py chat-basic     # Core chat functionality  
./scripts/test-automated.py kb            # Knowledge Base tests
./scripts/test-automated.py providers     # Provider/model tests
./scripts/test-automated.py comprehensive # Full integration tests
```

### Development Workflow
```bash
# After making changes
./scripts/test-automated.py health         # Quick system check
./scripts/test-automated.py chat-basic     # Verify core functionality

# Before committing
./scripts/test-automated.py core          # Run core test suite
./scripts/test-automated.py all           # Full validation (recommended)
```

## Test Categories

### 🏥 Health & Status Tests
**Purpose**: Verify system health and service status

```bash
./scripts/test-automated.py health        # Core system health
./scripts/test-automated.py status        # Service status checks
./scripts/test-automated.py kb-health     # KB repository status
```

**What's Tested**:
- Gateway service health and service discovery
- Individual service health endpoints
- Database connectivity and responsiveness
- Redis caching layer functionality
- KB repository status and file count

### 💬 Chat & Communication Tests
**Purpose**: Validate chat endpoints and conversation functionality

```bash
./scripts/test-automated.py chat-basic    # Core v0.2 and v1 chat
./scripts/test-automated.py chat          # All chat functionality
./scripts/test-automated.py chat-all      # Comprehensive chat tests
```

**What's Tested**:
- v0.2 chat endpoint (simple response format)
- v1 chat endpoint (OpenAI-compatible format)
- Context preservation across conversation turns
- Response format validation
- Chat history management
- Authentication requirements

### 🧠 Knowledge Base Tests
**Purpose**: Verify KB functionality and integration

```bash
./scripts/test-automated.py kb            # All KB tests
./scripts/test-automated.py kb-health     # KB health and status
```

**What's Tested**:
- KB service direct health checks
- Repository status and file information
- KB search functionality (if available)
- KB context loading
- Integration with chat endpoints
- Git repository synchronization status

### 🔧 Provider & Model Tests
**Purpose**: Test provider and model endpoint functionality

```bash
./scripts/test-automated.py providers     # Provider endpoints
./scripts/test-automated.py models        # Model endpoints
```

**What's Tested**:
- Provider listing and information
- Model availability and details
- Provider health status
- Model recommendation functionality
- Provider-model relationship consistency

### 🔐 Security & Authentication Tests
**Purpose**: Validate authentication and security measures

```bash
./scripts/test-automated.py auth          # Authentication tests
```

**What's Tested**:
- Valid API key acceptance
- Invalid API key rejection
- Unauthenticated request blocking
- Authentication security measures
- JWT token validation (when available)

### 🔄 Integration & Performance Tests
**Purpose**: End-to-end system validation and performance monitoring

```bash
./scripts/test-automated.py comprehensive # Full system integration
./scripts/test-automated.py integration   # E2E integration tests
./scripts/test-automated.py performance   # Basic performance tests
./scripts/test-automated.py compatibility # API compatibility tests
```

**What's Tested**:
- Complete conversation flows with context
- Cross-service integration
- API version compatibility (v0.2 vs v1)
- Basic response time monitoring
- End-to-end authentication flows

## Test Architecture

### Test Files Structure
```
tests/
├── test_working_endpoints.py           # Core working functionality (11 tests)
├── test_api_endpoints_comprehensive.py # Full endpoint coverage (9 tests)
├── test_v02_chat_api.py                # Detailed v0.2 API tests (14 tests)
├── test_provider_model_endpoints.py    # Provider/model testing (11 tests)
├── test_kb_endpoints.py                # KB functionality (12 tests)
└── test_comprehensive_suite.py         # System integration (8 tests)
```

### Test Environment
- **Docker Integration**: All tests run in Docker environment for consistency
- **Service Connectivity**: Tests use Docker internal URLs (`http://gateway:8000`)
- **Authentication**: Uses test API keys and headers
- **Isolation**: Each test is independent and can run individually

### Response Format Handling
The test suite properly validates different API response formats:

**v0.2 Format (Simple)**:
```json
{
  "response": "AI response content here"
}
```

**v1 Format (OpenAI-compatible)**:
```json
{
  "choices": [
    {
      "message": {
        "content": "AI response content here"
      }
    }
  ]
}
```

## Advanced Usage

### Environment-Specific Testing
```bash
./scripts/test-automated.py --environment dev health
./scripts/test-automated.py --environment staging comprehensive
```

### Quiet Mode (Minimal Output)
```bash
./scripts/test-automated.py --quiet all
```

### Help and Available Commands
```bash
./scripts/test-automated.py help
```

## Test Development Guidelines

### Adding New Tests

1. **Choose the Right Test File**:
   - Core functionality → `test_working_endpoints.py`
   - Comprehensive coverage → `test_api_endpoints_comprehensive.py`  
   - Specific API version → `test_v02_chat_api.py`
   - KB functionality → `test_kb_endpoints.py`
   - Integration scenarios → `test_comprehensive_suite.py`

2. **Follow Test Patterns**:
   ```python
   async def test_new_functionality(self, gateway_url, headers):
       """Test description of what this validates."""
       async with httpx.AsyncClient() as client:
           response = await client.post(
               f"{gateway_url}/api/endpoint",
               headers=headers,
               json={"test": "data"}
           )
           
           assert response.status_code == 200
           data = response.json()
           assert "expected_field" in data
           
           logger.info(f"Test result: {data}")
   ```

3. **Use Proper Assertions**:
   - Test both success and failure cases
   - Validate response structure and content
   - Check for expected vs actual behavior
   - Log useful information for debugging

### Test Fixtures
Standard fixtures available in all test files:
- `gateway_url`: Gateway service URL (`http://gateway:8000`)
- `kb_url`: KB service direct URL (`http://kb-service:8000`)
- `api_key`: Test API key from environment
- `headers`: Standard authentication headers

### Error Handling
Tests are designed to handle various service states:
- **200 OK**: Endpoint working as expected
- **404 Not Found**: Endpoint not implemented (acceptable for some features)
- **401/403**: Authentication errors (expected for auth tests)
- **500**: Server errors (logged but may be acceptable for optional features)

## Integration with CI/CD

### GitHub Actions Integration
```yaml
- name: Run Automated Tests
  run: |
    docker compose up -d
    ./scripts/test-automated.py all
```

### Pre-commit Testing
```bash
# Add to your pre-commit workflow
./scripts/test-automated.py core
```

### Deployment Validation
```bash
# After deployment
./scripts/test-automated.py health
./scripts/test-automated.py comprehensive
```

## Troubleshooting

### Common Issues

**Tests Timing Out**:
- Ensure Docker services are running: `docker compose ps`
- Check service health: `./scripts/test-automated.py health`
- Increase timeout in test files if needed

**Authentication Failures**:
- Verify API key in `.env` file
- Check service authentication setup
- Run auth-specific tests: `./scripts/test-automated.py auth`

**Service Connectivity Issues**:
- Ensure services are accessible via Docker network
- Check Docker compose network configuration
- Verify service URLs in test fixtures

**Inconsistent Results**:
- Tests should be deterministic - investigate flaky tests
- Check for race conditions or timing dependencies
- Ensure proper test isolation

### Debugging Failed Tests
```bash
# Run specific test with verbose output
./scripts/test-automated.py -v specific-test-name

# Run single test file
docker compose run --rm test python -m pytest tests/test_file.py -v

# Run with pdb debugging
docker compose run --rm test python -m pytest tests/test_file.py --pdb
```

## Migration from Manual Scripts

### Old vs New Approach

**Before (Manual)**:
```bash
./scripts/test.sh --local health
./scripts/test.sh --local chat "test message"
./scripts/test.sh --local providers
```

**After (Automated)**:
```bash
./scripts/test-automated.py health
./scripts/test-automated.py chat-basic  
./scripts/test-automated.py providers
```

### Benefits of Automation

1. **Consistency**: Same results every time, no human interpretation needed
2. **Speed**: Targeted test execution vs full manual script runs
3. **Coverage**: Tests functionality that manual scripts couldn't validate
4. **CI/CD Ready**: Easy integration into automated pipelines
5. **Regression Prevention**: Catches issues automatically
6. **Better Debugging**: Clear assertions and failure messages

### Deprecated Scripts
The following manual scripts have been replaced:
- `test_endpoints.py` → Automated test suite
- `scripts/test_api.py` → `test_api_endpoints_comprehensive.py`
- Manual `test.sh` testing → `test-automated.py`

## Performance Expectations

### Test Execution Times
- **Health tests**: ~2-3 seconds
- **Chat basic tests**: ~5-10 seconds  
- **Comprehensive suite**: ~2-3 minutes
- **Full test suite**: ~5-10 minutes

### Success Criteria
- **Health tests**: 100% pass rate expected
- **Core functionality**: >95% pass rate expected
- **Optional features**: Failures acceptable if documented
- **Performance tests**: Response times within expected bounds

## Best Practices

1. **Run Tests Frequently**: Don't wait until deployment
2. **Fix Failures Immediately**: Don't let broken tests accumulate
3. **Update Tests with Features**: New functionality needs new tests
4. **Document Expected Failures**: Known limitations should be documented
5. **Monitor Test Performance**: Watch for degrading response times
6. **Use Appropriate Test Types**: Unit, integration, and E2E tests each serve different purposes

This automated testing approach ensures reliable, maintainable validation of all Gaia Platform functionality while supporting rapid development and deployment cycles.