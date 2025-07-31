# Phase Transition Testing Checklist

## Why Test Between Phases?

Each phase builds on the previous one. A broken foundation means everything built on top will fail. Testing between phases ensures:
- ✅ Changes are working as expected
- ✅ No regressions introduced
- ✅ Safe to proceed to next phase
- ✅ Easy rollback if issues found

## Standard Phase Transition Tests

### 1. Quick Smoke Test (30 seconds)
```bash
# Verify services are healthy
docker compose ps

# Run a single critical test
docker compose run --rm test python -m pytest tests/integration/test_conversation_delete.py -v
```

### 2. Marker-Based Tests (2-3 minutes)
```bash
# Test each marker type still works
docker compose run --rm test python -m pytest -m unit --maxfail=3 -x
docker compose run --rm test python -m pytest -m integration --maxfail=3 -x
docker compose run --rm test python -m pytest -m e2e --maxfail=3 -x
```

### 3. Directory-Based Tests (if reorganized)
```bash
# Test new directory structure
docker compose run --rm test python -m pytest tests/unit --maxfail=3 -x
docker compose run --rm test python -m pytest tests/integration --maxfail=3 -x
```

### 4. Import Verification
```bash
# Verify key imports still work
docker compose run --rm test python -c "from tests.fixtures.test_auth import TestAuthManager; print('✅ Imports OK')"
```

### 5. Comprehensive Test (5 minutes)
```bash
# Run full verification script
python scripts/verify-tests-phase3.py
```

## Phase-Specific Validation

### After Phase 1 (Inventory)
- ✅ Verify TEST_INVENTORY.md is accurate
- ✅ Check FLAKY_TESTS.md identifies real issues
- ✅ No code changes, so no test runs needed

### After Phase 2 (Markers)
- ✅ Run marker verification script
- ✅ Ensure 100% marker coverage
- ✅ Test filtering by markers works
- ✅ No test failures from marker addition

### After Phase 3 (Reorganization)
- ✅ All files moved to correct directories
- ✅ No orphaned test files
- ✅ All imports updated
- ✅ Tests pass in new structure
- ✅ No missing fixtures

### After Phase 4 (Optimization)
- ✅ Flaky tests have retry logic
- ✅ Skipped tests removed
- ✅ Timeouts standardized
- ✅ Performance improved

### After Phase 5 (Documentation)
- ✅ TEST_GUIDE.md is comprehensive
- ✅ All patterns documented
- ✅ New developers can run tests

## Red Flags to Stop Progress

🚨 **STOP if you see:**
- Import errors after moving files
- Tests that passed now failing
- Fixture not found errors
- Module not found errors
- Significant increase in test time
- Docker connection errors

## Rollback Procedure

If tests fail after a phase:

1. **Don't panic** - We have git
2. **Identify the issue** - Check error messages
3. **Try quick fixes** - Often just import paths
4. **Run rollback if needed**:
   ```bash
   # For reorganization
   python scripts/reorganize-tests.py --rollback
   
   # For git changes
   git stash  # or git reset --hard HEAD~1
   ```

## Best Practices

1. **Always run tests in Docker** - Matches CI environment
2. **Start with fast tests** - Quick feedback loop
3. **Fix issues immediately** - Don't let them compound
4. **Document discoveries** - Update phase completion docs
5. **Commit after success** - Create restore points

## Example: What We Should Have Done

```bash
# After Phase 2 (markers)
python scripts/verify-tests-phase3.py
# ✅ All passing

# After Phase 3 (reorganization) 
python scripts/verify-tests-phase3.py
# ❌ Import errors found
# 🔧 Fixed with fix-test-imports.py
# ✅ Rerun verification - all passing
# 📝 Document in PHASE_3_REORGANIZATION_COMPLETE.md
# 💾 Commit changes
```

## Quick Test Command

For a fast "are we still good?" check:

```bash
docker compose run --rm test python -m pytest \
  tests/integration/test_conversation_delete.py \
  tests/integration/test_comprehensive_suite.py::TestComprehensiveSuite::test_core_system_health \
  -v
```

This runs in ~5 seconds and catches most critical issues.