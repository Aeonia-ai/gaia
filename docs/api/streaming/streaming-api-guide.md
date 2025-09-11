# Streaming API Guide

**Created**: January 2025  
**Purpose**: Document how to use GAIA's streaming API for real-time responses

## Overview

GAIA provides Server-Sent Events (SSE) streaming for real-time AI responses. This is crucial for VR/AR applications where immediate feedback improves user experience.

## How Streaming Works

Streaming in GAIA is handled through the **unified chat endpoint** with a `stream` parameter:

- **Endpoint**: `/api/v0.3/chat` (recommended) or `/api/v1/chat`
- **Parameter**: `"stream": true` in request body
- **Response**: Server-Sent Events (SSE) with `text/event-stream` content type

## API Usage

### Request Format

```json
POST /api/v0.3/chat
Content-Type: application/json
X-API-Key: YOUR_API_KEY

{
  "message": "Your question here",
  "stream": true,
  "conversation_id": "optional-id"
}
```

### Response Format (SSE)

The response is a stream of Server-Sent Events, each on its own line:

```
data: {"type": "start", "timestamp": "2025-01-01T00:00:00Z"}

data: {"type": "content", "content": "Here is"}

data: {"type": "content", "content": " the response"}

data: {"type": "content", "content": " streaming in"}

data: {"type": "content", "content": " real-time."}

data: {"type": "done", "finish_reason": "stop"}

data: [DONE]
```

### Event Types

- **start**: Initial acknowledgment with timestamp
- **content**: Text chunks as they're generated
- **done**: Completion signal with finish reason
- **[DONE]**: Final signal indicating stream end

## Client Implementation

### JavaScript/TypeScript Example

```javascript
const response = await fetch('https://gaia-gateway-dev.fly.dev/api/v0.3/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'YOUR_API_KEY'
  },
  body: JSON.stringify({
    message: 'Tell me a story',
    stream: true
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  buffer += decoder.decode(value, { stream: true });
  
  // Process complete SSE events (separated by double newlines)
  while (buffer.includes('\n\n')) {
    const [event, rest] = buffer.split('\n\n', 2);
    buffer = rest;
    
    if (event.startsWith('data: ')) {
      const data = event.slice(6);
      
      if (data === '[DONE]') {
        console.log('Stream complete');
        break;
      }
      
      try {
        const parsed = JSON.parse(data);
        if (parsed.type === 'content') {
          console.log('Received:', parsed.content);
        }
      } catch (e) {
        console.error('Parse error:', e);
      }
    }
  }
}
```

### Python Example

```python
import httpx
import json

async def stream_chat(message: str, api_key: str):
    url = "https://gaia-gateway-dev.fly.dev/api/v0.3/chat"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "message": message,
        "stream": True
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream('POST', url, json=payload, headers=headers) as response:
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                
                # Process complete events
                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)
                    
                    if event.startswith("data: "):
                        data_str = event[6:]
                        
                        if data_str == "[DONE]":
                            print("Stream complete")
                            return
                        
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "content":
                                print(data.get("content"), end="", flush=True)
                        except json.JSONDecodeError:
                            pass
```

### Unity/C# Implementation Notes

For Unity clients (like the AR ChatClient), you'll need:

1. **SSE Client Library**: Unity doesn't have native SSE support. Consider:
   - [Unity-SSE](https://github.com/karthink/Unity-SSE) 
   - Custom implementation using UnityWebRequest
   - Third-party WebSocket libraries that support SSE

2. **Key Implementation Points**:
   - Parse `data:` prefixed lines
   - Handle the `[DONE]` signal to know when complete
   - Process JSON chunks for `type` and `content` fields
   - Maintain buffer for partial events

## Performance Characteristics

- **First token latency**: ~500ms-1s
- **Throughput**: 30-50 tokens/second
- **Connection timeout**: 30 seconds
- **Max response time**: Configurable per request

## Testing

Use the provided test script to verify streaming works:

```bash
# Test streaming endpoint
API_KEY="your-key" python3 scripts/test-sse-streaming.py

# The script tests both v1 and v0.3 endpoints
# and verifies SSE event boundaries are preserved
```

## Common Issues

### 1. Client Disconnects Early
**Problem**: Client closes connection before receiving all data  
**Solution**: Wait for `[DONE]` signal before closing connection

### 2. Partial Events
**Problem**: Events split across network packets  
**Solution**: Buffer until you have complete events (ending with `\n\n`)

### 3. No Streaming Response
**Problem**: Getting full response instead of stream  
**Solution**: Ensure `"stream": true` is in request body

### 4. CORS Issues
**Problem**: Browser blocks SSE connection  
**Solution**: Gateway includes CORS headers, ensure client accepts them

## Architecture Notes

- Streaming is handled by `/chat/unified` endpoint internally
- Gateway detects `stream: true` and forwards appropriately
- All chat variants (v0.3, v1) support streaming
- Same intelligent routing applies (fast for simple, tools for complex)

## Related Documentation

- [SSE Streaming Gotchas](../../troubleshooting/sse-streaming-gotchas.md) - Implementation pitfalls
- [Chat Endpoint Variants](../chat/chat-endpoint-variants-explained.md) - All chat endpoints explained
- [API Reference](../reference/GAIA_API_REFERENCE.md) - Complete API documentation