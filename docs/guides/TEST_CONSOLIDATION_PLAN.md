# Test Consolidation Plan



## Overview

This document outlines the plan to consolidate all testing into the automated pytest suite, eliminating duplicate test scripts and creating a single source of truth for all testing.

## Current State Analysis

### Test Scripts to Deprecate (Duplicates)
1. **scripts/test-gateway-endpoints.sh**
   - Duplicates: `tests/integration/gateway/test_gateway_auth_endpoints.py`
   - Action: Add deprecation notice, point to pytest tests

2. **scripts/test_streaming_endpoint.py**
   - Duplicates: `tests/integration/chat/test_unified_streaming_format.py`
   - Action: Migrate TTFT metrics to pytest, deprecate script

### Test Scripts to Migrate (Unique)
1. **scripts/test-intelligent-routing.sh**
   - Target: `tests/integration/chat/test_intelligent_routing.py`
   - Tests: Routing logic, complexity detection, endpoint selection

2. **scripts/test-mcp-agent-hot-loading.sh**
   - Target: `tests/integration/chat/test_mcp_agent_hot_loading.py`
   - Tests: Hot loading performance, singleton behavior

3. **scripts/test-kb-storage-performance.py**
   - Target: `tests/performance/test_kb_storage_performance.py`
   - Tests: KB storage operations, performance benchmarks

4. **scripts/test_llm_platform_compatibility.sh**
   - Target: `tests/integration/compatibility/test_llm_platform.py`
   - Tests: Legacy LLM platform API compatibility

### Scripts to Keep (Not Tests)
These are administrative/utility scripts, not tests:
- `scripts/pytest-for-claude.sh` - Test runner utility
- `scripts/check-test-progress.sh` - Test monitoring
- `scripts/manage-users.sh` - User management
- `scripts/deploy.sh` - Deployment
- `scripts/setup-*.sh` - Setup utilities

## Migration Strategy

### Phase 1: Create pytest Structure
```
tests/
├── integration/
│   ├── chat/
│   │   ├── test_intelligent_routing.py      # NEW
│   │   └── test_mcp_agent_hot_loading.py   # NEW
│   └── compatibility/
│       └── test_llm_platform.py            # NEW
└── performance/
    └── test_kb_storage_performance.py      # NEW
```

### Phase 2: Migrate Test Logic
1. Convert bash test logic to Python pytest
2. Use existing fixtures (shared_test_user, gateway_url, etc.)
3. Maintain same test coverage and assertions
4. Add proper markers (@pytest.mark.integration, @pytest.mark.performance)

### Phase 3: Create Deprecation Scripts
Replace each deprecated test script with:
```bash
#!/bin/bash
echo "⚠️  DEPRECATED: This script has been moved to pytest"
echo "Please use: ./scripts/pytest-for-claude.sh tests/integration/chat/"
echo ""
echo "Specific tests:"
echo "  - Gateway endpoints: tests/integration/gateway/"
echo "  - Streaming: tests/integration/chat/test_unified_streaming_format.py"
exit 1
```

### Phase 4: Update Documentation
1. Update CLAUDE.md testing section
2. Update docs/testing/TESTING_GUIDE.md
3. Remove references to manual test scripts
4. Add migration guide for developers

## Benefits

1. **Single Source of Truth**: All tests in `tests/` directory
2. **Consistent Authentication**: All tests use same auth fixtures
3. **Better CI/CD**: Single pytest command runs everything
4. **Coverage Reporting**: Unified test coverage metrics
5. **Easier Maintenance**: One testing framework to maintain
6. **Better Discovery**: Developers know where to find tests

## Implementation Timeline

1. **Week 1**: Migrate unique test scripts to pytest
2. **Week 2**: Add deprecation notices, update documentation
3. **Week 3**: Monitor and assist developers with transition
4. **Week 4**: Remove deprecated scripts

## Success Criteria

- [ ] All unique test logic migrated to pytest
- [ ] Deprecation notices in place for old scripts
- [ ] Documentation updated
- [ ] No loss of test coverage
- [ ] All tests passing in CI/CD