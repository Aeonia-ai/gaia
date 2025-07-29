# Testing and Quality Assurance Guide

This guide ensures we maintain high code quality and prevent breaking changes, especially for critical authentication flows.

## 🚀 **NEW: Automated Testing Suite**

**🔥 PRIORITY**: We now have a complete automated testing implementation:

- **[Automated Testing Guide](automated-testing-guide.md)** - **IMPLEMENTED** - Complete pytest-based test suite with 50+ tests
- **[Testing Philosophy](testing-philosophy.md)** - **UPDATED** - Automated tests over manual scripts
- **[Testing Improvement Plan](automated-testing-improvement-plan.md)** - 3-phase comprehensive testing strategy  
- **[Security Testing Strategy](security-testing-strategy.md)** - OWASP Top 10 compliance, SQL injection prevention
- **[Service Testing Strategy](comprehensive-service-testing-strategy.md)** - 100% service functionality coverage

**Quick Start**: `./scripts/test-automated.py all` - Runs complete automated test suite

## 🚀 Quick Start

```bash
# Set up development environment with all quality checks
./scripts/setup-dev-environment.sh

# Run automated tests before committing changes
./scripts/test-automated.py health      # Quick system health check
./scripts/test-automated.py auth        # Authentication contract tests
./scripts/test-automated.py all         # Complete test suite

# Quality checks
pre-commit run --all-files              # Code formatting and linting
```

## 🛡️ Preventing Breakages

### 1. Pre-commit Hooks

Pre-commit hooks run automatically on `git commit` to catch issues early:

```yaml
# .pre-commit-config.yaml includes:
- Code formatting (black, isort)
- Linting (ruff)
- Auth endpoint modification checks
- Contract tests for auth changes
```

To install:
```bash
pre-commit install
```

To run manually:
```bash
pre-commit run --all-files
```

### 2. Authentication Contract Tests

Critical tests that ensure public endpoints remain public:

```bash
# Run auth contract tests
pytest tests/web/test_auth_flow.py -v

# Specific contract tests
pytest tests/web/test_auth_flow.py::TestAuthenticationFlow::test_login_endpoint_is_public
pytest tests/web/test_auth_flow.py::TestAuthenticationFlow::test_register_endpoint_is_public
```

Key test scenarios:
- ✅ Public endpoints work without auth headers
- ✅ Login/register don't require API keys
- ✅ Email verification flows work correctly
- ✅ Error messages are user-friendly
- ✅ Gateway client doesn't add auth to public calls

### 3. CI/CD Pipeline

GitHub Actions runs on every push and PR:

```yaml
# .github/workflows/test.yml
- Unit tests with coverage
- Integration tests
- Linting and formatting checks
- Docker build verification
- Public endpoint accessibility tests
```

View test results: Actions tab in GitHub

### 4. Common Mistakes to Avoid

#### ❌ DON'T: Add auth to public endpoints
```python
# WRONG - Login is a public endpoint
async def login(self, email, password):
    return await self.client.post(
        "/api/v1/auth/login",
        headers={"X-API-Key": self.api_key},  # NO!
        json={"email": email, "password": password}
    )
```

#### ✅ DO: Keep public endpoints public
```python
# CORRECT - No auth headers for public endpoints
async def login(self, email, password):
    return await self.client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
```

## 🧪 Testing Strategy

### Unit Tests
Test individual components in isolation:
```bash
pytest tests/ -v -m unit
```

### Integration Tests
Test service interactions:
```bash
pytest tests/ -v -m integration
```

### UI Layout Tests
Prevent visual regression and layout breakages:
```bash
# Run UI layout tests
pytest tests/web/test_ui_layout.py -v

# Capture UI snapshots before changes
python scripts/capture-ui-snapshots.py

# Compare snapshots after changes
python scripts/compare-ui-snapshots.py
```

Key UI tests:
- ✅ No `flex-col md:flex-row` patterns (breaks layout)
- ✅ Loading indicators outside swap targets
- ✅ Consistent color palette usage
- ✅ Standard spacing scale
- ✅ Mobile-first responsive design

### End-to-End Tests
Test complete user workflows:
```bash
# Local Docker environment
docker compose up -d
./scripts/test.sh --local all

# Staging environment
./scripts/test.sh --staging all
```

### Performance Tests
Monitor response times and throughput:
```bash
# Load test with locust
locust -f tests/load/locustfile.py
```

## 📋 Testing Checklist

Before deploying any changes:

- [ ] Run auth contract tests: `pytest tests/web/test_auth_flow.py`
- [ ] Run UI layout tests: `pytest tests/web/test_ui_layout.py`
- [ ] Check UI snapshots: `python scripts/compare-ui-snapshots.py`
- [ ] Run full test suite: `pytest tests/`
- [ ] Check pre-commit hooks: `pre-commit run --all-files`
- [ ] Test locally with Docker: `docker compose up`
- [ ] Verify public endpoints: `./scripts/test.sh --local health`
- [ ] Test on staging: `./scripts/test.sh --staging all`
- [ ] Check logs for errors: `fly logs -a gaia-gateway-dev`
- [ ] Test on mobile, tablet, and desktop viewports

## 🔍 Debugging Failed Tests

### Auth Test Failures
```bash
# Check if services are running
docker compose ps

# View service logs
docker compose logs -f gateway auth-service

# Test endpoints manually
curl -X POST http://localhost:8666/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'
```

### HTMX/UI Test Failures
```bash
# Run web service tests
docker compose exec web-service pytest /app/tests/web/ -v

# Check browser console for errors
# Enable HTMX debug logging in browser
```

## 📊 Test Coverage

Maintain minimum coverage requirements:
- Overall: 80%
- Critical paths (auth, payments): 95%
- New code: 90%

Check coverage:
```bash
pytest --cov=app --cov-report=html tests/
open htmlcov/index.html
```

## 🚨 When Tests Fail in CI

1. **Check the GitHub Actions log** for specific error
2. **Reproduce locally**:
   ```bash
   # Same environment as CI
   docker compose build --no-cache
   docker compose up -d
   pytest tests/
   ```
3. **Fix the issue** (not the test!)
4. **Add regression test** if it's a new edge case
5. **Update documentation** if behavior changed

## 📝 Writing New Tests

### Test Structure
```python
async def test_public_endpoint_requires_no_auth(client):
    """Ensure endpoint works without authentication"""
    response = await client.post("/api/v1/auth/register", 
        json={"email": "test@example.com", "password": "pass123"}
    )
    
    # Should not require auth
    assert response.status_code != 401
    assert response.status_code != 403
```

### Mock External Services
```python
@pytest.fixture
def mock_gateway_client():
    with patch('app.services.web.routes.auth.GaiaAPIClient') as mock:
        client = AsyncMock()
        mock.return_value.__aenter__.return_value = client
        yield client
```

## 🔄 Continuous Improvement

1. **Monitor Production Errors**
   - Set up error tracking (Sentry)
   - Alert on auth failures > 1%
   - Track registration success rate

2. **Regular Security Audits**
   - Review auth flows quarterly
   - Update dependencies monthly
   - Penetration testing annually

3. **Performance Benchmarks**
   - Response time < 200ms (p95)
   - Login success rate > 99%
   - Zero downtime deployments

## 📚 Related Documentation

- [API Contracts](api-contracts.md) - Public vs protected endpoints
- [CSS Style Guide](css-style-guide.md) - UI layout patterns and rules
- [HTMX Debugging Guide](htmx-fasthtml-debugging-guide.md) - UI testing tips
- [Troubleshooting Guide](troubleshooting-flyio-dns.md) - Common issues
- [Web UI Development Status](web-ui-development-status.md) - Current state

## 🎯 Key Takeaways

1. **Test early, test often** - Pre-commit hooks catch issues before they're committed
2. **Contract tests are critical** - Public endpoints must stay public
3. **Don't fix tests, fix code** - Tests document expected behavior
4. **Monitor production** - Set up alerts for auth failures
5. **Document everything** - Future you will thank present you