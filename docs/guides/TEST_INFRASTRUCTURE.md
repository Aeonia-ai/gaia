# Test Infrastructure Technical Reference

> **This document provides technical details about the GAIA test infrastructure, including runners, tools, and optimization strategies.**

## Table of Contents
1. [Async Test Execution](#async-test-execution)
2. [Docker Test Environment](#docker-test-environment)
3. [Test Runners and Scripts](#test-runners-and-scripts)
4. [Resource Management](#resource-management)
5. [Log Management](#log-management)
6. [Performance Optimization](#performance-optimization)
7. [CI/CD Integration](#cicd-integration)
8. [Troubleshooting Infrastructure](#troubleshooting-infrastructure)

## Async Test Execution

### The Problem: Claude Code Timeout

Claude Code's Bash tool has a **2-minute timeout**, but our test suite can take 5-15 minutes to complete. Direct pytest execution will timeout:

```bash
# ❌ This will timeout after 2 minutes
pytest tests/ -v

# Even specific suites can timeout
pytest tests/integration -v  # Can take 3-5 minutes
```

### The Solution: Async Test Runner

The `pytest-for-claude.sh` script runs tests asynchronously in the background:

```bash
#!/bin/bash
# Simplified view of pytest-for-claude.sh

# Create log directory
LOG_DIR="logs/tests/pytest"
mkdir -p "$LOG_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/test-run-$TIMESTAMP.log"

# Run pytest in background
nohup docker compose run --rm test pytest "$@" > "$LOG_FILE" 2>&1 &
TEST_PID=$!

# Save PID for monitoring
echo $TEST_PID > "$LOG_DIR/.current_test.pid"

echo "Tests started in background (PID: $TEST_PID)"
echo "Log file: $LOG_FILE"
```

### How It Works

1. **Background Execution**: Tests run in a detached process using `nohup`
2. **Log Capture**: All output saved to timestamped log files
3. **PID Tracking**: Process ID saved for status checking
4. **Non-blocking**: Returns immediately to avoid timeout

### Monitoring Test Progress

```bash
# Check if tests are running
./scripts/check-test-progress.sh

# Output:
# 🚀 Test run in progress (PID: 12345)
# Running for: 2 minutes 15 seconds
# Last 10 lines:
# tests/integration/test_chat_api.py::test_send_message PASSED
# ...

# Watch logs in real-time
tail -f logs/tests/pytest/test-run-*.log

# Check specific test status
grep -E "(PASSED|FAILED|ERROR)" logs/tests/pytest/test-run-*.log | tail -20
```

## Docker Test Environment

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Host Machine                       │
├─────────────────────────────────────────────────────┤
│                 Docker Compose                       │
├─────────────┬──────────┬──────────┬────────────────┤
│    Test     │ Gateway  │  Chat    │   Database     │
│  Container  │ Service  │ Service  │   Service      │
│             │          │          │                │
│  pytest     │ :8000    │ :8000    │   :5432        │
│  playwright │          │          │                │
└─────────────┴──────────┴──────────┴────────────────┘
```

### Test Container Configuration

```yaml
# docker-compose.yml (test service)
test:
  build:
    context: .
    dockerfile: Dockerfile.test
  environment:
    - PYTHONPATH=/app
    - DATABASE_URL=postgresql://postgres:postgres@db:5432/gaia_test
    - REDIS_URL=redis://redis:6379/1
    - WEB_SERVICE_URL=http://web-service:8001
    - GATEWAY_URL=http://gateway:8000
  volumes:
    - ./tests:/app/tests
    - ./app:/app/app
    - ./logs:/app/logs
  depends_on:
    - db
    - redis
    - gateway
    - auth-service
    - chat-service
```

### Service URLs in Tests

```python
# Service URLs available in test environment
GATEWAY_URL = "http://gateway:8000"
AUTH_SERVICE_URL = "http://auth-service:8000"
CHAT_SERVICE_URL = "http://chat-service:8000"
WEB_SERVICE_URL = "http://web-service:8001"
KB_SERVICE_URL = "http://kb-service:8000"

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@db:5432/gaia_test"
REDIS_URL = "redis://redis:6379/1"
```

## Test Runners and Scripts

### Primary Test Runner: pytest-for-claude.sh

```bash
# Full async test suite
./scripts/pytest-for-claude.sh

# With options
./scripts/pytest-for-claude.sh -v -s --tb=short

# Specific tests
./scripts/pytest-for-claude.sh tests/unit -v

# With markers
./scripts/pytest-for-claude.sh -m "not slow" -v

# Parallel execution
./scripts/pytest-for-claude.sh -n auto
```

### Progress Checker: check-test-progress.sh

```bash
#!/bin/bash
# Checks test execution status

PID_FILE="logs/tests/pytest/.current_test.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "🚀 Test run in progress (PID: $PID)"
        # Show runtime and last logs
    else
        echo "✅ Test run completed"
        # Show summary
    fi
else
    echo "No test run in progress"
fi
```

### Legacy Test Scripts (Deprecated)

```bash
# Old scripts - DO NOT USE
./scripts/test.sh              # Replaced by pytest-for-claude.sh
./scripts/test-comprehensive.sh # Replaced by pytest-for-claude.sh
```

## Resource Management

### Database Management

```python
# Test database isolation
@pytest.fixture(scope="session")
def test_database():
    """Create isolated test database"""
    create_test_database()
    yield
    cleanup_test_database()

# Transaction rollback pattern
@pytest.fixture
async def db_session():
    """Provide transactional session"""
    async with database.transaction() as tx:
        yield tx
        await tx.rollback()  # Fast cleanup
```

### Memory Management

```python
# Cleanup large objects
@pytest.fixture
def large_dataset():
    data = load_large_dataset()
    yield data
    del data  # Explicit cleanup
    gc.collect()  # Force garbage collection

# Limit concurrent tests
# pytest.ini
[tool:pytest]
addopts = -n 4  # Max 4 parallel workers
```

### Docker Resource Limits

```yaml
# docker-compose.yml
services:
  test:
    mem_limit: 2g
    memswap_limit: 2g
    cpus: "2.0"
```

## Log Management

### Log Organization

```
logs/
└── tests/
    └── pytest/
        ├── test-run-20250807-143022.log  # Full test run
        ├── test-run-20250807-145512.log  # Another run
        └── .current_test.pid              # Current test PID
```

### Log Rotation

```bash
# Clean old logs (older than 7 days)
find logs/tests/pytest -name "*.log" -mtime +7 -delete

# Keep last N test runs
ls -t logs/tests/pytest/test-run-*.log | tail -n +11 | xargs rm -f
```

### Structured Logging

```python
# conftest.py
import logging
import pytest

@pytest.fixture(autouse=True)
def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler('logs/tests/test-debug.log'),
            logging.StreamHandler()
        ]
    )
```

## Performance Optimization

### Docker Build Optimization

```dockerfile
# Dockerfile.test
FROM python:3.11-slim

# Cache dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install test dependencies
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy code last (changes most frequently)
COPY . .
```

### Build Caching

```bash
# Build with cache
docker compose build test

# Force rebuild (when dependencies change)
docker compose build --no-cache test

# Use BuildKit for better caching
DOCKER_BUILDKIT=1 docker compose build test
```

### Test Execution Optimization

```python
# pytest.ini
[tool:pytest]
# Parallel execution
addopts = -n auto

# Reuse database between tests
--reuse-db

# Fail fast
--maxfail=3

# Show slowest tests
--durations=10
```

### ⚠️ Critical: Parallel Execution Issues

**Why pytest-for-claude.sh runs tests sequentially:**

The Docker pytest.ini contains `-n auto` which enables parallel test execution with pytest-xdist. While this speeds up test runs, it causes several problems:

1. **Resource Conflicts**:
   - Shared test user conflicts (e.g., `pytest@aeonia.ai` being created/deleted simultaneously)
   - Database connection pool exhaustion
   - Port binding conflicts for test servers
   - File system race conditions

2. **State Pollution**:
   - Tests modifying shared state (cookies, sessions, cache)
   - Browser tests navigating to different pages simultaneously
   - Mock configurations bleeding between tests

3. **Timing Issues**:
   - HTMX not fully loaded before test assertions
   - WebSocket connections not established
   - API calls completing out of order

4. **Debugging Difficulty**:
   - Non-deterministic failures
   - Different results on each run
   - Logs interleaved from multiple tests

**Solution**: The pytest-for-claude.sh script overrides pytest.ini to disable parallel execution:
```bash
# Override pytest.ini to remove -n auto
docker compose run --rm test bash -c "PYTHONPATH=/app pytest --override-ini='addopts=-v --tb=short --strict-markers --disable-warnings' $TEST_ARGS"
```

This ensures tests run one at a time, eliminating race conditions and resource conflicts at the cost of slower execution (but still within Claude's timeout limits).

### Selective Test Running

```bash
# Run only changed tests
pytest-testmon

# Run failed tests first
pytest --lf  # last failed
pytest --ff  # failed first

# Skip slow tests during development
pytest -m "not slow"
```

## CI/CD Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
        
      - name: Cache Docker layers
        uses: actions/cache@v3
        with:
          path: /tmp/.buildx-cache
          key: ${{ runner.os }}-buildx-${{ github.sha }}
          
      - name: Run tests
        run: |
          docker compose up -d
          ./scripts/pytest-for-claude.sh --ci-mode
          ./scripts/check-test-progress.sh --wait
```

### Environment Variables for CI

```bash
# CI-specific settings
export CI=true
export PYTEST_TIMEOUT=1800  # 30 minutes
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

## Troubleshooting Infrastructure

### Common Issues and Solutions

#### 1. Tests Timeout in Claude Code

```bash
# Problem
pytest tests/  # Times out after 2 minutes

# Solution
./scripts/pytest-for-claude.sh tests/  # Runs async
```

#### 2. Docker Build Hangs

```bash
# Problem: Build hangs on "Sending build context"
# Solution: Add .dockerignore
echo ".venv/" >> .dockerignore
echo "venv/" >> .dockerignore
echo "__pycache__/" >> .dockerignore
```

#### 3. Out of Memory Errors

```bash
# Check memory usage
docker stats

# Increase Docker memory limit
# Docker Desktop > Preferences > Resources > Memory: 8GB

# Limit test parallelism
./scripts/pytest-for-claude.sh -n 2  # Only 2 workers
```

#### 4. Port Conflicts

```bash
# Check ports in use
lsof -i :8000
lsof -i :5432

# Stop conflicting services
docker compose down
pkill -f "python.*8000"
```

### Debugging Infrastructure

```bash
# Check service health
docker compose ps
docker compose logs -f gateway

# Inspect test container
docker compose run --rm test bash
> pytest --version
> python -c "import app; print(app.__file__)"

# Network debugging
docker compose run --rm test ping gateway
docker compose run --rm test curl http://gateway:8000/health
```

### Performance Profiling

```bash
# Profile test execution
pytest --profile

# Generate coverage report
pytest --cov=app --cov-report=html

# Memory profiling
pytest --memprof
```

## Advanced Topics

### Custom Test Markers

```python
# pytest.ini
[tool:pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    security: marks security-related tests
```

### Fixture Factories

```python
# tests/fixtures/factories.py
@pytest.fixture
def make_user():
    """Factory for creating test users"""
    created_users = []
    
    def _make_user(**kwargs):
        user = User(**kwargs)
        created_users.append(user)
        return user
    
    yield _make_user
    
    # Cleanup
    for user in created_users:
        delete_user(user)
```

### Test Database Strategies

```python
# Strategy 1: Truncate tables
@pytest.fixture(scope="function")
def clean_db():
    yield
    truncate_all_tables()

# Strategy 2: Transaction rollback
@pytest.fixture(scope="function")
def transactional_db():
    with database.transaction() as tx:
        yield tx
        tx.rollback()

# Strategy 3: Separate test database
@pytest.fixture(scope="session")
def test_db():
    create_test_database()
    yield
    drop_test_database()
```

## Maintenance

### Regular Tasks

1. **Clean old logs**: Weekly
   ```bash
   find logs/tests -name "*.log" -mtime +7 -delete
   ```

2. **Update test dependencies**: Monthly
   ```bash
   pip-compile requirements-test.in
   ```

3. **Profile slow tests**: Before releases
   ```bash
   pytest --durations=50
   ```

4. **Check flaky tests**: Continuous
   ```bash
   pytest --flake-finder --flake-runs=10
   ```

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

The test infrastructure described in this document has been verified against the current codebase.

-   **✅ Async Test Execution:**
    *   **Claim:** The `pytest-for-claude.sh` script runs tests asynchronously in the background to avoid timeouts.
    *   **Code Reference:** `scripts/pytest-for-claude.sh`.
    *   **Verification:** This is **VERIFIED**. The script uses `nohup` and backgrounding (`&`) to run the tests in a detached process.

-   **✅ Docker Test Environment:**
    *   **Claim:** A `test` service is defined in `docker-compose.yml` with a specific Dockerfile, environment variables, and volumes.
    *   **Code Reference:** `docker-compose.yml`.
    *   **Verification:** This is **VERIFIED**. The `test` service is configured as described.

-   **✅ Test Runners and Scripts:**
    *   **Claim:** `pytest-for-claude.sh` is the primary test runner, and `check-test-progress.sh` is used for monitoring.
    *   **Code References:** `scripts/pytest-for-claude.sh`, `scripts/check-test-progress.sh`.
    *   **Verification:** This is **VERIFIED**. Both scripts exist and function as described.

-   **✅ Log Management:**
    *   **Claim:** Test logs are stored in `logs/tests/pytest/` with a timestamped filename.
    *   **Code Reference:** `scripts/pytest-for-claude.sh`.
    *   **Verification:** This is **VERIFIED**. The script creates and writes to log files in this directory.

-   **✅ Parallel Execution Override:**
    *   **Claim:** The `pytest-for-claude.sh` script overrides the `pytest.ini` setting to disable parallel execution.
    *   **Code Reference:** `scripts/pytest-for-claude.sh` (line 220).
    *   **Verification:** This is **VERIFIED**. The script explicitly calls `pytest` with an overridden `addopts` setting that does not include the `-n auto` flag.

**Overall Conclusion:** This document provides an accurate and up-to-date overview of the test infrastructure.

---

**Remember**: Good infrastructure enables good testing. Invest in making tests easy to run and debug!