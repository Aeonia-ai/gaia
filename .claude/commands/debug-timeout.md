Debug test timeout issues:

$ARGUMENTS

1. **Check if using async runner**
   - ❌ WRONG: `pytest tests/`
   - ✅ RIGHT: `./scripts/pytest-for-claude.sh tests/`

2. **Verify test execution**
   ```bash
   ./scripts/check-test-progress.sh
   ```

3. **Check recent test logs**
   ```bash
   ls -la logs/tests/pytest/test-run-*.log | tail -3
   tail -50 logs/tests/pytest/test-run-*.log | grep -E "(TIMEOUT|ERROR|FAILED)"
   ```

4. **Common timeout causes:**
   - Direct pytest execution (2-minute Claude limit)
   - Docker not running
   - Infinite loops in tests
   - Missing async/await
   - External API calls without timeout

5. **Solution steps:**
   - Always use `./scripts/pytest-for-claude.sh`
   - Add explicit timeouts to external calls
   - Check for blocking operations
   - Verify Docker services are healthy

Provide specific recommendations based on the error.