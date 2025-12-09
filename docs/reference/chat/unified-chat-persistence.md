# Unified Chat Persistence Architecture

## Overview
This document describes how conversation persistence works in the GAIA platform's unified chat system, including the relationship between the web UI, gateway, and chat service.

## Key Discoveries

### 1. Gateway Routing Architecture

The system uses a clever routing pattern:
- **Web UI** calls `/api/v1/chat` (standard endpoint)
- **Gateway** routes `/api/v1/chat` → `/chat/unified` 
- **Chat Service** handles via unified endpoint with intelligent routing

This means the web UI benefits from unified chat features without code changes!

#### Gateway Conversation Management (Updated Sept 2025)

The gateway now properly proxies all conversation endpoints to the chat service instead of using mock implementations:

**Conversation Endpoints**:
- `POST /api/v1/conversations` → `POST /chat/conversations`
- `GET /api/v1/conversations/{id}` → `GET /chat/conversations/{id}`
- `GET /api/v1/conversations` → `GET /chat/conversations`
- `DELETE /api/v1/conversations/{id}` → `DELETE /chat/conversations/{id}`

**Authentication Injection Pattern**:
```python
# Gateway adds authentication info to request body
body["_auth"] = auth

# Remove content-length header since we modified the body
headers = dict(request.headers)
headers.pop("content-length", None)
headers.pop("Content-Length", None)

# Proxy to chat service
return await forward_request_to_service(
    service_name="chat",
    path="/conversations",
    method="POST",
    json_data=body,
    headers=headers
)
```

**Chat Service Dual Auth Format**:
```python
# Chat service handles both direct and gateway requests
if "_auth" in body:
    # Gateway format - use auth from body
    auth = body.get("_auth", {})
    title = body.get("title", "New Conversation")
else:
    # Direct format - use auth from dependency injection
    title = body.get("title", "New Conversation")
    # auth already populated from Depends(get_current_auth_legacy)
```

This ensures conversation validation works correctly when chat requests include `conversation_id`.

### 2. Conversation Persistence Implementation

The unified chat endpoint (`/chat/unified`) now includes:
- **Automatic conversation creation** on first message
- **Message persistence** across all routing paths (direct, KB tools, MCP agent)
- **Conversation ID in response metadata** for client tracking

Key code addition:
```python
async def _save_conversation(self, message: str, response: str, context: Dict, auth: Dict) -> str:
    """Save conversation and messages, returning conversation_id"""
    # Implementation saves both user message and AI response
    # Returns conversation_id for client tracking
```

### 3. Response Format Handling

The system supports multiple response formats:
- **OpenAI format** (default) - Compatible with existing clients
- **v0.3 format** - Cleaner response structure
- Format negotiated via `X-Response-Format` header

### 4. Web UI Architecture

Current web UI implementation:
- Uses **OpenAI format** by default (not v0.3 yet)
- Calls gateway's `/api/v1/chat` endpoint
- Has **redundant conversation management** (creates conversations separately)
- Uses **Server-Sent Events (SSE)** for streaming responses

The redundant conversation management could be removed since the unified endpoint handles it.

## Migration Path

To fully utilize unified chat persistence:

1. **Remove redundant conversation management** in web UI
2. **Switch to v0.3 format** for cleaner responses
3. **Rely on unified endpoint's conversation_id** in response metadata
4. **Simplify web UI chat logic** to just send/receive messages

## Testing Insights

### E2E Test Challenges

1. **Fresh User State**: New Supabase users have no pre-existing conversations
2. **EventSource Limitations**: Playwright doesn't send cookies with EventSource
3. **Message Counting**: Must exclude loading indicators ("Gaia is thinking...")

### Test Improvements Made

- Added viewport parameterization (mobile + desktop)
- Fixed logout test for mobile viewports
- Added SSE fallback mechanism for Playwright
- Documented "no mocks in E2E tests" principle

## Architectural Benefits

1. **Backward Compatibility**: Existing clients work without changes
2. **Unified Intelligence**: All chat routes through intelligent routing
3. **Automatic Persistence**: No manual conversation management needed
4. **Consistent Experience**: Same behavior across all entry points

## Critical Architecture Lessons (Sept 2025)

### ❌ **Anti-Pattern: Mixed Mock/Real Implementations**

**Problem**: Gateway had mock conversation endpoints that returned fake UUIDs, but chat service validated conversations exist in real database.

**Symptom**: Chat requests with `conversation_id` returned 404 "Conversation not found" even though conversation creation succeeded.

**Root Cause**: Architecture inconsistency - partially mocked gateway with real backend validation.

### ✅ **Solution: Consistent Service Patterns**

**Principle**: Services should either be fully mocked OR fully connected to real backends.

**Implementation**: Replace all gateway mocks with proper proxying to chat service's real conversation store.

**Benefits**:
- Eliminates validation mismatches
- Provides true end-to-end conversation flow
- Maintains single source of truth for conversation data

### 🔧 **HTTP Protocol Compliance**

**Critical Pattern**: When modifying request bodies for proxying, always remove original content-length headers:

```python
# WRONG - Will cause "Too much data for declared Content-Length" error
body["_auth"] = auth
return await forward_request_to_service(..., headers=dict(request.headers))

# CORRECT - Remove content-length after body modification
body["_auth"] = auth
headers = dict(request.headers)
headers.pop("content-length", None)
headers.pop("Content-Length", None)
return await forward_request_to_service(..., headers=headers)
```

### 📊 **Validation Results**

After implementing proper proxying:
- ✅ All conversation context preservation tests pass
- ✅ Multi-turn conversations work across routing types  
- ✅ Performance targets met (direct ~1s, kb_tools ~3s, mcp_agent ~2s)
- ✅ Zero 404 errors with conversation_id

## Future Considerations

1. **Web UI Simplification**: Remove redundant conversation logic
2. **Format Migration**: Move to v0.3 for all clients
3. **SSE Improvements**: Better fallback handling for test environments
4. **Performance**: Conversation persistence adds minimal overhead

## Conclusion

The unified chat persistence is fully implemented and working. The web UI already benefits from it through the gateway routing, though it could be simplified by removing its redundant conversation management code.