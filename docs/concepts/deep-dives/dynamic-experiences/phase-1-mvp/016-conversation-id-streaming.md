# V0.3 Conversation ID Streaming API

**API Version**: V0.3
**Protocol**: Server-Sent Events (SSE)
**Status**: ✅ Production Ready
**Client Compatibility**: Unity, JavaScript, Python, Mobile

## Quick Start

### Basic Request

```bash
curl -X POST http://localhost:8666/api/v0.3/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Hello, world!",
    "model": "claude-sonnet-4-5",
    "stream": true
  }' --no-buffer
```

### Response (SSE Stream)

```
data: {"type": "metadata", "conversation_id": "550e8400-e29b-41d4-a716-446655440000", "model": "unified-chat", "timestamp": 1234567890}

data: {"type": "content", "delta": {"content": "Hello"}}

data: {"type": "content", "delta": {"content": "! How"}}

data: {"type": "content", "delta": {"content": " can I help you today?"}}

data: [DONE]
```

## API Reference

### Endpoint

```
POST /api/v0.3/chat
```

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | Authentication API key |
| `Content-Type` | Yes | Must be `application/json` |
| `Accept` | Recommended | Set to `text/event-stream` for proper SSE handling |

### Request Body

```json
{
  "message": "string",
  "model": "string",
  "stream": true,
  "conversation_id": "string|null"
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | User message content |
| `model` | string | Yes | LLM model identifier (e.g., "claude-sonnet-4-5") |
| `stream` | boolean | Yes | Must be `true` for streaming responses |
| `conversation_id` | string or null | No | Conversation UUID, "new", or omit for new conversation |

#### Conversation ID Values

| Value | Behavior |
|-------|----------|
| `null` or omitted | Creates new conversation |
| `"new"` | Explicitly creates new conversation |
| Valid UUID | Resumes existing conversation |
| Invalid UUID | Creates new conversation (graceful fallback) |

### Response Format

The API returns a Server-Sent Events stream with the following event types:

#### Metadata Event (Always First)

```json
{
  "type": "metadata",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "model": "unified-chat",
  "timestamp": 1234567890
}
```

**Fields**:
- `type`: Always "metadata"
- `conversation_id`: UUID of the conversation (new or existing)
- `model`: Model used for this response
- `timestamp`: Unix timestamp of response start

#### Content Events

```json
{
  "type": "content",
  "delta": {
    "content": "text chunk"
  }
}
```

**Fields**:
- `type`: Always "content"
- `delta.content`: Incremental text content from the LLM

#### Stream Termination

```
data: [DONE]
```

Indicates the end of the streaming response.

### HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Successful streaming response |
| `400` | Invalid request format or missing required fields |
| `401` | Authentication failed |
| `403` | Access denied (e.g., conversation belongs to different user) |
| `429` | Rate limit exceeded |
| `500` | Internal server error |

## Client Implementation Patterns

### Unity C# Client

```csharp
using System;
using System.Net.Http;
using System.Threading.Tasks;
using UnityEngine;
using Newtonsoft.Json;

public class GaiaStreamingClient : MonoBehaviour
{
    private HttpClient httpClient;
    private string baseUrl = "http://localhost:8666";
    private string apiKey = "your-api-key";

    [Serializable]
    public class StreamEvent
    {
        public string type;
        public string conversation_id;
        public string model;
        public long timestamp;
        public Delta delta;
    }

    [Serializable]
    public class Delta
    {
        public string content;
    }

    public async Task<string> SendStreamingMessage(string message, string conversationId = null)
    {
        var request = new
        {
            message = message,
            model = "claude-sonnet-4-5",
            stream = true,
            conversation_id = conversationId
        };

        var json = JsonConvert.SerializeObject(request);
        var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");

        httpClient.DefaultRequestHeaders.Clear();
        httpClient.DefaultRequestHeaders.Add("X-API-Key", apiKey);

        using var response = await httpClient.PostAsync($"{baseUrl}/api/v0.3/chat", content);
        response.EnsureSuccessStatusCode();

        var extractedConversationId = "";
        var fullResponse = "";

        using var stream = await response.Content.ReadAsStreamAsync();
        using var reader = new System.IO.StreamReader(stream);

        string line;
        while ((line = await reader.ReadLineAsync()) != null)
        {
            if (line.StartsWith("data: "))
            {
                var eventData = line.Substring(6);

                if (eventData == "[DONE]")
                    break;

                try
                {
                    var streamEvent = JsonConvert.DeserializeObject<StreamEvent>(eventData);

                    // Extract conversation_id from first metadata event
                    if (streamEvent.type == "metadata" && !string.IsNullOrEmpty(streamEvent.conversation_id))
                    {
                        extractedConversationId = streamEvent.conversation_id;
                        Debug.Log($"Conversation ID: {extractedConversationId}");
                    }

                    // Accumulate content
                    if (streamEvent.type == "content" && streamEvent.delta?.content != null)
                    {
                        fullResponse += streamEvent.delta.content;
                    }
                }
                catch (JsonException ex)
                {
                    Debug.LogWarning($"Failed to parse stream event: {ex.Message}");
                }
            }
        }

        Debug.Log($"Full response: {fullResponse}");
        return extractedConversationId;
    }
}
```

### JavaScript Client

```javascript
class GaiaStreamingClient {
    constructor(baseUrl = 'http://localhost:8666', apiKey = 'your-api-key') {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
    }

    async sendStreamingMessage(message, conversationId = null) {
        const response = await fetch(`${this.baseUrl}/api/v0.3/chat`, {
            method: 'POST',
            headers: {
                'X-API-Key': this.apiKey,
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify({
                message: message,
                model: 'claude-sonnet-4-5',
                stream: true,
                conversation_id: conversationId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let extractedConversationId = null;
        let fullResponse = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const eventData = line.substring(6);

                        if (eventData === '[DONE]') {
                            return { conversationId: extractedConversationId, response: fullResponse };
                        }

                        try {
                            const event = JSON.parse(eventData);

                            // Extract conversation_id from metadata event
                            if (event.type === 'metadata' && event.conversation_id) {
                                extractedConversationId = event.conversation_id;
                                console.log(`Conversation ID: ${extractedConversationId}`);
                            }

                            // Accumulate content
                            if (event.type === 'content' && event.delta?.content) {
                                fullResponse += event.delta.content;
                            }
                        } catch (e) {
                            console.warn('Failed to parse event:', e);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }

        return { conversationId: extractedConversationId, response: fullResponse };
    }
}

// Usage example
const client = new GaiaStreamingClient();

client.sendStreamingMessage('Hello, how are you?')
    .then(result => {
        console.log('Conversation ID:', result.conversationId);
        console.log('Response:', result.response);
    })
    .catch(error => {
        console.error('Error:', error);
    });
```

### Python Client

```python
import aiohttp
import asyncio
import json
from typing import Optional, AsyncGenerator, Tuple

class GaiaStreamingClient:
    def __init__(self, base_url: str = "http://localhost:8666", api_key: str = "your-api-key"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }

    async def send_streaming_message(
        self,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Tuple[Optional[str], str]:
        """
        Send a streaming message and return (conversation_id, full_response)
        """
        payload = {
            "message": message,
            "model": "claude-sonnet-4-5",
            "stream": True
        }

        if conversation_id:
            payload["conversation_id"] = conversation_id

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v0.3/chat",
                json=payload,
                headers=self.headers
            ) as response:
                response.raise_for_status()

                extracted_conversation_id = None
                full_response = ""

                async for chunk in response.content.iter_chunked(1024):
                    chunk_text = chunk.decode('utf-8')

                    for line in chunk_text.split('\n'):
                        if line.startswith('data: '):
                            event_data = line[6:]

                            if event_data == '[DONE]':
                                return extracted_conversation_id, full_response

                            try:
                                event = json.loads(event_data)

                                # Extract conversation_id from metadata
                                if event.get('type') == 'metadata' and event.get('conversation_id'):
                                    extracted_conversation_id = event['conversation_id']
                                    print(f"Conversation ID: {extracted_conversation_id}")

                                # Accumulate content
                                if event.get('type') == 'content' and event.get('delta', {}).get('content'):
                                    full_response += event['delta']['content']

                            except json.JSONDecodeError:
                                continue

                return extracted_conversation_id, full_response

    async def stream_with_callback(
        self,
        message: str,
        on_metadata: callable = None,
        on_content: callable = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Stream with real-time callbacks for metadata and content events
        """
        payload = {
            "message": message,
            "model": "claude-sonnet-4-5",
            "stream": True
        }

        if conversation_id:
            payload["conversation_id"] = conversation_id

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v0.3/chat",
                json=payload,
                headers=self.headers
            ) as response:
                response.raise_for_status()

                conversation_id_extracted = None

                async for chunk in response.content.iter_chunked(1024):
                    chunk_text = chunk.decode('utf-8')

                    for line in chunk_text.split('\n'):
                        if line.startswith('data: '):
                            event_data = line[6:]

                            if event_data == '[DONE]':
                                return conversation_id_extracted

                            try:
                                event = json.loads(event_data)

                                if event.get('type') == 'metadata':
                                    conversation_id_extracted = event.get('conversation_id')
                                    if on_metadata:
                                        await on_metadata(event)

                                elif event.get('type') == 'content':
                                    if on_content:
                                        await on_content(event.get('delta', {}).get('content', ''))

                            except json.JSONDecodeError:
                                continue

                return conversation_id_extracted

# Usage examples
async def main():
    client = GaiaStreamingClient()

    # Basic usage
    conversation_id, response = await client.send_streaming_message("Hello, world!")
    print(f"Conversation: {conversation_id}")
    print(f"Response: {response}")

    # Continue conversation
    conversation_id2, response2 = await client.send_streaming_message(
        "What did I just say?",
        conversation_id=conversation_id
    )
    print(f"Continued conversation: {conversation_id2}")
    print(f"Response: {response2}")

    # Real-time streaming with callbacks
    async def on_metadata(metadata):
        print(f"📋 Metadata: {metadata}")

    async def on_content(content):
        print(content, end='', flush=True)

    print("\n🔄 Real-time streaming:")
    await client.stream_with_callback(
        "Tell me a short story",
        on_metadata=on_metadata,
        on_content=on_content
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## Performance Characteristics

| Metric | Typical Value | Notes |
|--------|---------------|-------|
| **First Event Latency** | 30-80ms | Time to first metadata event |
| **Conversation ID Availability** | Event 0 | Always in first SSE event |
| **Metadata Event Size** | ~120 bytes | Minimal overhead |
| **Memory Overhead** | <1KB per request | Temporary buffers |
| **Database Impact** | +20% INSERTs | New conversation creation |

## Error Handling

### Client-Side Error Recovery

```python
async def robust_conversation_extraction(client, message, conversation_id=None, max_retries=3):
    """Example of robust conversation_id extraction with retries"""

    for attempt in range(max_retries):
        try:
            extracted_id, response = await client.send_streaming_message(message, conversation_id)

            if extracted_id:
                return extracted_id, response
            else:
                print(f"Warning: No conversation_id extracted on attempt {attempt + 1}")

        except aiohttp.ClientError as e:
            print(f"Network error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

    # Fallback: generate client-side temporary ID
    import uuid
    temp_id = f"client-{uuid.uuid4().hex[:8]}"
    print(f"Using fallback conversation ID: {temp_id}")
    return temp_id, ""
```

### Common Error Scenarios

| Error | HTTP Code | Response | Client Action |
|-------|-----------|----------|---------------|
| Invalid API key | 401 | `{"error": "Invalid API key"}` | Check authentication |
| Malformed request | 400 | `{"error": "Invalid JSON"}` | Validate request format |
| Rate limit exceeded | 429 | `{"error": "Rate limit exceeded"}` | Implement backoff |
| Server error | 500 | `{"error": "Internal server error"}` | Retry with exponential backoff |
| Stream timeout | - | Connection timeout | Reconnect and retry |

## Migration Guide

### From V1 to V0.3

**V1 API** (Non-streaming):
```json
POST /api/v1/chat
{
  "message": "Hello",
  "conversation_id": "uuid"
}

Response:
{
  "choices": [{"message": {"content": "Hi there!"}}],
  "_metadata": {"conversation_id": "uuid"}
}
```

**V0.3 API** (Streaming):
```json
POST /api/v0.3/chat
{
  "message": "Hello",
  "stream": true,
  "conversation_id": "uuid"
}

Response:
data: {"type": "metadata", "conversation_id": "uuid", ...}
data: {"type": "content", "delta": {"content": "Hi"}}
data: {"type": "content", "delta": {"content": " there!"}}
data: [DONE]
```

### Key Migration Points

1. **Response Format**: JSON object → SSE stream
2. **Conversation ID Location**: `_metadata.conversation_id` → First metadata event
3. **Content Structure**: `choices[0].message.content` → Accumulated `delta.content`
4. **Request Headers**: Add `Accept: text/event-stream`
5. **Client Parsing**: JSON response → SSE event parsing

## Related Documentation

- [Streaming API Guide](streaming-api-guide.md) - General streaming concepts
- [SSE Chunking Implementation](sse-chunking-implementation.md) - Technical details
- [Authentication Guide](../authentication/README.md) - API key setup
- [V0.3 Streaming Architecture](../../technical-design/v03-streaming-architecture.md) - Technical design

---

**API Version**: 0.3
**Last Updated**: September 2025
**Maintainer**: GAIA Platform Team