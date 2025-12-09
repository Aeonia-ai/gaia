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

### Unity C# Example using Best.HTTP/3

For GAIA's streaming API, you need to handle SSE data directly from the POST response using the `OnStreamingData` callback. 

**Important Notes**:
1. The EventSource class in Best.HTTP is designed for GET requests that establish a persistent SSE connection. GAIA's API uses a POST request that returns SSE data, so we must use the manual streaming approach.
2. We're not "sending a streaming message" - we're **sending a regular message and requesting a streaming response** by setting `stream: true` in the request body.
3. The API uses a single `SendMessage()` method with a `stream` parameter to control the response format.

```csharp
using BestHTTP;
using System;
using System.Text;
using UnityEngine;

public class GaiaChatSSEClient : MonoBehaviour
{
    private HTTPRequest streamRequest;
    private StringBuilder messageBuffer = new StringBuilder();
    private string eventBuffer = "";
    
    public void StartStreaming(string message, string apiKey)
    {
        var uri = new Uri("https://gaia-gateway-dev.fly.dev/api/v0.3/chat");
        
        streamRequest = new HTTPRequest(uri, HTTPMethods.Post);
        streamRequest.SetHeader("X-API-Key", apiKey);
        streamRequest.SetHeader("Content-Type", "application/json");
        streamRequest.SetHeader("Accept", "text/event-stream");
        
        var payload = $"{{\"message\":\"{message}\",\"stream\":true}}";
        streamRequest.RawData = Encoding.UTF8.GetBytes(payload);
        
        // Enable streaming
        streamRequest.OnStreamingData += OnStreamingData;
        streamRequest.DisableCache = true;
        streamRequest.StreamFragmentSize = 1;
        
        streamRequest.Send();
    }
    
    private bool OnStreamingData(HTTPRequest req, HTTPResponse resp, byte[] dataFragment, int dataFragmentLength)
    {
        string chunk = Encoding.UTF8.GetString(dataFragment, 0, dataFragmentLength);
        eventBuffer += chunk;
        
        // Process complete events (ending with \n\n)
        while (eventBuffer.Contains("\n\n"))
        {
            int eventEnd = eventBuffer.IndexOf("\n\n");
            string eventData = eventBuffer.Substring(0, eventEnd);
            eventBuffer = eventBuffer.Substring(eventEnd + 2);
            
            ProcessSSEEvent(eventData);
        }
        
        return true; // Continue streaming
    }
    
    private void ProcessSSEEvent(string eventLine)
    {
        if (!eventLine.StartsWith("data: ")) return;
        
        string data = eventLine.Substring(6);
        
        if (data == "[DONE]")
        {
            Debug.Log($"Stream complete. Full message: {messageBuffer}");
            streamRequest?.Abort();
            return;
        }
        
        try
        {
            var eventData = JsonUtility.FromJson<SSEEventData>(data);
            
            if (eventData.type == "content")
            {
                messageBuffer.Append(eventData.content);
                // Update UI
                UpdateChatUI(eventData.content);
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"Parse error: {e.Message}");
        }
    }
    
    private void UpdateChatUI(string textChunk)
    {
        // Update your Unity UI here
    }
    
    void OnDestroy()
    {
        streamRequest?.Abort();
    }
}

[Serializable]
public class SSEEventData
{
    public string type;
    public string content;
    public string timestamp;
    public string finish_reason;
}
```

### Usage Examples

```csharp
// Basic non-streaming message
chatClient.SendMessage("Hello guardian");

// Request streaming response
chatClient.SendMessage("Tell me a story", stream: true);

// Streaming with chunk callback
chatClient.SendMessage("Explain the forest", 
    stream: true, 
    onChunk: (chunk) => {
        // Update UI as text arrives
        chatTextUI.text += chunk;
    }
);
```

### Complete Working Example

Here's a production-ready implementation that handles all edge cases:

```csharp
using BestHTTP;
using System;
using System.Collections;
using System.Text;
using UnityEngine;

public class ChatClient : MonoBehaviour
{
    private HTTPRequest activeRequest;
    private StringBuilder fullMessage = new StringBuilder();
    private string eventBuffer = "";
    
    [Header("Configuration")]
    [SerializeField] private string apiKey = "YOUR_API_KEY";
    [SerializeField] private string apiUrl = "https://gaia-gateway-dev.fly.dev/api/v0.3/chat";
    
    public delegate void OnMessageChunk(string chunk);
    public delegate void OnMessageComplete(string fullMessage);
    public delegate void OnDirective(string directiveJson);
    public delegate void OnError(string error);
    
    public event OnMessageChunk MessageChunkReceived;
    public event OnMessageComplete MessageComplete;
    public event OnDirective DirectiveReceived;
    public event OnError ErrorOccurred;
    
    public void SendMessage(string message, bool stream = false, Action<string> onChunk = null)
    {
        // Cancel any active request
        activeRequest?.Abort();
        
        // Reset buffers
        fullMessage.Clear();
        eventBuffer = "";
        
        // Create request
        activeRequest = new HTTPRequest(new Uri(apiUrl), HTTPMethods.Post);
        
        // Set headers
        activeRequest.SetHeader("X-API-Key", apiKey);
        activeRequest.SetHeader("Content-Type", "application/json");
        
        if (stream)
        {
            activeRequest.SetHeader("Accept", "text/event-stream");
        }
        
        // Create payload
        var payload = new
        {
            message = message,
            stream = stream  // Request streaming response if true
        };
        
        string jsonPayload = JsonUtility.ToJson(payload);
        activeRequest.RawData = Encoding.UTF8.GetBytes(jsonPayload);
        
        if (stream)
        {
            // Set up streaming response handling
            activeRequest.OnStreamingData += OnStreamingData;
            activeRequest.DisableCache = true;
            activeRequest.StreamFragmentSize = 1; // Get data as soon as available
            
            // Store the chunk callback if provided
            if (onChunk != null)
            {
                MessageChunkReceived += onChunk;
            }
        }
        
        // Set completion callback
        activeRequest.Callback = OnRequestComplete;
        
        // Send request
        activeRequest.Send();
        
        Debug.Log($"Sent message: {message} (stream response: {stream})");
    }
    
    private bool OnStreamingData(HTTPRequest req, HTTPResponse resp, byte[] dataFragment, int dataFragmentLength)
    {
        if (dataFragmentLength == 0) return true;
        
        string chunk = Encoding.UTF8.GetString(dataFragment, 0, dataFragmentLength);
        eventBuffer += chunk;
        
        // Process complete SSE events (separated by \n\n)
        while (eventBuffer.Contains("\n\n"))
        {
            int eventEnd = eventBuffer.IndexOf("\n\n");
            string eventData = eventBuffer.Substring(0, eventEnd);
            eventBuffer = eventBuffer.Substring(eventEnd + 2);
            
            ProcessSSEEvent(eventData);
        }
        
        return true; // Continue streaming
    }
    
    private void ProcessSSEEvent(string eventLine)
    {
        if (string.IsNullOrWhiteSpace(eventLine)) return;
        
        // SSE events start with "data: "
        if (!eventLine.StartsWith("data: ")) return;
        
        string data = eventLine.Substring(6).Trim();
        
        // Check for stream completion
        if (data == "[DONE]")
        {
            string finalMessage = fullMessage.ToString();
            Debug.Log($"Stream complete. Message length: {finalMessage.Length}");
            
            // Extract directives from complete message
            ExtractDirectives(finalMessage);
            
            // Notify completion
            MessageComplete?.Invoke(finalMessage);
            
            return;
        }
        
        // Parse JSON event
        try
        {
            var eventData = JsonUtility.FromJson<SSEEventData>(data);
            
            switch (eventData.type)
            {
                case "start":
                    Debug.Log($"Stream started at: {eventData.timestamp}");
                    break;
                    
                case "content":
                    if (!string.IsNullOrEmpty(eventData.content))
                    {
                        fullMessage.Append(eventData.content);
                        MessageChunkReceived?.Invoke(eventData.content);
                    }
                    break;
                    
                case "done":
                    Debug.Log($"Stream finished: {eventData.finish_reason}");
                    break;
                    
                default:
                    Debug.LogWarning($"Unknown event type: {eventData.type}");
                    break;
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning($"Failed to parse SSE event: {e.Message}\nData: {data}");
        }
    }
    
    private void ExtractDirectives(string message)
    {
        // Pattern to match directives like {"m":"spawn_character","p":{"type":"fairy"}}
        var pattern = @"\{""m"":""([^""]+)"",""p"":\{[^}]+\}\}";
        var matches = System.Text.RegularExpressions.Regex.Matches(message, pattern);
        
        foreach (System.Text.RegularExpressions.Match match in matches)
        {
            Debug.Log($"Found directive: {match.Value}");
            DirectiveReceived?.Invoke(match.Value);
        }
    }
    
    private void OnRequestComplete(HTTPRequest req, HTTPResponse resp)
    {
        if (resp == null)
        {
            string error = "No response received";
            Debug.LogError(error);
            ErrorOccurred?.Invoke(error);
            return;
        }
        
        if (!resp.IsSuccess)
        {
            string error = $"Request failed: {resp.StatusCode} - {resp.Message}";
            Debug.LogError(error);
            ErrorOccurred?.Invoke(error);
            return;
        }
        
        // For non-streaming responses
        if (!req.HasHeader("Accept") || !req.GetFirstHeaderValue("Accept").Contains("event-stream"))
        {
            try
            {
                string responseText = resp.DataAsText;
                var responseData = JsonUtility.FromJson<ChatResponse>(responseText);
                
                fullMessage.Clear();
                fullMessage.Append(responseData.response);
                
                ExtractDirectives(responseData.response);
                MessageComplete?.Invoke(responseData.response);
            }
            catch (Exception e)
            {
                string error = $"Failed to parse response: {e.Message}";
                Debug.LogError(error);
                ErrorOccurred?.Invoke(error);
            }
        }
    }
    
    void OnDestroy()
    {
        activeRequest?.Abort();
    }
    
    [Serializable]
    private class ChatResponse
    {
        public string response;
        public string conversation_id;
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