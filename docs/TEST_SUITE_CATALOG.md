# Gaia Platform Test Suite Catalog

## Overview

This document provides a comprehensive catalog of all tests in the Gaia Platform, organized by type, detailing what each tests, how it tests, and whether it uses mocks or real services.

## Test Organization

```
tests/
├── unit/           # Fast, isolated component tests with mocks
├── integration/    # API endpoint tests with real services
├── e2e/           # Browser-based end-to-end tests with real auth
├── fixtures/      # Shared test utilities and auth management
└── web/           # Web-specific test configurations
```

## Unit Tests (`tests/unit/`)

Unit tests focus on isolated component testing with mocked dependencies. They run quickly and don't require external services.

### test_auth_flow.py
**Purpose**: Tests authentication flows for the web service
**Mocking**: Yes - Mocks GaiaAPIClient responses
**Authentication**: Simulated JWT tokens

Key tests:
- `test_login_endpoint_is_public` - Ensures login doesn't require auth
- `test_register_endpoint_is_public` - Ensures registration is public
- `test_login_with_valid_credentials` - Tests successful login flow
- `test_register_with_valid_data` - Tests user registration
- `test_email_confirmation_flow` - Tests email verification process

### test_authentication_consistency.py
**Purpose**: Ensures authentication behavior consistency
**Mocking**: Yes - Mocks HTTP responses
**Authentication**: Tests various auth header formats

Key tests:
- `test_no_auth_returns_401` - Verifies unauthenticated requests fail
- `test_invalid_auth_returns_401` - Tests invalid auth rejection
- `test_valid_auth_succeeds` - Confirms valid auth works

### test_db_persistence.py
**Purpose**: Tests database connection persistence
**Mocking**: Yes - Mocks asyncpg connections
**Authentication**: N/A (infrastructure test)

Key tests:
- `test_get_connection_creates_new` - Tests connection creation
- `test_get_connection_reuses_existing` - Tests connection pooling
- `test_close_connection` - Tests proper cleanup

### test_error_handling.py
**Purpose**: Tests error response formatting
**Mocking**: No
**Authentication**: N/A

Key tests:
- `test_create_error_response` - Verifies error format
- `test_error_response_content` - Checks error details
- `test_custom_status_codes` - Tests various HTTP status codes

### test_simple.py
**Purpose**: Basic functionality tests
**Mocking**: No
**Authentication**: N/A

Key tests:
- `test_addition` - Simple arithmetic test (sanity check)

### test_ui_layout.py
**Purpose**: Tests UI rendering and layout
**Mocking**: Yes - Mocks FastHTML components
**Authentication**: Simulated sessions

Key tests:
- `test_chat_layout_renders` - Verifies chat UI structure
- `test_login_form_renders` - Tests login form generation
- `test_responsive_design_classes` - Checks CSS classes

## Integration Tests (`tests/integration/`)

Integration tests verify API endpoints work correctly with real services running in Docker.

### test_working_endpoints.py
**Purpose**: Core endpoint functionality testing
**Mocking**: No - Uses real services
**Authentication**: API key from environment
**Coverage**: 11 tests

Key tests:
- `test_health_check` - Gateway health endpoint
- `test_service_status` - Individual service status
- `test_providers_endpoint` - AI provider listing
- `test_models_endpoint` - Model availability
- `test_v02_chat_completion` - v0.2 chat API
- `test_v1_chat_stream` - v1 streaming chat

### test_v02_chat_api.py
**Purpose**: Comprehensive v0.2 API testing
**Mocking**: No - Real gateway/chat service
**Authentication**: API key
**Coverage**: 14 tests

Key tests:
- `test_chat_simple_completion` - Basic chat functionality
- `test_chat_with_conversation_id` - Conversation management
- `test_streaming_chat` - SSE streaming responses
- `test_model_not_found` - Error handling
- `test_conversation_history` - Message persistence
- `test_parallel_conversations` - Concurrent usage

### test_v03_api.py
**Purpose**: Clean v0.3 API testing
**Mocking**: No
**Authentication**: API key
**Coverage**: Multiple endpoint tests

Key tests:
- `test_v03_providers` - Provider listing without internal details
- `test_v03_models` - Model listing in clean format
- `test_v03_health` - Service health without internal info
- `test_v03_no_internal_keys` - Ensures no auth details leak

### test_kb_endpoints.py
**Purpose**: Knowledge Base functionality
**Mocking**: No - Real KB service
**Authentication**: API key
**Coverage**: 12 tests

Key tests:
- `test_kb_health` - KB service health
- `test_kb_search` - Document search functionality
- `test_kb_repository_status` - Git sync status
- `test_kb_list_documents` - Document listing
- `test_kb_add_document` - Document creation

### test_provider_model_endpoints.py
**Purpose**: Provider and model management
**Mocking**: No
**Authentication**: API key
**Coverage**: 11 tests

Key tests:
- `test_list_providers` - All providers listing
- `test_provider_details` - Individual provider info
- `test_list_models` - Available models
- `test_model_search` - Model filtering
- `test_provider_model_association` - Relationship validation

### test_comprehensive_suite.py
**Purpose**: End-to-end integration scenarios
**Mocking**: No
**Authentication**: API key
**Coverage**: 8 comprehensive tests

Key tests:
- `test_complete_chat_flow` - Full chat lifecycle
- `test_streaming_chat_flow` - Streaming with conversation
- `test_provider_model_integration` - Provider/model usage
- `test_concurrent_operations` - Parallel request handling
- `test_performance_monitoring` - Response time checks

### test_api_endpoints_comprehensive.py
**Purpose**: Additional API coverage
**Mocking**: No
**Authentication**: API key
**Coverage**: 9 tests

Key tests:
- `test_invalid_endpoints` - 404 handling
- `test_method_not_allowed` - HTTP method validation
- `test_request_validation` - Input validation
- `test_cors_headers` - CORS configuration

## End-to-End Tests (`tests/e2e/`)

E2E tests use Playwright for browser automation and MUST use real Supabase authentication.

### test_real_auth_e2e.py ⭐ (Primary E2E Test)
**Purpose**: Complete user journey with real authentication
**Mocking**: NO - Real Supabase authentication only
**Authentication**: Creates real Supabase users
**Browser**: Headless Chromium

Key tests:
- `test_real_login_and_logout` - Full auth cycle
- `test_real_chat_functionality` - Authenticated chat
- `test_registration_flow` - New user registration
- `test_session_persistence` - Cookie management
- `test_concurrent_users` - Multi-user scenarios

```python
# Example pattern used:
factory = TestUserFactory()
user = factory.create_verified_test_user(
    email=f"e2e-{uuid.uuid4().hex[:8]}@test.local",
    password="TestPassword123!"
)
# Perform real login through UI
```

### test_authenticated_browser.py
**Purpose**: Tests authenticated browser sessions
**Mocking**: Mixed - Can use mocked or real auth
**Authentication**: Flexible based on test needs
**Browser**: Playwright

Key tests:
- `test_login_redirects_to_chat` - Post-login navigation
- `test_chat_requires_authentication` - Auth enforcement
- `test_logout_functionality` - Session cleanup

### test_full_web_browser.py
**Purpose**: Comprehensive web UI testing
**Mocking**: Real services
**Authentication**: Real Supabase
**Browser**: Full browser automation

Key tests:
- `test_responsive_design` - Mobile/desktop layouts
- `test_form_validation` - Client-side validation
- `test_error_handling` - UI error states
- `test_loading_states` - Progress indicators

### test_browser_edge_cases.py
**Purpose**: Edge cases and error scenarios
**Mocking**: No
**Authentication**: Real auth
**Browser**: Playwright with error monitoring

Key tests:
- `test_console_errors` - JavaScript error detection
- `test_memory_leaks` - Long-running session tests
- `test_race_conditions` - Concurrent UI updates
- `test_browser_back_button` - Navigation handling

### test_chat_browser_auth.py
**Purpose**: Chat-specific browser testing
**Mocking**: No
**Authentication**: Real Supabase users
**Browser**: Headless mode

Key tests:
- `test_send_message` - Message submission
- `test_receive_response` - Response display
- `test_conversation_history` - Message persistence
- `test_auto_scroll` - UI behavior

### test_layout_integrity.py
**Purpose**: UI consistency and layout
**Mocking**: No
**Authentication**: Session-based
**Browser**: Visual testing

Key tests:
- `test_no_flex_col_patterns` - Layout anti-patterns
- `test_consistent_spacing` - Design system adherence
- `test_color_palette` - Theme consistency
- `test_responsive_breakpoints` - Media queries

## Test Fixtures and Utilities

### fixtures/test_auth.py
**Purpose**: Centralized authentication management
**Provides**:
- `TestAuthManager` - Unified auth handling
- `TestUserFactory` - Real Supabase user creation
- JWT token generation
- User cleanup utilities

## Test Execution

### Running Tests by Category

```bash
# Unit tests (fast, mocked)
./scripts/pytest-for-claude.sh tests/unit -v

# Integration tests (real services)
./scripts/pytest-for-claude.sh tests/integration -v

# E2E tests (requires SUPABASE_SERVICE_KEY)
./scripts/pytest-for-claude.sh tests/e2e -v

# All tests
./scripts/pytest-for-claude.sh
```

### Test Markers

```python
@pytest.mark.unit          # Fast, isolated tests
@pytest.mark.integration   # API endpoint tests
@pytest.mark.e2e          # Browser-based tests
@pytest.mark.slow         # Tests taking >2 seconds
@pytest.mark.container_safe  # Can run in Docker
@pytest.mark.host_only    # Requires Docker access
```

## Authentication Approaches by Test Type

| Test Type | Authentication Method | Real Supabase? | Speed |
|-----------|---------------------|----------------|--------|
| Unit | Mocked JWT tokens | No | Fast (<100ms) |
| Integration | API keys from env | No | Medium (~500ms) |
| E2E | Real user creation | Yes | Slow (2-5s) |

## Key Testing Principles

1. **Unit Tests**: Mock everything external, test logic only
2. **Integration Tests**: Test real API contracts, use Docker networking
3. **E2E Tests**: NO MOCKS - real users, real auth, real browser
4. **Async Execution**: Use `pytest-for-claude.sh` to avoid timeouts
5. **Cleanup**: Always clean up test data, especially Supabase users

## Coverage Summary

- **Total Test Files**: 45+
- **Unit Tests**: ~15 tests across 6 files
- **Integration Tests**: ~65 tests across 10 files  
- **E2E Tests**: ~50 tests across 20+ files
- **Total Coverage**: ~130+ individual test cases

## Performance Benchmarks

- Unit test suite: ~2 seconds
- Integration test suite: ~30 seconds
- E2E test suite: ~2-5 minutes
- Full test suite: ~5-10 minutes

Note: Always use `./scripts/pytest-for-claude.sh` for full test runs to avoid Claude Code's 2-minute timeout!