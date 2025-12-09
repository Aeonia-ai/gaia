# GAIA Platform API Map


This document provides a comprehensive mapping of all API endpoints through the GAIA platform services.

## Architecture Overview

```
Client -> Gateway (port 8666) -> Backend Services
                                  ├── Auth Service (port 8000)
                                  ├── Chat Service (port 8000)
                                  ├── Asset Service (port 8000)
                                  ├── KB Service (port 8000)
                                  └── Web Service (port 8000, exposed as 8080)
```

## Gateway Service (Port 8666)

**Public URL:** https://gaia-gateway-[env].fly.dev  
**Purpose:** Main API gateway and request router  
**Services Proxied:** All backend services  
**Authentication:** Routes authentication to auth service

### API Version Support
- **v0.2** - Legacy LLM Platform compatibility endpoints
- **v0.3** - ✅ Complete authentication endpoints (new)
- **v1** - Modern microservices endpoints
- **Backward Compatibility** - All versions supported simultaneously

The gateway is the main entry point for all API requests and routes them to appropriate backend services.

### Health & Status Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| GET | `/health` | - | - | No | Gateway health check |
| GET | `/` | - | - | Yes (Rate Limited) | Root endpoint with API version info |

### Authentication Endpoints (v1 + v0.3)

#### v1 Authentication Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| POST | `/api/v1/auth/validate` | auth | `/auth/validate` | No | Validate JWT or API key |
| POST | `/api/v1/auth/refresh` | auth | `/auth/refresh` | No | Refresh JWT token |
| POST | `/api/v1/auth/register` | auth | `/auth/register` | No | Register new user |
| POST | `/api/v1/auth/login` | auth | `/auth/login` | No | User login |
| POST | `/api/v1/auth/logout` | auth | `/auth/logout` | No | User logout |
| POST | `/api/v1/auth/confirm` | auth | `/auth/confirm` | No | Confirm email |
| POST | `/api/v1/auth/resend-verification` | auth | `/auth/resend-verification` | No | Resend email verification |

#### v0.3 Authentication Endpoints ✅

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| POST | `/api/v0.3/auth/login` | auth | `/auth/login` | No | User login (same as v1) |
| POST | `/api/v0.3/auth/register` | auth | `/auth/register` | No | User registration (same as v1) |
| POST | `/api/v0.3/auth/logout` | auth | `/auth/logout` | No | User logout (same as v1) |
| POST | `/api/v0.3/auth/validate` | auth | `/auth/validate` | No | Validate JWT (same as v1) |
| POST | `/api/v0.3/auth/refresh` | auth | `/auth/refresh` | No | Refresh JWT (same as v1) |
| POST | `/api/v0.3/auth/confirm` | auth | `/auth/confirm` | No | Confirm email (same as v1) |
| POST | `/api/v0.3/auth/resend-verification` | auth | `/auth/resend-verification` | No | Resend verification (same as v1) |

**✅ Behavioral Identity**: All v0.3 auth endpoints route to identical v1 handlers  
**✅ Token Interoperability**: v1 and v0.3 tokens work across both API versions  
**✅ Test Coverage**: 8 comprehensive integration tests passing

### Chat Endpoints (v1)

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| POST | `/api/v1/chat` | chat | `/chat/unified` | Yes | Main chat endpoint with intelligent routing |
| POST | `/api/v1/chat/completions` | chat | `/chat/` | Yes | OpenAI-compatible completions |
| DELETE | `/api/v1/conversations/{id}` | chat | `/conversations/{id}` | Yes | Delete specific conversation |
| GET | `/api/v1/chat/personas` | chat | `/personas/` | Yes | Get personas |
| POST | `/api/v1/chat/personas` | chat | `/personas` | Yes | Create persona |


### Asset Endpoints (v1)

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| GET | `/api/v1/assets` | asset | `/assets/` | Yes | List assets |
| POST | `/api/v1/assets/generate` | asset | `/assets/request` | Yes | Generate asset |
| GET | `/api/v1/assets/test` | asset | `/assets/test` | No | Test endpoint |
| GET | `/api/v1/assets/{id}` | asset | `/assets/{id}` | Yes | Get specific asset |

### v0.2 API Endpoints

#### Base v0.2 Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| GET | `/api/v0.2/` | chat | `/api/v0.2/` | No | v0.2 API info |
| GET | `/api/v0.2/health` | chat | `/api/v0.2/health` | No | v0.2 health check |

#### v0.2 Chat Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| POST | `/api/v0.2/chat` | chat | `/api/v0.2` | Yes | Unified chat (streaming/non-streaming) |

#### v0.2 Provider & Model Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| GET | `/api/v0.2/providers` | chat | `/api/v0.2/providers/` | Yes | List providers |
| GET | `/api/v0.2/providers/{provider}` | chat | `/api/v0.2/providers/{provider}` | Yes | Get provider details |
| GET | `/api/v0.2/providers/{provider}/models` | chat | `/api/v0.2/providers/{provider}/models` | Yes | Get provider models |
| GET | `/api/v0.2/providers/{provider}/health` | chat | `/api/v0.2/providers/{provider}/health` | Yes | Provider health |
| GET | `/api/v0.2/providers/stats` | chat | `/api/v0.2/providers/stats` | Yes | All provider stats |
| GET | `/api/v0.2/models` | chat | `/api/v0.2/models/` | Yes | List all models |
| GET | `/api/v0.2/models/{model_id}` | chat | `/api/v0.2/models/{model_id}` | Yes | Get model details |

#### v0.2 Asset Pricing & Cost Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| GET | `/api/v0.2/assets/pricing/current` | chat | `/api/v0.2/assets/pricing/current` | Yes | Current pricing |
| GET | `/api/v0.2/assets/pricing/analytics` | chat | `/api/v0.2/assets/pricing/analytics` | Yes | Cost analytics |
| POST | `/api/v0.2/assets/pricing/update` | chat | `/api/v0.2/assets/pricing/update` | Yes | Update pricing |
| POST | `/api/v0.2/assets/pricing/cost-estimator/estimate` | chat | `/api/v0.2/assets/pricing/cost-estimator/estimate` | Yes | Estimate cost |

#### v0.2 Usage Tracking Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| GET | `/api/v0.2/usage/current` | chat | `/api/v0.2/usage/current` | Yes | Current usage |
| GET | `/api/v0.2/usage/history` | chat | `/api/v0.2/usage/history` | Yes | Usage history |
| POST | `/api/v0.2/usage/log` | chat | `/api/v0.2/usage/log` | Yes | Log usage |
| GET | `/api/v0.2/usage/limits` | chat | `/api/v0.2/usage/limits` | Yes | Usage limits |

#### v0.2 Persona Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| GET | `/api/v0.2/personas` | chat | `/api/v0.2/personas/` | Yes | List personas |
| GET | `/api/v0.2/personas/current` | chat | `/api/v0.2/personas/current` | Yes | Get current persona |
| GET | `/api/v0.2/personas/{id}` | chat | `/api/v0.2/personas/{id}` | Yes | Get specific persona |
| POST | `/api/v0.2/personas` | chat | `/api/v0.2/personas/` | Yes | Create persona |
| PUT | `/api/v0.2/personas/{id}` | chat | `/api/v0.2/personas/{id}` | Yes | Update persona |
| DELETE | `/api/v0.2/personas/{id}` | chat | `/api/v0.2/personas/{id}` | Yes | Delete persona |

#### v0.2 KB Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| POST | `/api/v0.2/kb/search` | kb | `/search` | Yes | Search KB |
| POST | `/api/v0.2/kb/read` | kb | `/read` | Yes | Read KB file |
| POST | `/api/v0.2/kb/context` | kb | `/context` | Yes | Load KOS context |
| POST | `/api/v0.2/kb/navigate` | kb | `/navigate` | Yes | Navigate KB index |
| POST | `/api/v0.2/kb/list` | kb | `/list` | Yes | List KB directory |
| POST | `/api/v0.2/kb/write` | kb | `/write` | Yes | Write KB file |
| DELETE | `/api/v0.2/kb/delete` | kb | `/delete` | Yes | Delete KB file |
| POST | `/api/v0.2/kb/move` | kb | `/move` | Yes | Move/rename KB file |
| GET | `/api/v0.2/kb/git/status` | kb | `/git/status` | Yes | Git status |
| GET | `/api/v0.2/kb/cache/stats` | kb | `/cache/stats` | Yes | Cache statistics |
| POST | `/api/v0.2/kb/cache/invalidate` | kb | `/cache/invalidate` | Yes | Invalidate cache |

#### v0.2 Performance Monitoring Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| GET | `/api/v0.2/performance/summary` | chat | `/api/v0.2/performance/summary` | Yes | Performance summary |
| GET | `/api/v0.2/performance/providers` | chat | `/api/v0.2/performance/providers` | Yes | Provider performance |
| GET | `/api/v0.2/performance/stages` | chat | `/api/v0.2/performance/stages` | Yes | Stage timing analysis |
| GET | `/api/v0.2/performance/live` | chat | `/api/v0.2/performance/live` | Yes | Live metrics |
| DELETE | `/api/v0.2/performance/reset` | chat | `/api/v0.2/performance/reset` | Yes | Reset metrics |

### v0.3 Clean API Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| POST | `/api/v0.3/chat` | chat | `/chat/unified` | Yes | Clean chat interface (no provider details) |
| GET | `/api/v0.3/conversations` | chat | `/conversations` | Yes | List conversations (clean format) |
| POST | `/api/v0.3/conversations` | chat | `/conversations` | Yes | Create conversation (clean format) |

### Legacy Endpoints

| Method | Gateway Path | Target Service | Target Path | Auth Required | Description |
|--------|-------------|----------------|-------------|---------------|-------------|
| POST | `/calculator/add` | - | - | No | Legacy calculator (backward compatibility) |

## Backend Services

### Auth Service Endpoints

| Method | Path | Description | Notes |
|--------|------|-------------|-------|
| GET | `/health` | Service health check | Includes route discovery |
| GET | `/status` | Detailed service status | Shows enabled features |
| POST | `/auth/validate` | Validate auth credentials | Supports JWT, API key, service JWT |
| POST | `/auth/register` | Register new user | Via Supabase |
| POST | `/auth/login` | User login | Returns JWT tokens |
| POST | `/auth/refresh` | Refresh JWT | Using refresh token |
| POST | `/auth/logout` | Logout user | Clears session |
| POST | `/auth/confirm` | Confirm email | With verification token |
| POST | `/auth/resend-verification` | Resend verification email | Rate limited |
| POST | `/internal/validate` | Internal auth validation | For inter-service auth |
| POST | `/internal/service-token` | Generate service JWT | For service-to-service |

### Chat Service Endpoints

| Method | Path | Description | Notes |
|--------|------|-------------|-------|
| GET | `/health` | Service health check | With route discovery |
| POST | `/chat/` | Main chat endpoint | Legacy compatibility |
| POST | `/chat/unified` | Unified intelligent routing | Automatic endpoint selection |
| GET | `/chat/metrics` | Unified chat metrics | Routing statistics |
| GET | `/chat/status` | Chat history status | Message count |
| POST | `/chat/multi-provider` | Multi-provider chat | With fallback support |
| POST | `/chat/reload-prompt` | Reload system prompt | Updates all histories |
| DELETE | `/chat/history` | Clear chat history | Memory + Redis |
| POST | `/chat/mcp-agent` | MCP-agent orchestration | Advanced multiagent |
| POST | `/chat/direct` | Direct LLM chat | No framework overhead |
| POST | `/chat/mcp-agent-hot` | Hot-loaded MCP-agent | Keeps agent initialized |
| POST | `/chat/direct-db` | Direct with DB | PostgreSQL memory |
| POST | `/chat/orchestrated` | Orchestrated routing | Dynamic agent spawning |
| POST | `/chat/ultrafast*` | Ultra-fast variants | <1s response times |
| POST | `/chat/gamemaster` | Game Master scenario | Interactive scenes |
| POST | `/chat/worldbuilding` | World building scenario | Specialist agents |
| POST | `/chat/storytelling` | Storytelling scenario | Multi-perspective |
| POST | `/chat/problemsolving` | Problem solving scenario | Expert collaboration |
| GET | `/conversations` | List conversations | For authenticated user |
| POST | `/conversations` | Create conversation | Returns new ID |
| GET | `/conversations/{id}` | Get conversation | With messages |
| PUT | `/conversations/{id}` | Update conversation | Title, preview |
| DELETE | `/conversations/{id}` | Delete conversation | Soft delete |
| POST | `/conversations/{id}/messages` | Add message | To conversation |
| GET | `/conversations/{id}/messages` | Get messages | For conversation |
| GET | `/conversations/search/{query}` | Search conversations | By title/content |
| GET | `/conversations/stats` | Conversation statistics | Counts |
| POST | `/api/v0.2` | v0.2 unified endpoint | Streaming/non-streaming |
| GET | `/api/v0.2/chat/status` | v0.2 chat status | With API version |
| DELETE | `/api/v0.2/chat/history` | v0.2 clear history | Reinitializes prompt |
| POST | `/api/v0.2/chat/reload-prompt` | v0.2 reload prompt | Updates histories |

### Asset Service Endpoints

| Method | Path | Description | Notes |
|--------|------|-------------|-------|
| GET | `/health` | Service health check | Basic health |
| GET | `/` | Service info | Version and endpoints |
| GET | `/assets/` | List assets | Placeholder |
| GET | `/assets/test` | Test endpoint | No auth required |
| POST | `/assets/request` | Request asset generation | Full pipeline |
| GET | `/assets/health` | Asset server health | Detailed status |

### KB Service Endpoints

| Method | Path | Description | Notes |
|--------|------|-------------|-------|
| GET | `/health` | Service health check | With route discovery |
| POST | `/trigger-clone` | Manually trigger git clone | Testing only |
| POST | `/search` | Search KB with ripgrep | Full-text search |
| POST | `/context` | Load KOS context | By name |
| POST | `/multitask` | Execute multiple KB tasks | Parallel execution |
| POST | `/navigate` | Navigate KB index | Manual index system |
| POST | `/synthesize` | Synthesize insights | Across contexts |
| POST | `/threads` | Get active KOS threads | With filters |
| POST | `/read` | Read specific KB file | By path |
| POST | `/list` | List KB directory | Files in directory |
| GET | `/cache/stats` | Cache statistics | Hit rates, size |
| POST | `/cache/invalidate` | Invalidate cache | By pattern |
| POST | `/write` | Write/update KB file | Creates Git commit |
| DELETE | `/delete` | Delete KB file | Creates Git commit |
| POST | `/move` | Move/rename KB file | Creates Git commit |
| GET | `/git/status` | Git repository status | Modified files |
| POST | `/sync/from-git` | Sync from Git to DB | Pull latest |
| POST | `/sync/to-git` | Sync from DB to Git | Export and commit |
| GET | `/sync/status` | Sync status | Git vs DB state |
| GET | `/api/v0.2/kb/status` | v0.2 KB status | Compatibility |

### Web Service Endpoints

| Method | Path | Description | Notes |
|--------|------|-------------|-------|
| GET | `/` | Home page | Redirects based on auth |
| GET | `/login` | Login page | With email verification support |
| GET | `/register` | Registration page | Supabase integration |
| GET | `/email-verification` | Email verification notice | After registration |
| GET | `/health` | Health check | Service status |
| GET | `/logout` | Logout | Clears session |
| GET | `/chat` | Main chat interface | Protected route |
| GET | `/chat/{conversation_id}` | Load specific conversation | HTMX support |
| POST | `/chat/new` | Create new conversation | Returns fresh UI |
| POST | `/auth/dev-login` | Dev login bypass | Debug mode only |
| POST | `/auth/test-login` | Test login | TEST_MODE=true only |
| POST | `/auth/login` | Handle login form | Supabase auth |
| POST | `/auth/register` | Handle registration | Email verification |
| GET | `/auth/confirm` | Email confirmation | From Supabase link |
| POST | `/auth/resend-verification` | Resend verification | Rate limited |
| POST | `/api/chat/send` | Send chat message | Creates conversation |
| GET | `/api/chat/response` | Get chat response | Non-streaming fallback |
| GET | `/api/conversations` | Get conversation list | For sidebar |
| DELETE | `/api/conversations/{id}` | Delete conversation | Updates list |
| GET | `/api/search-conversations` | Search conversations | By query |
| GET | `/debug/htmx` | HTMX debug test | Development |
| GET | `/debug/swap-test` | innerHTML swap test | Development |
| GET | `/test/htmx` | HTMX test endpoint | Development |
| GET | `/test/conversation-switch` | Conversation switch test | Development |

## Authentication Flow

1. **API Key Authentication**:
   - Client sends `X-API-Key` header
   - Gateway validates with auth service
   - Auth service checks database for user-associated API key

2. **JWT Authentication**:
   - Client sends `Authorization: Bearer <token>` header
   - Gateway validates with auth service
   - Auth service validates Supabase JWT or service JWT

3. **Service-to-Service Authentication**:
   - Services request JWT from auth service `/internal/service-token`
   - Use service JWT for inter-service calls
   - Validated by auth service

## Key Features by Version

### v0.1 (Legacy)
- Basic chat functionality
- API key authentication only
- Single provider support

### v0.2 (Current)
- Unified streaming/non-streaming endpoint
- Multi-provider support with fallback
- Provider/model selection
- Performance monitoring
- Usage tracking
- Persona management
- KB integration

### v0.3 (Clean Interface)
- No provider details exposed
- Simplified request/response format
- Server-side intelligence hidden
- Consistent streaming format

## Response Formats

### v0.2 Non-Streaming Response
```json
{
  "response": "AI response text",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  },
  "response_time_ms": 1234,
  "reasoning": "Model selection reasoning",
  "fallback_used": false
}
```

### v0.2 Streaming Response (SSE)
```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### v0.3 Clean Response
```json
{
  "response": "AI response text"
}
```

### v0.3 Clean Streaming (SSE)
```
data: {"type": "content", "content": "Hello"}
data: {"type": "content", "content": " there!"}
data: {"type": "done"}
```

## Rate Limiting

- Root endpoint: Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_PERIOD`
- Uses Redis for distributed rate limiting when available
- Key generation: JWT hash > API key hash > IP address

## Error Handling

All services return consistent error format:
```json
{
  "detail": "Error message"
}
```

HTTP status codes:
- 400: Bad Request (validation errors)
- 401: Unauthorized (auth required)
- 403: Forbidden (insufficient permissions)
- 404: Not Found
- 429: Too Many Requests (rate limited)
- 500: Internal Server Error
- 503: Service Unavailable