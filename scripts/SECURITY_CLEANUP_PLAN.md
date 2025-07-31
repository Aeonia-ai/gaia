# 🚨 CRITICAL SECURITY CLEANUP: Hardcoded API Keys

## Affected Files (10+ files with hardcoded keys):

1. `scripts/test-supabase-jwt.sh` - Hardcoded API key in curl command
2. `scripts/test_streaming_endpoint.py` - API key with fallback to hardcoded value
3. `scripts/test-service-discovery.sh` - Default hardcoded API key
4. `scripts/test-mtls-connections.py` - Multiple hardcoded keys in headers
5. `scripts/test-auth-simple.py` - Hardcoded API key for testing
6. `scripts/tests/test_kb_integration.py` - Hardcoded key in headers
7. `scripts/tests/test_tool_invocation_accuracy.py` - Default parameter with key
8. `scripts/tests/test_single_route.py` - Hardcoded key in headers
9. `scripts/test-multiuser-kb.py` - Multiple hardcoded keys for different users
10. `scripts/test-rbac-setup.py` - Hardcoded keys for RBAC testing

## Action Plan:

### Phase 1: Immediate Removal (HIGH PRIORITY)
1. Delete all manual test scripts with hardcoded keys
2. Replace with environment variable references where needed
3. Convert critical tests to automated tests using proper fixtures

### Phase 2: Automated Test Migration
1. Create `tests/integration/test_unified_auth.py` for auth testing
2. Create `tests/integration/test_rbac.py` for RBAC testing  
3. Use pytest fixtures that generate test API keys dynamically

### Phase 3: Prevention
1. Add pre-commit hook to prevent hardcoded keys
2. Add CI check for common key patterns
3. Document proper testing patterns in testing guide

## Security Principles:
- ❌ NEVER hardcode API keys, JWTs, or secrets
- ✅ Use environment variables for configuration
- ✅ Use test fixtures that generate temporary keys
- ✅ Use Docker secrets for production keys