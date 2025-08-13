# API Version Test Split Action Plan

## Overview
This document outlines the systematic approach to splitting 21 test files that currently mix API versions (v1, v0.2, v0.3).

## Files Requiring Split

### Chat Integration Tests (11 files)
1. **test_unified_chat_endpoint.py**
   - Current: Primarily v1 with v0.3 references
   - Action: Keep as v1-only, move v0.3 references to documentation

2. **test_personas_api.py** 
   - Current: v0.2 persona endpoints + v0.3 chat
   - Action: Split into test_v02_personas_api.py and test_v03_personas_integration.py

3. **test_persona_system_prompt.py**
   - Current: Mixed v0.3 and v1
   - Action: Split by version, test persona integration for each

4. **test_api_v03_endpoints.py**
   - Current: Mixed v0.2 and v0.3
   - Action: Remove v0.2 tests, keep v0.3 only

5. **test_api_v1_completions_auth.py**
   - Current: Mixed v0.2 and v1
   - Action: Already split in previous session ✅

6. **test_api_v1_conversations_auth.py**
   - Current: Mixed v0.3 and v1
   - Action: Already split in previous session ✅

7. **test_format_negotiation.py**
   - Current: Tests v0.3 and v1 format negotiation
   - Action: Keep as-is (legitimate cross-version test)

8. **test_api_v02_chat_endpoints.py**
   - Current: Mixed v0.2 and v1
   - Action: Remove v1 references, keep v0.2 only

9. **test_conversation_delete.py**
   - Current: Mixed v0.3 and v1
   - Action: Split into version-specific files

10. **test_routing_with_personas.py**
    - Current: Mixed v0.3 and v1
    - Action: Split routing tests by version

11. **test_unified_streaming_format.py**
    - Current: Mixed v0.3 and v1
    - Action: Split streaming tests by version

### Gateway Tests (6 files)
1. **test_v03_directive_generation.py**
   - Current: Mixed v0.2 and v0.3
   - Action: Focus on v0.3 directive testing only

2. **test_api_key_jwt_exchange.py**
   - Current: Mixed v0.2 and v1
   - Action: Test auth for all versions separately

3. **test_gateway_client.py**
   - Current: Mixed v0.2 and v1
   - Action: Split client tests by version

4. **test_web_gateway_simple.py**
   - Current: Mixed v0.3 and v1
   - Action: Web interface should use v0.3 only

### System/General Tests (4 files)
1. **test_api_endpoints_comprehensive.py**
   - Current: Mixed v0.2 and v1
   - Action: Split comprehensive tests by version

2. **test_roadmap_unified_endpoint.py**
   - Current: Mixed v0.3 and v1
   - Action: Focus on v0.3 future roadmap

3. **test_system_regression.py**
   - Current: Mixed v0.2 and v1
   - Action: Regression tests for each version

4. **test_system_comprehensive.py**
   - Current: Mixed v0.2 and v0.3
   - Action: Comprehensive tests for each version

### Other Tests
1. **test_kb_endpoints_validation.py**
   - Current: Mixed v0.2 and v1
   - Action: KB endpoints per version

2. **test_supabase_api_key_fix.py**
   - Current: Mixed v0.2 and v1
   - Action: Auth tests per version

## Implementation Strategy

### Phase 1: High-Impact Files (Week 1)
- test_personas_api.py → Critical for persona functionality
- test_api_v03_endpoints.py → Core v0.3 functionality
- test_unified_chat_endpoint.py → Core chat functionality
- test_conversation_delete.py → Important CRUD operations

### Phase 2: Gateway & Auth (Week 2)
- test_api_key_jwt_exchange.py → Auth consistency
- test_gateway_client.py → Client library tests
- test_v03_directive_generation.py → v0.3 features
- test_web_gateway_simple.py → Web UI consistency

### Phase 3: System & Comprehensive (Week 3)
- test_api_endpoints_comprehensive.py → Full coverage
- test_system_regression.py → Regression safety
- test_system_comprehensive.py → System-wide tests
- Remaining files

## Guidelines for Splitting

### 1. File Naming Convention
```
# Original mixed file
test_personas_api.py

# Split into version-specific files
test_v02_personas_api.py      # v0.2 persona endpoints
test_v03_personas_chat.py      # v0.3 chat with personas
test_v1_personas_integration.py # v1 OpenAI format with personas
```

### 2. Test Organization
```python
# Each version file should have clear class names
class TestV02PersonasAPI:
    """Test v0.2 persona management endpoints"""

class TestV03PersonasIntegration:
    """Test v0.3 chat with automatic persona integration"""

class TestV1PersonasUsage:
    """Test v1 OpenAI-compatible format with persona context"""
```

### 3. Shared Fixtures
- Keep authentication fixtures in test_auth.py
- Version-specific request builders in each file
- Shared test data in fixtures/test_data.py

### 4. Coverage Requirements
Each split must maintain:
- Basic functionality tests
- Authentication tests  
- Error handling tests
- Integration tests
- Version-specific behavior tests

## Success Criteria
- No test file contains multiple API versions (except legitimate cross-version tests)
- All tests pass after splitting
- Test coverage remains the same or improves
- Clear documentation of version-specific behaviors

## Tracking Progress
- [ ] Phase 1: High-Impact Files (0/4 completed)
- [ ] Phase 2: Gateway & Auth (0/4 completed)  
- [ ] Phase 3: System & Comprehensive (0/13 completed)
- [ ] Documentation updates
- [ ] CI/CD configuration updates

---
*Created: August 2025*
*Total files to split: 21*
*Estimated effort: 3 weeks*