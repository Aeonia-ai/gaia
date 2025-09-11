# Unity Integration Guide for GAIA Platform

**Purpose**: Quick reference for Unity developers integrating with GAIA chat services

## Essential Documentation

1. **[Action Items](../unity-chatclient-feedback-action-items.md)** - Specific fixes needed for ChatClient
2. **[Streaming API Guide](../api/streaming/streaming-api-guide.md)** - SSE implementation details
3. **[Client API Reference](../api/reference/CLIENT_API_REFERENCE.md)** - Endpoint specifications

## Current Integration Status

### ✅ Working
- Basic HTTP POST to `/api/v0.3/chat`
- Send/receive text messages
- Network connectivity established

### 🔧 Needs Implementation
- Remove local chat history (GAIA handles state)
- Parse message roles (system vs assistant)
- Extract directives from responses
- Add SSE streaming support

## API Endpoint

```csharp
// Endpoint
string apiUrl = "https://gaia-gateway-dev.fly.dev/api/v0.3/chat";

// Headers
headers["X-API-Key"] = "your-api-key";
headers["Content-Type"] = "application/json";
```

## Request/Response Format

### Basic Chat Request
```json
{
  "message": "Hello guardian",
  "conversation_id": "optional-uuid"
}
```

### Basic Response
```json
{
  "response": "Greetings, traveler! I am the forest guardian.",
  "conversation_id": "auto-generated-if-not-provided"
}
```

### Streaming Request
```json
{
  "message": "Tell me about the forest",
  "stream": true,
  "conversation_id": "optional-uuid"
}
```

### Streaming Response (SSE)
```
data: {"type": "start", "timestamp": "2025-01-01T00:00:00Z"}

data: {"type": "content", "content": "The forest is"}

data: {"type": "content", "content": " ancient and magical"}

data: [DONE]
```

## Directive Format

Directives are embedded in chat responses as JSON:

```json
{
  "response": "A fairy appears before you! {\"m\":\"spawn_character\",\"p\":{\"type\":\"fairy\",\"position\":[10,0,5]}}",
  "conversation_id": "uuid"
}
```

### Parsing Directives

```csharp
// Regex to extract directives
string pattern = @"\{""m"":""([^""]+)"",""p"":\{([^}]+)\}\}";

// Example directives
{"m":"spawn_character","p":{"type":"fairy"}}
{"m":"play_effect","p":{"name":"sparkles"}}
{"m":"move_to","p":{"waypoint":"clearing"}}
```

## Message Role Identification

```csharp
public enum MessageRole {
    System,    // Don't display (e.g., "You are a helpful guardian")
    Assistant, // AI responses (parse for directives)
    User       // Player messages
}

// In response handling
if (response.role == "system") {
    // Skip display
} else if (response.role == "assistant") {
    // Display and parse for directives
}
```

## Testing Endpoints

### Diagnostic Endpoint (no state modification)
```bash
POST /api/v0.3/chat/diagnostic
{
  "message": "test",
  "test_mode": true
}
```

### Regular Chat
```bash
POST /api/v0.3/chat
{
  "message": "Hello guardian"
}
```

## Implementation Checklist

### High Priority
- [ ] Remove local history management
- [ ] Add message role parsing
- [ ] Implement directive extraction
- [ ] Create diagnostic test mode

### Medium Priority  
- [ ] Add SSE streaming support
- [ ] Progressive text rendering

### Low Priority
- [ ] Error recovery improvements
- [ ] Connection retry logic

## Quick Test Commands

```bash
# Test basic chat
curl -X POST http://localhost:8666/api/v0.3/chat \
  -H "X-API-Key: test-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello guardian"}'

# Test streaming
curl -X POST http://localhost:8666/api/v0.3/chat \
  -H "X-API-Key: test-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a story", "stream": true}'
```

## Common Issues

### Issue: Chat history confusion
**Solution**: Remove all local history management. GAIA maintains conversation state.

### Issue: System messages displayed to player
**Solution**: Check message role before displaying.

### Issue: Directives not parsed
**Solution**: Look for JSON patterns in assistant messages only.

### Issue: Streaming not working
**Solution**: Set `"stream": true` and implement SSE client.

## Support

- GAIA backend team: Check #backend channel
- Unity questions: Check #unity-dev channel
- API issues: See [API troubleshooting](../api/README.md)