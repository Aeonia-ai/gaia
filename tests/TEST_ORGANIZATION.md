# Test Organization Guide

## Overview

Tests are organized by execution context to avoid issues with Docker access and dependencies.

## Test Categories

### 1. Container-Safe Tests (Default)
- **Location**: Most tests in `/tests/`
- **Execution**: Run inside Docker containers via `test-automated.py`
- **Characteristics**: 
  - Have all dependencies available
  - Can access services via Docker networking (http://service-name:port)
  - Cannot run Docker commands
- **Markers**: Default (no marker needed) or `@pytest.mark.container_safe`

### 2. Host-Only Tests
- **Location**: Any test marked with `@pytest.mark.host_only`
- **Execution**: Must run from host machine
- **Characteristics**:
  - Can run Docker commands (`docker exec`, etc.)
  - Need pytest installed on host
  - Used for testing container structure, logs, etc.
- **Example**: `test_kb_service.py::test_multiuser_kb_structure`

### 3. Web UI Tests
- **Location**: `/tests/web/`
- **Execution**: Run inside web-service container
- **Characteristics**:
  - Test FastHTML routes and components
  - Have access to web service dependencies
- **Script**: `./scripts/test-web.sh`

### 4. Browser Tests
- **Location**: Tests using Playwright (various files)
- **Execution**: Special setup with headless browsers
- **Markers**: `@pytest.mark.browser`

## Running Tests

### Quick Commands

```bash
# Run all container-safe tests (parallel)
./scripts/test-automated.py all

# Run specific test categories
./scripts/test-automated.py core      # Core functionality
./scripts/test-automated.py v03       # v0.3 API tests
./scripts/test-automated.py kb        # Knowledge Base tests

# Run web UI tests
./scripts/test-web.sh

# Run host-only tests (from host machine)
./scripts/test-host-only.sh

# Run everything organized
./scripts/test-all-organized.sh
```

### Parallel Execution

Tests now run in parallel using pytest-xdist:
- Automatically uses all CPU cores
- Significantly faster execution (40s vs 2+ minutes)
- May expose race conditions or shared state issues

## Test Markers

Defined in `pytest.ini`:

- `host_only`: Tests requiring Docker access from host
- `container_safe`: Tests that run inside containers
- `browser`: Playwright browser tests
- `integration`: Integration tests
- `unit`: Unit tests
- `requires_redis`: Tests needing Redis
- `requires_db`: Tests needing database

## Adding New Tests

1. **Decide execution context**:
   - Need Docker commands? → Mark with `@pytest.mark.host_only`
   - Web UI testing? → Put in `/tests/web/`
   - Everything else → Regular test (runs in container)

2. **Add appropriate markers**:
   ```python
   @pytest.mark.host_only
   def test_container_structure():
       subprocess.run(["docker", "exec", ...])
   ```

3. **Consider parallel execution**:
   - Ensure tests are isolated
   - Don't rely on shared state
   - Clean up after test completion

## Troubleshooting

### Test fails in parallel but passes alone?
- Check for shared state (database, files)
- Add proper test isolation/cleanup
- Consider using fixtures for setup/teardown

### "Docker not found" error?
- Test is marked `host_only` but running in container
- Either remove Docker usage or ensure test runs on host

### Import errors?
- Check if test is running in correct container
- Web tests need web-service container
- API tests need test container