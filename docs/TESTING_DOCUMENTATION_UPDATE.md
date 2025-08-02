# Testing Documentation Update Required

Based on our recent changes, the following documentation needs updating:

## 1. Key Changes Made

### Test Runner Update
- **OLD**: `./scripts/test-automated.py` (removed)
- **NEW**: `./scripts/pytest-for-claude.sh` - Async test runner to avoid timeouts
- **Check Progress**: `./scripts/check-test-progress.sh`

### E2E Authentication Approach
- **OLD**: Mock authentication allowed in E2E tests
- **NEW**: Real Supabase authentication ONLY - no mocks in E2E tests
- **Required**: Valid SUPABASE_SERVICE_KEY in .env

### API Authentication
- **OLD**: Hardcoded API keys as fallback
- **NEW**: JWT-only authentication, no API key fallbacks

## 2. Documentation Files to Update

### `/docs/current/development/testing-and-quality-assurance.md`
- Update Quick Start section to use `pytest-for-claude.sh`
- Remove references to `test-automated.py`
- Add E2E test section emphasizing real auth requirement

### `/docs/current/development/testing-philosophy.md`
- Update test runner examples to `pytest-for-claude.sh`
- Remove `test-automated.py` references
- Add section on "No Mocks in E2E Tests"
- Update migration guide

### `/docs/browser-testing-strategy.md`
- Remove mock authentication as recommended approach
- Update to show real auth using TestUserFactory
- Remove mock auth examples for E2E tests

### `/docs/current/development/automated-testing-guide.md`
- Update test execution commands
- Add section on E2E real authentication
- Document TestUserFactory usage

### `/docs/current/authentication/authentication-guide.md`
- Update to reflect JWT-only approach
- Remove API key fallback documentation
- Add E2E testing authentication section

## 3. New Documentation Needed

### `/docs/current/development/e2e-real-auth-testing.md`
Create comprehensive guide covering:
- TestUserFactory usage
- Real Supabase authentication in tests
- No mock policy for E2E tests
- Troubleshooting auth issues
- Service key configuration

### `/docs/current/development/async-test-execution.md`
Document the async test pattern:
- Why we use background execution
- How pytest-for-claude.sh works
- Monitoring test progress
- Avoiding Claude Code timeouts

## 4. Example Updates

### Old Testing Quick Start
```bash
# OLD - No longer works
./scripts/test-automated.py all
./scripts/test-automated.py health
```

### New Testing Quick Start
```bash
# NEW - Async execution
./scripts/pytest-for-claude.sh                    # All tests
./scripts/pytest-for-claude.sh tests/integration  # Integration only
./scripts/check-test-progress.sh                  # Check status
```

### Old E2E Test Pattern
```python
# OLD - Mock auth allowed
await page.route("**/auth/login", mock_response)
```

### New E2E Test Pattern
```python
# NEW - Real auth required
factory = TestUserFactory()
user = factory.create_verified_test_user()
# Perform real login
```

## 5. Priority Updates

1. **HIGH**: Update main testing guide to use correct test runner
2. **HIGH**: Document E2E real auth requirement
3. **MEDIUM**: Update authentication docs to remove API key fallback
4. **MEDIUM**: Create async test execution guide
5. **LOW**: Update all example code snippets

## 6. CLAUDE.md Updates Needed

The CLAUDE.md file should be updated to emphasize:
- Always use `pytest-for-claude.sh` not `pytest` directly
- E2E tests require real Supabase auth
- No mocks in E2E tests
- Valid SUPABASE_SERVICE_KEY required for testing

This ensures future Claudes understand the testing approach correctly.