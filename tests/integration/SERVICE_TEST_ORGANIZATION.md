# Service-Specific Integration Test Organization

This document describes the new service-specific organization of integration tests for better maintainability and clarity.

## Directory Structure

```
tests/integration/
├── auth/           # Authentication Service Tests
├── chat/           # Chat Service Tests  
├── gateway/        # Gateway Service Tests
├── kb/             # Knowledge Base Service Tests
├── asset/          # Asset Service Tests (placeholder)
├── web-service/    # Web UI Service Tests
├── system/         # System-Wide Integration Tests
├── general/        # Cross-Service Integration Tests
└── web/            # Browser-Based Tests (existing)
```

## Service Breakdown

### 🔐 Authentication Service (`auth/`)
**Purpose**: Tests for Supabase auth integration, API key validation, and service health
- `test_auth_service_health.py` - Auth service health checks
- `test_auth_supabase_integration.py` - Supabase authentication flows
- `test_auth_web_integration.py` - Web UI authentication integration
- `test_supabase_api_key_fix.py` - API key validation fixes

**Coverage**: JWT validation, session management, user registration/login

### 💬 Chat Service (`chat/`)
**Purpose**: Tests for all chat functionality, conversation management, and API versions
- `test_api_v02_chat_endpoints.py` - v0.2 chat API endpoints
- `test_api_v02_completions_auth.py` - v0.2 completions with auth
- `test_api_v03_endpoints.py` - v0.3 clean API endpoints  
- `test_api_v03_conversations.py` - v0.3 conversation management
- `test_api_v03_conversations_auth.py` - v0.3 auth integration
- `test_api_v03_conversation_persistence.py` - Conversation persistence
- `test_conversation_delete.py` - Conversation deletion
- `test_conversation_persistence.py` - General persistence tests
- `test_format_negotiation.py` - Response format negotiation
- `test_personas_api.py` - Chat personas functionality
- `test_unified_chat_endpoint.py` - Unified chat interface
- `test_unified_streaming_format.py` - Streaming responses

**Coverage**: All chat APIs, streaming, conversation management, personas

### 🚪 Gateway Service (`gateway/`)
**Purpose**: Tests for gateway routing, authentication passthrough, and API forwarding
- `test_gateway_auth_endpoints.py` - Gateway auth endpoint forwarding
- `test_gateway_client.py` - Gateway client functionality
- `test_web_gateway_integration.py` - Web UI through gateway
- `test_web_gateway_simple.py` - Simple gateway functionality

**Coverage**: Request forwarding, error handling, authentication passthrough

### 📚 Knowledge Base Service (`kb/`)
**Purpose**: Tests for KB functionality, search, and integration
- `test_kb_endpoints_validation.py` - KB endpoint validation
- `test_kb_gateway_integration.py` - KB through gateway
- `test_kb_service_direct.py` - Direct KB service tests

**Coverage**: KB search, integration, MCP tools

### 🌐 Web Service (`web-service/`)
**Purpose**: Tests for FastHTML web UI, HTMX patterns, and frontend functionality
- `test_migration_web_ui_v03.py` - v0.3 web UI migration
- `test_web_conversations_api.py` - Web conversation API
- `test_web_style_conversation.py` - Web UI conversation styling

**Coverage**: HTMX integration, web UI patterns, frontend API

### 🏗️ System Tests (`system/`)
**Purpose**: System-wide integration tests, health checks, and cross-service functionality
- `test_services_health.py` - All service health checks
- `test_system_comprehensive.py` - Comprehensive system tests
- `test_system_microservices.py` - Microservice integration
- `test_system_regression.py` - Regression test suite

**Coverage**: Service communication, system health, end-to-end flows

### 🔄 General Tests (`general/`)
**Purpose**: Cross-service tests that don't fit into a single service category
- `test_api_endpoints_comprehensive.py` - Comprehensive API testing
- `test_migration_format_planning.py` - Migration planning
- `test_provider_model_endpoints.py` - Provider/model endpoint tests
- `test_roadmap_unified_endpoint.py` - Unified endpoint roadmap

**Coverage**: Multi-service workflows, migration tests, comprehensive API coverage

### 🖥️ Asset Service (`asset/`)
**Purpose**: Asset management and file handling tests
- (Currently empty - placeholder for future asset service tests)

## Testing Commands by Service

### Run tests for specific services:
```bash
# Auth service tests
./scripts/pytest-for-claude.sh tests/integration/auth/ -v

# Chat service tests  
./scripts/pytest-for-claude.sh tests/integration/chat/ -v

# Gateway service tests
./scripts/pytest-for-claude.sh tests/integration/gateway/ -v

# KB service tests
./scripts/pytest-for-claude.sh tests/integration/kb/ -v

# Web service tests
./scripts/pytest-for-claude.sh tests/integration/web-service/ -v

# System-wide tests
./scripts/pytest-for-claude.sh tests/integration/system/ -v

# All integration tests
./scripts/pytest-for-claude.sh tests/integration/ -v
```

## Benefits of This Organization

1. **🎯 Focused Testing**: Developers can run tests specific to their service
2. **🔍 Clear Ownership**: Each service team owns their test directory
3. **🚀 Faster Debugging**: Easier to find relevant tests when issues occur
4. **📈 Better Coverage**: Clear visibility into what each service tests
5. **🔄 Parallel Development**: Teams can work on tests independently
6. **📊 Metrics**: Better test metrics per service

## Migration Notes

- All existing tests have been moved to appropriate directories
- No test functionality has been changed - only organization
- Import paths remain the same (relative imports work correctly)
- Shared fixtures in `conftest.py` are still available to all tests
- Browser tests remain in the `web/` directory for clarity

## Next Steps

1. ✅ **File Organization**: Complete (all tests moved)
2. 🔄 **Test Suite Creation**: Create service-specific test suites
3. 📊 **Documentation**: Update CI/CD to use service-specific test runs
4. 🎯 **Coverage Analysis**: Generate service-specific coverage reports

This organization aligns with our microservices architecture and makes test maintenance significantly easier.