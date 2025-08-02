# Async Test Execution Guide

## Why Async Test Execution?

Claude Code's Bash tool has a **2-minute timeout**. Our comprehensive test suite takes 5-15 minutes to run, which would cause timeouts. The async test execution pattern solves this problem.

## The Problem

```bash
# ❌ This will timeout in Claude Code after 2 minutes
pytest tests/ -v

# Even with specific tests, large suites timeout
pytest tests/integration -v  # Can take 3-5 minutes
```

## The Solution: pytest-for-claude.sh

### How It Works

1. **Background Execution**: Tests run in a detached process
2. **Log Capture**: Output saved to timestamped log files
3. **Progress Monitoring**: Check status without blocking
4. **Completion Detection**: Know when tests finish

### Basic Usage

```bash
# Start tests in background
./scripts/pytest-for-claude.sh

# Check progress
./scripts/check-test-progress.sh

# View live output
tail -f pytest-*.log
```

## Script Details

### pytest-for-claude.sh

```bash
#!/bin/bash
# Async pytest runner for Claude Code

# Generate unique log file
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="pytest-${TIMESTAMP}.log"

# Run pytest in background with all arguments passed through
echo "Starting pytest in background..."
echo "Log file: $LOG_FILE"
echo "Check progress with: ./scripts/check-test-progress.sh"

nohup pytest "$@" > "$LOG_FILE" 2>&1 &
echo $! > .pytest.pid

echo "Tests started! PID: $(cat .pytest.pid)"
```

### check-test-progress.sh

```bash
#!/bin/bash
# Check pytest progress

if [ ! -f .pytest.pid ]; then
    echo "No pytest process found"
    exit 1
fi

PID=$(cat .pytest.pid)
if ps -p $PID > /dev/null; then
    echo "Tests still running (PID: $PID)"
    # Show last 10 lines of most recent log
    LOG=$(ls -t pytest-*.log | head -1)
    echo "Recent output from $LOG:"
    tail -10 "$LOG"
else
    echo "Tests completed!"
    rm .pytest.pid
    # Show summary from log
    LOG=$(ls -t pytest-*.log | head -1)
    tail -20 "$LOG" | grep -E "(passed|failed|error|warnings)"
fi
```

## Usage Patterns

### Run All Tests
```bash
./scripts/pytest-for-claude.sh
```

### Run Specific Test File
```bash
./scripts/pytest-for-claude.sh tests/test_working_endpoints.py -v
```

### Run Test Category
```bash
./scripts/pytest-for-claude.sh tests/integration -v
./scripts/pytest-for-claude.sh tests/e2e -v
./scripts/pytest-for-claude.sh tests/unit -v
```

### Run Specific Test
```bash
./scripts/pytest-for-claude.sh tests/test_v02_chat_api.py::test_chat_completion -v
```

### With Markers
```bash
./scripts/pytest-for-claude.sh -m "not slow" -v
./scripts/pytest-for-claude.sh -m integration -v
```

## Monitoring Tests

### Check If Running
```bash
./scripts/check-test-progress.sh
```

### Watch Live Output
```bash
# Get latest log file
LOG=$(ls -t pytest-*.log | head -1)
tail -f "$LOG"
```

### See Full Results
```bash
# After completion
cat pytest-*.log | less
```

### Find Failures
```bash
# Quick failure summary
grep -E "FAILED|ERROR" pytest-*.log
```

## Best Practices

### 1. Always Use for Full Suites
```bash
# ❌ Don't use pytest directly for full suites
pytest tests/

# ✅ Use async runner
./scripts/pytest-for-claude.sh tests/
```

### 2. Direct pytest for Quick Tests
```bash
# ✅ OK for single, quick tests
pytest tests/test_working_endpoints.py::test_health -v
```

### 3. Clean Up Old Logs
```bash
# Remove logs older than 7 days
find . -name "pytest-*.log" -mtime +7 -delete
```

### 4. Check Before Starting New Run
```bash
# Avoid multiple concurrent runs
./scripts/check-test-progress.sh
```

## Handling Failures

### Test Suite Hangs
```bash
# Find and kill hung process
cat .pytest.pid
kill $(cat .pytest.pid)
rm .pytest.pid
```

### Can't Find Results
```bash
# List all test logs by date
ls -lt pytest-*.log
```

### Need Detailed Output
```bash
# Run with maximum verbosity
./scripts/pytest-for-claude.sh -vvv -s
```

## Integration with CI/CD

### GitHub Actions
```yaml
- name: Run Tests Async
  run: |
    ./scripts/pytest-for-claude.sh
    # Poll for completion
    while [ -f .pytest.pid ] && ps -p $(cat .pytest.pid) > /dev/null; do
      sleep 10
    done
    # Check results
    tail -50 pytest-*.log
```

### Local Development
```bash
# Pre-commit hook
./scripts/pytest-for-claude.sh tests/unit tests/integration
./scripts/check-test-progress.sh
```

## Common Issues

### "No pytest process found"
- Tests completed or never started
- Check for recent log files
- Ensure pytest is installed

### Tests Never Complete
- Check Docker services: `docker compose ps`
- Look for errors in log: `grep ERROR pytest-*.log`
- Some tests may have infinite loops

### Can't See Output
- Log file permissions issue
- Check current directory: `pwd`
- List log files: `ls -la pytest-*.log`

## Advanced Usage

### Custom Log Location
```bash
# Modify pytest-for-claude.sh
LOG_FILE="/tmp/pytest-${TIMESTAMP}.log"
```

### Email on Completion
```bash
# Add to check-test-progress.sh
if ! ps -p $PID > /dev/null; then
    mail -s "Tests Complete" user@example.com < "$LOG"
fi
```

### Parallel Test Runs
```bash
# Run different test categories in parallel
./scripts/pytest-for-claude.sh tests/unit &
./scripts/pytest-for-claude.sh tests/integration &
./scripts/pytest-for-claude.sh tests/e2e &
```

## Summary

The async test execution pattern enables:
- ✅ Full test suite execution without timeouts
- ✅ Background testing while you work
- ✅ Progress monitoring without blocking
- ✅ Complete test results capture
- ✅ Integration with Claude Code's constraints

Remember: **Always use `pytest-for-claude.sh` for test suites that might take over 2 minutes!**