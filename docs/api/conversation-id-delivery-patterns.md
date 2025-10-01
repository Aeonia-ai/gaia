# Conversation ID Delivery Patterns

## Overview

This document explains how conversation IDs are delivered to clients in both streaming and non-streaming responses, why this dual-method approach exists, and how it aligns with industry best practices.

## Current Implementation

### Non-Streaming Responses

For standard synchronous requests (`stream: false`), the conversation ID is returned in the JSON response body:

```json
{
  "response": "Hello! How can I help you today?",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Location**: Root level of JSON response body
**Field name**: `conversation_id`
**Format**: UUID v4 string

### Streaming Responses (SSE)

For Server-Sent Events streaming (`stream: true`), the conversation ID is delivered in the first metadata event:

```
data: {"type": "metadata", "conversation_id": "550e8400-e29b-41d4-a716-446655440000", "model": "unified-chat", "timestamp": 1234567890}

data: {"type": "content", "content": "Hello! "}

data: {"type": "content", "content": "How can I help you today?"}

data: {"type": "done"}
```

**Location**: First SSE event with `type: "metadata"`
**Field name**: `conversation_id` within the metadata object
**Format**: UUID v4 string
**Timing**: Delivered before any content chunks

## Why This Dual-Method Approach?

### Protocol Constraints

1. **Non-streaming**: Returns a complete JSON object after processing
   - Can include all metadata in a single structured response
   - Client receives everything at once

2. **Streaming (SSE)**: Sends line-delimited events over time
   - Cannot modify response structure after streaming starts
   - Must send metadata early for client session management
   - Limited to `data:` prefixed text lines per SSE specification

### Industry Alignment

This pattern matches industry standards:

| Provider | Non-Streaming | Streaming | Pattern |
|----------|--------------|-----------|---------|
| **OpenAI** | `id` in JSON root | `id` in first SSE chunk | Metadata-first |
| **Anthropic** | `conversation_id` in JSON root | `conversation_id` in first event | Metadata-first |
| **Gaia** | `conversation_id` in JSON root | `conversation_id` in metadata event | Metadata-first |

### Best Practice: "Metadata Priming Event"

According to API design experts and industry analysis (2024):

✅ **Recommended Approach**:
- Include essential metadata in the first SSE event for streaming
- Place metadata at root level for non-streaming JSON
- Document extraction patterns clearly
- Maintain consistency in field naming

❌ **Anti-Patterns to Avoid**:
- Using HTTP headers for session IDs (incompatible with some SSE clients)
- Out-of-band metadata delivery
- Omitting metadata from streaming responses
- Requiring side-channel extraction

## Client Implementation Guide

### Recommended Extraction Logic

```csharp
// C# Unity Example
public class ConversationIdExtractor
{
    public string ExtractConversationId(Response response)
    {
        // Non-streaming: Extract from JSON body
        if (!response.IsStreaming)
        {
            return response.Body?.ConversationId;
        }

        // Streaming: Extract from first metadata event
        var firstEvent = response.GetFirstEvent();
        if (firstEvent?.Type == "metadata")
        {
            return firstEvent.ConversationId;
        }

        return null;
    }
}
```

### What NOT to Implement

- ❌ **HTTP Header Extraction**: Gaia does not use `X-Conversation-Id` headers
- ❌ **Auto-Generation**: Only for mock/test scenarios, not production
- ❌ **Complex Fallback Chains**: The ID is always present in the documented location

## Technical Rationale

### Why Not Use Headers?

While headers would provide a unified extraction point, they have limitations:
1. SSE client libraries often don't expose response headers
2. Some proxies/CDNs strip custom headers
3. Browser EventSource API has limited header access

### Why Not Always Stream?

While forcing all responses through SSE would unify extraction:
1. Adds overhead for simple request-response patterns
2. Increases complexity for non-real-time use cases
3. Not all clients need or want streaming

### Why This Pattern Works

1. **Clear Separation**: Different transport methods for different use cases
2. **Early Delivery**: Clients get conversation ID before processing content
3. **Industry Standard**: Matches OpenAI, Anthropic, and other major APIs
4. **Protocol Respect**: Works within SSE and HTTP constraints

## Migration Guide

If updating from older client implementations:

### Remove These Patterns
```csharp
// OLD: Header extraction (not used by Gaia)
var conversationId = response.Headers["X-Conversation-Id"];

// OLD: Complex fallback chains
var conversationId = response.Body?.ConversationId
    ?? response.Headers["X-Conversation-Id"]
    ?? GenerateGuid();  // Only for mocks
```

### Use This Pattern
```csharp
// NEW: Simple dual extraction
var conversationId = isStreaming
    ? GetFromFirstMetadataEvent(response)
    : response.Body?.ConversationId;
```

## Version History

- **v0.3** (Current): Dual-method delivery (JSON body + SSE metadata)
- **v0.2** (Deprecated): Various experimental patterns
- **v0.1** (Removed): Header-based delivery

## References

- [SSE Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [OpenAI Streaming Documentation](https://platform.openai.com/docs/api-reference/chat/create#chat-create-stream)
- [Anthropic Messages API](https://docs.anthropic.com/claude/reference/messages-streaming)
- Industry analysis via Perplexity AI (September 2024)

## Conclusion

The dual-method approach for conversation ID delivery is not a design flaw but a necessary adaptation to protocol constraints. It aligns with industry best practices and provides a reliable, predictable pattern for clients to implement. The key is clear documentation and consistent implementation across both delivery methods.