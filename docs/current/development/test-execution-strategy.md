# Test Execution Strategy

## Overview

This document outlines the optimal test execution strategy for the GAIA platform based on empirical findings from resource exhaustion analysis and test infrastructure improvements.

## Key Findings

### Resource Exhaustion Issues

**Problem**: Parallel browser test execution causes significant resource exhaustion, leading to timeouts and unreliable results.

**Evidence**: 
- Parallel browser tests: 18% pass rate (11/60 passed)  
- Sequential browser tests: 52% pass rate (31/60 passed)
- **3x improvement** when running browser tests sequentially

**Root Cause**: Browser tests consume significant memory, CPU, and file handles. Docker containers running multiple browser instances simultaneously exhaust available resources.

## Test Execution Recommendations

### 1. Unit Tests
- **Execution**: Parallel (`pytest -n auto`)
- **Rationale**: Unit tests are lightweight and benefit from parallel execution
- **Current Status**: 124 passed, 2 expected failures (PersonaService not built)
- **Performance**: ~20 seconds with parallel execution

### 2. Integration Tests  
- **Execution**: Parallel (`pytest -n auto`)
- **Rationale**: API integration tests are I/O bound and parallelize well
- **Current Status**: 233 passed, 61 failed (mostly browser-related timeouts)
- **Performance**: ~5-6 minutes with parallel execution

### 3. Browser Tests (E2E)
- **Execution**: Sequential (`pytest -n 1`) ⚠️ **CRITICAL**
- **Rationale**: Browser tests cause resource exhaustion when run in parallel
- **Evidence**: 3x improvement in pass rates with sequential execution
- **Performance**: Slower but significantly more reliable

### 4. Mixed Test Suites
- **Strategy**: Run browser tests separately from other tests
- **Example**:
  ```bash
  # Run unit + integration (parallel)
  pytest tests/unit/ tests/integration/api/ -n auto
  
  # Run browser tests (sequential) 
  pytest tests/integration/web/ tests/e2e/ -n 1
  ```

## Current Test Infrastructure Status

### ✅ Working Well
- **Unit tests**: 99% pass rate (124/126)
- **API integration tests**: 79% pass rate (172/233 passed)
- **StreamingFormatter**: Fixed empty content handling
- **Async test runner**: Prevents Claude Code timeouts with `./scripts/pytest-for-claude.sh`

### ⚠️ Known Issues  
- **Browser tests**: Resource exhaustion when run in parallel
- **PersonaService**: 2 unit tests failing (service not implemented yet)
- **Tech debt**: Multiple unused chat implementations marked for removal
- **E2E tests**: May hang or timeout (need sequential execution)

## Implementation Commands

### For Development (Fast Feedback)
```bash
# Quick unit tests
./scripts/pytest-for-claude.sh tests/unit/ -v

# Quick API integration tests  
./scripts/pytest-for-claude.sh tests/integration/test_*api*.py -v
```

### For CI/CD (Complete Coverage)
```bash
# Stage 1: Fast parallel tests
./scripts/pytest-for-claude.sh tests/unit/ tests/integration/test_*api*.py -n auto

# Stage 2: Sequential browser tests
./scripts/pytest-for-claude.sh tests/integration/web/ tests/e2e/ -n 1  

# Stage 3: Report combined results
```

### For Claude Code (Timeout Prevention)
```bash
# ALWAYS use the async wrapper to prevent 2-minute timeouts
./scripts/pytest-for-claude.sh [test-args]

# NEVER use direct pytest 
pytest [test-args]  # ❌ Will timeout in Claude Code
```

## Resource Requirements

### Sequential Browser Tests
- **Memory**: ~2-4GB per browser instance
- **CPU**: 2-4 cores recommended
- **Time**: ~15-30 minutes for full E2E suite
- **Docker**: Increase container memory limits if needed

### Parallel Unit/Integration Tests
- **Memory**: ~1-2GB total
- **CPU**: Uses all available cores efficiently
- **Time**: ~5-10 minutes for full suite
- **Concurrency**: Automatically detected (`-n auto`)

## Monitoring and Debugging

### Test Progress Monitoring
```bash
# Check if tests are running
./scripts/check-test-progress.sh

# Monitor test logs in real-time
tail -f logs/tests/pytest/test-run-*.log
```

### Resource Monitoring
```bash
# Check Docker resource usage
docker stats

# Check system resources
htop
free -h
```

### Common Issues

1. **Tests hanging at X% complete**
   - Usually browser resource exhaustion
   - Solution: Kill and restart with `-n 1`

2. **Timeout after 2 minutes in Claude Code**  
   - Using direct `pytest` instead of wrapper
   - Solution: Use `./scripts/pytest-for-claude.sh`

3. **Inconsistent browser test results**
   - Running browser tests in parallel
   - Solution: Sequential execution with `-n 1`

## Future Improvements

### Short Term
1. **Implement PersonaService** to fix remaining unit test failures
2. **Remove tech debt** chat services and their tests
3. **Optimize browser test timeouts** for faster sequential execution

### Medium Term  
1. **Test sharding**: Split browser tests across multiple sequential runs
2. **Resource limits**: Configure Docker containers with appropriate limits
3. **Test categorization**: Better separation of test types in CI/CD

### Long Term
1. **Headless optimization**: Optimize browser tests for headless mode
2. **Test parallelization**: Research safe browser test parallelization techniques
3. **Container orchestration**: Use multiple containers for different test types

## Summary

The key insight is that **browser tests must run sequentially** to avoid resource exhaustion, while unit and API integration tests benefit from parallel execution. This hybrid approach maximizes both speed and reliability.

**Golden Rule**: When in doubt, run browser tests with `-n 1`.