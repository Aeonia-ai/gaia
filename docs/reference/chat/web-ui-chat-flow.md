# Web UI Chat Flow Architecture



## Overview

This document describes how the web UI handles chat interactions, including the current implementation and opportunities for simplification.

## Current Implementation

### 1. Message Flow

```
User Input → Web UI → Gateway → Chat Service (Unified) → AI Response
     ↓                    ↓                                    ↓
Browser SSE ← Web UI ← Gateway ← Chat Service ← LLM Provider
```

### 2. Key Components

#### Web UI (`/app/services/web`)
- **Endpoint**: `/api/chat/send`
- **Creates conversation** via chat service
- **Streams response** using EventSource (SSE)
- **Manually saves** AI responses back to chat service
- **Updates conversation list** via HTMX

#### Gateway (`/app/gateway`)
- **Endpoint**: `/api/v1/chat`
- **Routes to**: `/chat/unified` (intelligent routing)
- **Handles auth**: API keys and JWTs
- **Forwards streaming**: SSE pass-through

#### Chat Service (`/app/services/chat`)
- **Endpoint**: `/chat/unified`
- **Intelligent routing**: Direct, KB tools, MCP agent
- **Conversation persistence**: Automatic (new!)
- **Response formats**: OpenAI (default), v0.3

### 3. Redundant Operations

The web UI currently performs redundant conversation management:

```python
# Web UI creates conversation
conversation_id = await chat_service_client.create_conversation(user_id, message)

# Then calls gateway (which calls unified endpoint)
async with GaiaAPIClient() as client:
    async for chunk in client.chat_completion_stream(messages, jwt_token):
        # Process streaming response

# Then manually saves AI response
await chat_service_client.add_message(conversation_id, "assistant", response_content)
```

**This is redundant** because the unified endpoint now handles all of this automatically!

## Simplification Opportunities

### 1. Remove Manual Conversation Management

The unified endpoint already:
- Creates conversations on first message
- Saves all messages (user and AI)
- Returns conversation_id in metadata

### 2. Switch to v0.3 Format

Current: OpenAI format (complex parsing)
```json
{
  "choices": [{
    "delta": {"content": "..."},
    "finish_reason": null
  }]
}
```

Better: v0.3 format (clean)
```json
{
  "type": "content",
  "content": "...",
  "conversation_id": "..."
}
```

### 3. Simplified Web UI Flow

```python
# Just send message and handle response
async def send_message(message, conversation_id=None):
    # Call gateway with v0.3 format
    response = await gateway.chat(
        message=message,
        conversation_id=conversation_id,
        format="v0.3"
    )
    
    # Extract conversation_id from response
    new_conversation_id = response.metadata.get("conversation_id")
    
    # That's it! No manual saving needed
```

## SSE Streaming Details

### Current Implementation

1. **Send Message**: POST to `/api/chat/send`
2. **Start SSE**: EventSource to `/api/chat/stream`
3. **Handle Chunks**: Parse OpenAI format chunks
4. **Save Response**: Manual save to chat service

### Issues with Playwright

- EventSource doesn't send cookies in Playwright
- Causes authentication failures in E2E tests
- Works fine in real browsers
- See: [Playwright EventSource Issue](../troubleshooting/playwright-eventsource-issue.md)

## Migration Path

### Phase 1: Use Unified Response Metadata
- Keep current flow
- Use conversation_id from response metadata
- Stop creating conversations manually

### Phase 2: Remove Redundant Saves
- Stop manually saving AI responses
- Trust unified endpoint persistence
- Simplify error handling

### Phase 3: Switch to v0.3 Format
- Change response format to v0.3
- Simplify response parsing
- Cleaner streaming chunks

### Phase 4: Full Simplification
- Remove ChatServiceClient from web UI
- Only use GaiaAPIClient
- Minimal code, maximum functionality

## Benefits

1. **Less Code**: Remove 50%+ of chat handling code
2. **Fewer Bugs**: No sync issues between services
3. **Better Performance**: Fewer API calls
4. **Cleaner Architecture**: Single source of truth

## Conclusion

The web UI is already using the unified chat endpoint indirectly through the gateway. The next step is to remove the redundant conversation management code and fully embrace the unified architecture. This will significantly simplify the codebase while maintaining all functionality.