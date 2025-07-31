# Test Launcher Script Inventory

## 🚀 Main Test Runners (Keep These)

### Primary Automated Test Runners
1. **`test-automated.py`** ✅ - Main Docker-based test runner (pytest wrapper)
2. **`test.sh`** ✅ - Smart API testing script for local/remote environments
3. **`test-comprehensive.sh`** ✅ - Runs comprehensive test suite
4. **`test-host-only.sh`** ✅ - Runs tests that require host Docker access
5. **`run-browser-tests.sh`** ✅ - Dedicated browser test runner

### Secondary Test Runners  
6. **`test-all-organized.sh`** - Organized test runner (might be redundant with test-automated.py)
7. **`pytest-fullsuite-no-timeout.sh`** - Runs full suite without timeouts

## 🛠️ Test Utilities & Analysis (Keep These)

### Test Analysis Tools
- `analyze-test-failures.py` - Analyzes test failure patterns
- `analyze-test-markers.py` - Analyzes pytest markers
- `check-test-progress.sh` - Checks test progress
- `test-status-analysis.py` - Analyzes test status
- `verify-tests-phase3.py` - Verifies phase 3 test implementation

### Test Organization Tools
- `apply-test-markers.py` - Applies pytest markers to tests
- `fix-test-imports.py` - Fixes test import errors
- `migrate-browser-tests.py` - Migrates browser tests to new pattern
- `reorganize-tests.py` - Reorganizes test structure

## 🧪 Manual Test Scripts (Should Convert or Remove)

### Performance Testing (Convert to automated)
- `test-intelligent-routing-performance.sh` - Performance testing for routing
- `test-kb-storage-performance.py` - KB storage performance
- `test-mcp-agent-hot-loading.sh` - MCP agent performance

### Feature Testing (Convert to automated)
- `test-multiuser-kb.py` - Multi-user KB testing
- `test-multiuser-simple.py` - Simple multi-user tests
- `test-rbac-setup.py` - RBAC setup testing
- `test-service-key.py` - Service key authentication
- `test-supabase-table.py` - Supabase table operations

### API Testing (Already automated?)
- `test-ai-response.py` - AI response testing
- `test-chat-automated.py` - Automated chat testing
- `test_streaming_endpoint.py` - Streaming endpoint tests
- `test-web-ui.py` - Web UI testing

### Utility Testing
- `test-intelligent-routing.sh` - Routing logic testing
- `test-kb-remote.sh` - Remote KB testing
- `test-service-discovery.sh` - Service discovery testing
- `test-parity.sh` - Local/remote parity testing
- `test-quick-verify.sh` - Quick verification tests

## 📝 Other Scripts
- `demo-test-outputs.sh` - Demo test output display
- `register-test-user.sh` - User registration helper
- `test_llm_platform_compatibility.sh` - LLM platform compatibility

## Recommendations:

### Keep (9 scripts):
- Primary runners: `test-automated.py`, `test.sh`, `test-comprehensive.sh`, `test-host-only.sh`
- Browser runner: `run-browser-tests.sh`
- Analysis tools: 4 analysis scripts

### Convert to Automated Tests (8 scripts):
- Performance tests (3)
- Feature tests (5)

### Evaluate for Removal (10+ scripts):
- Scripts that duplicate automated test coverage
- Manual API test scripts
- Utility scripts with limited use