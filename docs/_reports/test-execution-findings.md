# Test Execution Findings

## Summary

During test suite execution on the `feat/unified-chat-persistence` branch, we discovered that E2E browser tests were causing significant hanging issues.

## Key Findings

### 1. E2E Tests Hang with Async Wrapper
- `pytest-for-claude.sh` async wrapper causes E2E tests to hang indefinitely
- Tests stop at 18% completion (after `test_example_with_screenshot_cleanup.py`)
- Running tests directly with `docker compose run` works better

### 2. Specific Problem Tests
- `test_responsive_breakpoints` - Creates multiple browser contexts causing timeouts
- `test_layout_integrity.py` - Multiple tests timeout when navigating to pages
- `test_example_with_screenshot_cleanup.py` - Screenshot tests fail but don't hang

### 3. Working Test Patterns

**Direct pytest execution (recommended for E2E):**
```bash
# Single test file
docker compose run --rm test bash -c "PYTHONPATH=/app pytest tests/e2e/test_e2e_real_auth.py -v"

# With timeout to prevent hanging
docker compose run --rm test bash -c "PYTHONPATH=/app timeout 60 pytest tests/e2e/test_specific.py -v"

# Sequential execution for browser tests
docker compose run --rm test bash -c "PYTHONPATH=/app pytest tests/e2e -v -n 1"
```

**Async wrapper (works well for unit/integration):**
```bash
./scripts/pytest-for-claude.sh tests/unit -v
./scripts/pytest-for-claude.sh tests/integration --ignore=tests/integration/web/ -v
```

### 4. Test Results Summary

**Working Tests:**
- Unit tests: Pass (except expected PersonaService failures)
- Integration tests: Pass (except browser-based ones)
- E2E auth tests: Pass when run individually

**Problematic Tests:**
- `test_layout_integrity.py` - Page navigation timeouts
- `test_responsive_breakpoints` - Multiple browser context creation
- Screenshot tests - Failures but don't cause hanging

## Recommendations

1. **For E2E Tests**: Use direct pytest execution with timeouts
2. **For CI/CD**: Run E2E tests sequentially (-n 1) with strict timeouts
3. **Skip/Fix**: `test_responsive_breakpoints` needs refactoring
4. **Investigation Needed**: Why layout integrity tests timeout on page navigation

## Test Execution Commands

```bash
# Run specific E2E test file
docker compose run --rm test bash -c "PYTHONPATH=/app pytest tests/e2e/test_e2e_real_auth.py -v"

# Run all E2E tests with timeout (prevents hanging)
docker compose run --rm test bash -c "PYTHONPATH=/app timeout 300 pytest tests/e2e -v -n 1"

# Run non-browser tests with async wrapper
./scripts/pytest-for-claude.sh tests/unit tests/integration --ignore=tests/integration/web/ -v
```