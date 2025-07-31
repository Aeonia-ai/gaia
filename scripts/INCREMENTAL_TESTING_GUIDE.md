# 🔄 Incremental Testing Guide

## Quick Reference for pytest-for-claude.sh

### Basic Usage:
```bash
# All tests
./scripts/pytest-for-claude.sh

# Specific directory
./scripts/pytest-for-claude.sh tests/integration

# Single test file
./scripts/pytest-for-claude.sh tests/integration/test_v03_api.py

# Single test class
./scripts/pytest-for-claude.sh tests/integration/test_v03_api.py::TestV03ChatAPI

# Single test method
./scripts/pytest-for-claude.sh tests/integration/test_v03_api.py::TestV03ChatAPI::test_simple_chat_message
```

### Pattern Matching (-k):
```bash
# All health tests
./scripts/pytest-for-claude.sh "tests/ -k health"

# All auth tests
./scripts/pytest-for-claude.sh "tests/ -k auth"

# Tests containing "chat" but not "stream"
./scripts/pytest-for-claude.sh "tests/ -k 'chat and not stream'"
```

### Failed Test Handling:
```bash
# Run only last failed tests
./scripts/pytest-for-claude.sh --lf

# Run failed tests first, then others
./scripts/pytest-for-claude.sh --ff

# Run tests that failed in specific file
./scripts/pytest-for-claude.sh --lf tests/integration/test_v03_api.py
```

### Marker-Based Testing:
```bash
# Only integration tests
./scripts/pytest-for-claude.sh "tests/ -m integration"

# Only unit tests
./scripts/pytest-for-claude.sh "tests/ -m unit"

# Integration but not slow
./scripts/pytest-for-claude.sh "tests/ -m 'integration and not slow'"
```

### Debugging Options:
```bash
# Stop on first failure
./scripts/pytest-for-claude.sh -x

# Show local variables on failure
./scripts/pytest-for-claude.sh -l

# Verbose output with full diffs
./scripts/pytest-for-claude.sh -vv

# No parallel execution (easier debugging)
./scripts/pytest-for-claude.sh "-n 0"
```

### Performance Testing:
```bash
# Show slowest 10 tests
./scripts/pytest-for-claude.sh --durations=10

# Profile test execution
./scripts/pytest-for-claude.sh --profile
```

### Combining Options:
```bash
# Failed integration tests only, stop on first failure
./scripts/pytest-for-claude.sh "--lf -x -m integration"

# Health tests in verbose mode without parallel
./scripts/pytest-for-claude.sh "tests/ -k health -vv -n 0"

# Debug a specific failing test
./scripts/pytest-for-claude.sh "tests/integration/test_v03_api.py::TestV03ChatAPI::test_conversation_context -vv -l -n 0"
```

## 💡 Pro Tips:

1. **Start broad, then narrow**:
   ```bash
   ./scripts/pytest-for-claude.sh tests/integration  # See what fails
   ./scripts/pytest-for-claude.sh --lf              # Run only failures
   ```

2. **Use markers for categories**:
   ```bash
   ./scripts/pytest-for-claude.sh "-m 'not slow'"   # Skip slow tests
   ```

3. **Debug effectively**:
   ```bash
   # Turn off parallel execution for clearer output
   ./scripts/pytest-for-claude.sh "failing_test.py -n 0 -vv"
   ```

4. **Check test output**:
   ```bash
   tail -f test-run-*.log  # Watch progress
   ```

Remember: All these commands run in Docker asynchronously to avoid timeouts!