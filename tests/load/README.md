# Load Tests

This directory contains load and performance tests that are separated from regular integration tests.

## Why Separate Load Tests?

1. **Different execution requirements** - Load tests need controlled environments
2. **Different success criteria** - Performance metrics vs functional correctness
3. **Different resource usage** - May hit rate limits or consume API quotas
4. **Different frequency** - Run before releases, not on every commit

## Running Load Tests

```bash
# Run load tests explicitly (not part of regular test suite)
pytest tests/load/ -v -m load

# Run with specific rate limits
LOAD_TEST_MAX_RPS=10 pytest tests/load/ -v
```

## Test Categories

- `test_concurrent_*.py` - Tests for concurrent request handling
- `test_burst_*.py` - Tests for burst traffic patterns
- `test_sustained_*.py` - Tests for sustained load over time

## Important Notes

- These tests may consume API quotas - run sparingly
- Consider using mock providers for cost-effective testing
- Always run in isolated environments
- Monitor rate limits and costs