# 📚 API Reference & Contracts

📍 **Location:** [Home](../README.md) → API

## 🎯 API Documentation Structure

Complete reference for all Gaia Platform API endpoints, contracts, and integration patterns.

### 📁 Documentation Organization

#### [Reference Documentation](reference/)
Complete API references and endpoint mappings
- [GAIA API Reference](reference/GAIA_API_REFERENCE.md) - Full API specification
- [GAIA API Map](reference/GAIA_API_MAP.md) - Endpoint routing and service mapping
- [Client API Reference](reference/CLIENT_API_REFERENCE.md) - Client-specific API documentation

#### [Authentication](authentication/)
Authentication and authorization documentation
- [API Authentication Guide](authentication/api-authentication-guide.md) - Complete auth patterns
- [Gateway Auth Contract](authentication/gateway-auth-api-contract.md) - Gateway authentication spec
- [OAuth 2.0 Extension](authentication/oauth-2-extension-spec.md) - OAuth implementation spec

#### [Chat API](chat/)
Chat service endpoints and routing
- [Chat Endpoint Variants](chat/chat-endpoint-variants-explained.md) - Different chat endpoint types
- [Chat Execution Paths](chat/chat-endpoint-execution-paths.md) - Request flow through chat
- [Intelligent Routing](chat/intelligent-chat-routing.md) - Smart routing implementation
- [Unified Chat Implementation](chat/unified-chat-implementation.md) - Unified chat interface
- [Unified Intelligent Spec](chat/unified-intelligent-chat-spec.md) - Intelligent chat specification

#### [Client Libraries](clients/)
Client SDKs and usage guides
- [Client Usage Guide](clients/client-usage-guide.md) - How to use client libraries
- [GAIA CLI Client](clients/GAIA_CLI_CLIENT.md) - Command-line interface client

#### [v0.3 API](v03/)
Version 0.3 specific documentation
- [v0.3 API Documentation](v03/v03-api-documentation.md) - v0.3 API reference
- [v0.3 Client Specification](v03/v03-client-specification.md) - v0.3 client requirements

### 📋 Cross-Cutting Documentation

#### [API Contracts](api-contracts.md)
**🟢 Status: CURRENT** - Defines which endpoints require authentication and which are public

- **Public Endpoints** - No authentication required (health checks, registration, login)
- **Protected Endpoints** - Require API key or JWT token
- **Service Communication** - Internal endpoint specifications
- **Contract Testing** - Automated validation of API behavior

#### [KB Endpoints](kb-endpoints.md)
Knowledge Base API endpoints and operations
- **Shared Configuration** - Unified authentication across all services
- **Local-Remote Parity** - Same authentication code in all environments
- **Testing Patterns** - How to test authentication flows

### 💬 [Chat Endpoints](chat-endpoint-variants-explained.md)
**🟢 Status: CURRENT** - LLM interaction and streaming endpoints

- **Unified Chat Endpoint** - Single `/chat` endpoint with intelligent routing
- **Streaming Responses** - Server-sent events for real-time AI responses
- **Model Selection** - Multi-provider LLM support (Claude, OpenAI, etc.)
- **Error Handling** - Comprehensive error response patterns

### 📊 [Chat Execution Paths](chat-endpoint-execution-paths.md)
**🟢 Status: CURRENT** - Internal request flow documentation

- **Request Routing** - How gateway routes chat requests
- **Service Orchestration** - Multi-service coordination patterns
- **Performance Optimization** - Caching and response time improvements
- **Debugging Flow** - Tracing requests through the system

### 👥 [Client Usage Guide](client-usage-guide.md)
**🟢 Status: CURRENT** - Integration guide for external clients

- **Unity XR Integration** - VR/AR client connection patterns
- **Mobile Client Setup** - React Native and Unity Mobile AR integration
- **Web Client Examples** - JavaScript/TypeScript integration
- **Authentication Setup** - Client-side auth implementation

### 🗄️ [KB Endpoints](kb-endpoints.md)
**🟢 Status: FULLY OPERATIONAL** - Knowledge Base service API endpoints

- **Core Operations** - Search, read, write, delete, move documents
- **Git Integration** - Repository sync and status endpoints
- **Cache Management** - Performance optimization endpoints
- **AI-Enhanced Chat** - KB-powered chat endpoints with MCP integration
- **25+ REST Endpoints** - Complete CRUD operations via gateway

## 🔄 API Versioning Strategy

### Current Version: Mixed (v0.2 + v0.3 + v1)
- **v0.2** - Legacy LLM Platform compatibility endpoints
- **v0.3** - Clean API format with complete authentication endpoints ✅
- **v1** - Modern microservices endpoints (partial implementation)
- **Gateway Implementation** - Mix of all versions in `app/gateway/main.py`
- **Client Compatibility** - Full backward compatibility maintained

### Version Timeline
- **v0.2** - Legacy LLM Platform compatibility endpoints
- **v0.3** - **NEW** Complete authentication API with behavioral identity ✅
- **v1** - Modern microservices endpoints (partial implementation)
- **v2** - Planned unified API version (future)

### v0.3 Authentication Implementation ✅
- **Complete Auth Endpoints** - All 7 auth operations (login, register, logout, validate, refresh, confirm, resend)
- **Behavioral Identity** - v0.3 endpoints route to v1 handlers with identical responses
- **Token Interoperability** - v1 and v0.3 tokens work across both API versions
- **Full Test Coverage** - 8 comprehensive integration tests passing

## 🧪 Testing Your Integration

### Quick API Tests
```bash
# Test gateway health (public)
curl https://gaia-gateway-staging.fly.dev/health

# Test v0.3 authentication endpoints
curl https://gaia-gateway-staging.fly.dev/api/v0.3/auth/login \
  -d '{"email": "user@example.com", "password": "password"}'

curl https://gaia-gateway-staging.fly.dev/api/v0.3/auth/register \
  -d '{"email": "newuser@example.com", "password": "password"}'

# Test authenticated chat endpoint
curl -H "X-API-Key: your-key" \
  https://gaia-gateway-staging.fly.dev/api/v0.2/chat \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'

# Test streaming endpoint
curl -H "X-API-Key: your-key" \
  https://gaia-gateway-staging.fly.dev/api/v0.2/chat/stream \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'

# Test KB search endpoint
curl -H "X-API-Key: your-key" \
  https://gaia-gateway-staging.fly.dev/api/v0.2/kb/search \
  -d '{"query": "search terms", "max_results": 10}'
```

### Automated Testing
```bash
# Run comprehensive API tests
./scripts/test.sh --staging all

# Test specific endpoint categories
./scripts/test.sh --staging chat
./scripts/test.sh --staging providers
./scripts/test.sh --staging auth
```

## 📊 API Metrics

### Endpoint Coverage
- **100+ Total Endpoints** - Complete LLM Platform compatibility + KB service
- **KB Endpoints** - 25+ fully operational (search, CRUD, Git sync, cache)
- **Chat Endpoints** - Complete with KB-enhanced variants
- **Provider Endpoints** - 9 implemented (vs 20 documented)
- **Streaming Endpoints** - 7 implemented (vs 10 documented)
- **Authentication Endpoints** - Full coverage

### Performance Targets
- **Response Time** - Sub-700ms for VR/AR compatibility
- **Throughput** - 10x traffic handling capacity
- **Availability** - 99.9% uptime with fault isolation
- **Caching** - 97% performance improvement with Redis

## 🔗 See Also

- **🟢 [Current Implementation](../current/README.md)** - What's working now
- **🔐 [Authentication Docs](../current/authentication/)** - Complete auth guides
- **🔧 [Troubleshooting](../current/troubleshooting/)** - Fix API issues
- **🏠 [Documentation Home](../README.md)** - Main index