Run comprehensive test suite for GAIA platform:

1. **Unit Tests**
   ```bash
   ./scripts/pytest-for-claude.sh tests/unit -v
   ```

2. **Integration Tests**
   ```bash
   ./scripts/pytest-for-claude.sh tests/integration -v
   ```

3. **E2E Tests** (requires SUPABASE_SERVICE_KEY)
   ```bash
   ./scripts/pytest-for-claude.sh tests/e2e -v
   ```

4. **Code Quality**
   ```bash
   ruff check app/
   ```

5. **Test Coverage**
   Generate coverage report from test results

**Summary Format:**
- Total tests run
- Passed/Failed/Skipped breakdown
- Any failing test details
- Code quality issues
- Coverage percentage
- Recommendations for fixes