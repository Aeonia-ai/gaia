# Test Execution Quick Reference Guide

## Running Tests

### By Test Type

```bash
# Unit tests only (fast, ~2 seconds)
./scripts/pytest-for-claude.sh tests/unit -v

# Integration tests only (~30 seconds)
./scripts/pytest-for-claude.sh tests/integration -v

# E2E tests only (2-5 minutes, requires SUPABASE_SERVICE_KEY)
./scripts/pytest-for-claude.sh tests/e2e -v

# All tests (~5-10 minutes)
./scripts/pytest-for-claude.sh
```

### Specific Test Files

```bash
# Run a specific test file
./scripts/pytest-for-claude.sh tests/integration/test_working_endpoints.py -v

# Run a specific test
./scripts/pytest-for-claude.sh tests/integration/test_working_endpoints.py::TestWorkingEndpoints::test_health_check -v

# Run tests matching a pattern
./scripts/pytest-for-claude.sh -k "chat" -v
```

### With Test Markers

```bash
# Only container-safe tests
./scripts/pytest-for-claude.sh -m container_safe

# Skip slow tests
./scripts/pytest-for-claude.sh -m "not slow"

# Only integration tests
./scripts/pytest-for-claude.sh -m integration
```

### Monitoring Test Progress

```bash
# Start tests
./scripts/pytest-for-claude.sh

# Check if still running
./scripts/check-test-progress.sh

# Watch live output
tail -f pytest-*.log

# Find failures quickly
grep -E "FAILED|ERROR" pytest-*.log
```

## Environment Setup

### Required Environment Variables

```bash
# For integration tests
export API_KEY="your-test-api-key"

# For E2E tests (REQUIRED)
export SUPABASE_SERVICE_KEY="your-service-key"
export SUPABASE_ANON_KEY="your-anon-key"
export SUPABASE_URL="https://your-project.supabase.co"

# Optional for debugging
export PYTEST_VERBOSE="-vv"
export PYTEST_CAPTURE="no"  # See print statements
```

### Docker Services Required

```bash
# Ensure all services are running
docker compose up -d

# Check service health
docker compose ps

# View logs if tests fail
docker compose logs gateway auth-service chat-service
```

## Common Test Scenarios

### After Code Changes

```bash
# Quick validation
./scripts/pytest-for-claude.sh tests/unit -v
./scripts/pytest-for-claude.sh tests/integration/test_working_endpoints.py -v

# If changing auth
./scripts/pytest-for-claude.sh tests/unit/test_auth_flow.py -v
./scripts/pytest-for-claude.sh tests/e2e/test_real_auth_e2e.py -v
```

### Before Committing

```bash
# Run core tests
./scripts/pytest-for-claude.sh tests/unit tests/integration -v

# Or full suite if time permits
./scripts/pytest-for-claude.sh
```

### Debugging Failures

```bash
# Run with debugging output
./scripts/pytest-for-claude.sh tests/failing_test.py -vvs

# Run with pdb on failure
./scripts/pytest-for-claude.sh tests/failing_test.py --pdb

# Generate detailed HTML report
./scripts/pytest-for-claude.sh --html=test-report.html --self-contained-html
```

## Test Categories Summary

### Unit Tests (15 tests)
- **Speed**: <100ms per test
- **Dependencies**: None
- **Mocking**: Heavy
- **Use for**: Logic validation, error handling

### Integration Tests (65 tests)
- **Speed**: ~500ms per test  
- **Dependencies**: Docker services
- **Mocking**: None
- **Use for**: API contracts, service integration

### E2E Tests (50+ tests)
- **Speed**: 2-5s per test
- **Dependencies**: Supabase, Docker services
- **Mocking**: NONE (real auth only)
- **Use for**: User journeys, UI validation

## Troubleshooting

### "No API key available"
```bash
# Set API key for tests
export API_KEY="test-key-from-env-file"
```

### "Invalid API key" in E2E tests
```bash
# Ensure valid Supabase service key
export SUPABASE_SERVICE_KEY="correct-key-from-dashboard"

# Test the key
python test_supabase_keys.py
```

### Tests timing out
```bash
# Always use async runner
./scripts/pytest-for-claude.sh  # NOT direct pytest
```

### Docker connection errors
```bash
# Ensure services are up
docker compose up -d

# Wait for health checks
sleep 10

# Retry tests
./scripts/pytest-for-claude.sh
```

### Can't see test output
```bash
# Check latest log file
ls -lt pytest-*.log | head -1

# View full output
cat pytest-*.log | less
```

## Performance Tips

1. **Run in parallel**: Tests use pytest-xdist for parallel execution
2. **Skip slow tests during development**: `-m "not slow"`
3. **Run unit tests first**: Fast feedback loop
4. **Use specific test selection**: Don't run all tests every time
5. **Keep E2E tests focused**: Each test should have one clear purpose

## CI/CD Integration

```yaml
# GitHub Actions example
- name: Run Tests
  run: |
    # Start services
    docker compose up -d
    
    # Wait for services
    sleep 10
    
    # Run tests
    ./scripts/pytest-for-claude.sh
    
    # Check results
    if [ -f .pytest.pid ]; then
      # Wait for completion
      while ps -p $(cat .pytest.pid) > /dev/null; do
        sleep 5
      done
    fi
    
    # Show summary
    tail -50 pytest-*.log | grep -E "(passed|failed|error)"
```

Remember: The async test runner (`pytest-for-claude.sh`) is REQUIRED to avoid Claude Code's 2-minute timeout!