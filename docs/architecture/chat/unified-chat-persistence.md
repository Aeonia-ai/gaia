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

## Future Considerations

1. **Web UI Simplification**: Remove redundant conversation logic
2. **Format Migration**: Move to v0.3 for all clients
3. **SSE Improvements**: Better fallback handling for test environments
4. **Performance**: Conversation persistence adds minimal overhead

## Conclusion

The unified chat persistence is fully implemented and working. The web UI already benefits from it through the gateway routing, though it could be simplified by removing its redundant conversation management code.