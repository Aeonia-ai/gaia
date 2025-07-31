# Testing Guide

## ⚠️ IMPORTANT: Avoiding Claude Code Timeouts

**Claude Code has a 2-minute timeout for all commands.** Running the full test suite directly will timeout and fail.

### ✅ Correct Way to Run Tests

Always use the async test runner:

```bash
# Start tests in background (returns immediately)
./scripts/run-all-tests.sh

# Check test progress
./scripts/check-test-progress.sh

# Watch live output
tail -f test-run-*.log
```

### ❌ DO NOT Run Tests These Ways

These will timeout in Claude Code:
```bash
# DON'T DO THIS - will timeout!
pytest
docker compose run test
docker compose run test pytest
python -m pytest
```

## Test Execution Details

### Parallel Execution
Tests run with `pytest-xdist` using all available CPU cores:
- Automatically detects CPU count with `-n auto`
- Typically 3-4x faster than sequential execution
- Essential for running 400+ tests within reasonable time

### Test Categories
- **Unit tests**: Fast, isolated component tests
- **Integration tests**: Service interaction tests
- **Web tests**: FastHTML UI tests with Playwright
- **Compatibility tests**: LLM Platform compatibility

### Quick Test Commands

For specific test files (safe to run directly):
```bash
# Single file - usually fast enough
pytest tests/test_auth.py -v

# Specific test
pytest tests/test_auth.py::test_api_key_validation -v
```

### Test Configuration

**pytest.ini** settings:
- `-n auto`: Parallel execution on all cores
- `-v`: Verbose output
- `--tb=short`: Concise traceback
- `--disable-warnings`: Cleaner output

**Requirements**:
- pytest>=7.4.3
- pytest-asyncio>=0.23.0
- pytest-cov>=6.0.0
- pytest-xdist>=3.5.0 (parallel execution)

## CI/CD Considerations

For GitHub Actions or other CI:
```yaml
- name: Run Tests
  run: |
    # CI can run pytest directly (no 2-minute timeout)
    pytest -n auto --cov=app --cov-report=xml
```

## Monitoring Test Health

After running tests:
```bash
# Check last run results
./scripts/check-test-progress.sh

# Find test logs
ls -la test-run-*.log

# Check for flaky tests
grep -E "FAILED|ERROR" test-run-*.log
```

## Performance Tips

1. **Use parallel execution**: Always included with `-n auto`
2. **Run specific tests during development**: Target what you're working on
3. **Full suite before commits**: Use async runner for complete validation
4. **Resource limits**: Docker containers limited to prevent system overload

## Troubleshooting

### Tests timing out?
- Always use `./scripts/run-all-tests.sh`
- Check Docker resource limits aren't too restrictive
- Ensure pytest-xdist is installed

### Tests failing randomly?
- Could be parallel execution issues
- Try with `-n 1` to run sequentially
- Check for shared state between tests

### Can't find test results?
- Check `test-run-*.log` files
- Use `./scripts/check-test-progress.sh` for summary
- Logs are timestamped for easy identification