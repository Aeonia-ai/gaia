# Unity Integration Guide for GAIA Platform

**Purpose**: Quick reference for Unity developers integrating with GAIA chat services

## Essential Documentation

1. **[Action Items](../unity-chatclient-feedback-action-items.md)** - Specific fixes needed for ChatClient
2. **[Streaming API Guide](../reference/api/streaming/streaming-api-guide.md)** - SSE implementation details
3. **[Client API Reference](../reference/api/reference/CLIENT_API_REFERENCE.md)** - Endpoint specifications

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

### C# Streaming Implementation with Best.HTTP

**Important**: EventSource class cannot be used here because it only supports GET requests. GAIA's streaming API requires a POST request with JSON body, so we must use the `OnStreamingData` callback approach.

```csharp
using BestHTTP;
using System;
using UnityEngine;

public class ChatStreamingClient : MonoBehaviour
{
    private string apiKey = "YOUR_API_KEY";
    private StringBuilder fullMessage = new StringBuilder();
    
    public void SendMessage(string message, bool stream = false)
    {
        var request = new HTTPRequest(
            new Uri("https://gaia-gateway-dev.fly.dev/api/v0.3/chat"),
            HTTPMethods.Post
        );
        
        request.SetHeader("X-API-Key", apiKey);
        request.SetHeader("Content-Type", "application/json");
        request.SetHeader("Accept", "text/event-stream");
        
        // Create streaming request payload
        var payload = new
        {
            message = message,
            stream = true
        };
        
        request.RawData = System.Text.Encoding.UTF8.GetBytes(
            JsonUtility.ToJson(payload)
        );
        
        // Enable streaming
        request.OnStreamingData += OnStreamingData;
        request.DisableCache = true;
        
        request.Send();
    }
    
    private bool OnStreamingData(HTTPRequest req, HTTPResponse resp, 
                                 byte[] dataFragment, int dataFragmentLength)
    {
        string chunk = System.Text.Encoding.UTF8.GetString(
            dataFragment, 0, dataFragmentLength
        );
        
        // Parse SSE events line by line
        var lines = chunk.Split('\n');
        foreach (var line in lines)
        {
            if (line.StartsWith("data: "))
            {
                ProcessSSEData(line.Substring(6));
            }
        }
        
        return true; // Continue streaming
    }
    
    private void ProcessSSEData(string data)
    {
        if (data == "[DONE]")
        {
            Debug.Log("Stream complete");
            OnChatComplete(fullMessage.ToString());
            return;
        }
        
        try
        {
            var evt = JsonUtility.FromJson<SSEEvent>(data);
            
            switch (evt.type)
            {
                case "content":
                    fullMessage.Append(evt.content);
                    // Update UI progressively
                    UpdateChatBubble(evt.content);
                    break;
                    
                case "start":
                    Debug.Log($"Stream started: {evt.timestamp}");
                    break;
                    
                case "done":
                    Debug.Log($"Finished: {evt.finish_reason}");
                    break;
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning($"Could not parse SSE data: {e.Message}");
        }
    }
    
    private void UpdateChatBubble(string textChunk)
    {
        // Append text to UI as it arrives
        // Your UI update code here
    }
    
    private void OnChatComplete(string fullResponse)
    {
        // Extract and process directives
        ParseDirectives(fullResponse);
    }
    
    private void ParseDirectives(string response)
    {
        var pattern = @"\{""m"":""([^""]+)"",""p"":\{([^}]+)\}\}";
        var matches = System.Text.RegularExpressions.Regex.Matches(response, pattern);
        
        foreach (System.Text.RegularExpressions.Match match in matches)
        {
            ProcessDirective(match.Value);
        }
    }
    
    private void ProcessDirective(string directiveJson)
    {
        // Parse and execute directive
        Debug.Log($"Directive: {directiveJson}");
    }
}

[System.Serializable]
public class SSEEvent
{
    public string type;
    public string content;
    public string timestamp;
    public string finish_reason;
}
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