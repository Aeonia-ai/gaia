# Chat Request/Response Flow Documentation

This document provides a comprehensive overview of how chat requests flow through the GAIA platform from the web UI to the chat service and back.

## Architecture Overview

```
Web UI → Gateway Service → Chat Service → LLM Providers
   ↓         ↓              ↓              ↓
HTML ←   JSON/SSE ←    JSON/SSE ←    API Responses
```

The chat system uses a **layered architecture** where each component has specific responsibilities:
- **Web UI**: Server-side rendered HTML with HTMX and SSE for real-time updates
- **Gateway Service**: Authentication and request routing proxy
- **Chat Service**: LLM orchestration, conversation management, and tool integration

## 1. Web UI to Gateway Service

### Web UI Chat Interface

**Location**: `/app/services/web/routes/chat.py`

The web UI uses **FastHTML + HTMX** for server-side rendering with dynamic updates.

### Primary Endpoints

#### **Form Submission: `/api/chat/send`**
```http
POST /api/chat/send
Content-Type: application/x-www-form-urlencoded

message=Hello%20world&conversation_id=abc123
```

#### **Streaming: `/api/chat/stream`**
```http
GET /api/chat/stream?message=encoded_message&conversation_id=abc123
```

### Web UI Response Format

The web UI expects **HTML fragments** that HTMX can swap into the page:

```html
<!-- User message bubble -->
<div class="flex justify-end mb-4">
    <div class="bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-2xl px-4 py-3">
        <div class="whitespace-pre-wrap">Hello, how are you?</div>
        <div class="text-xs opacity-70 mt-1">2:30 PM</div>
    </div>
</div>

<!-- Loading indicator with SSE JavaScript -->
<div id="loading-abc123" class="flex justify-start mb-4">
    <div class="bg-slate-700 text-white rounded-2xl px-4 py-3">
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
        <div class="text-xs opacity-70 mt-2">Gaia is thinking...</div>
    </div>
</div>

<script>
    // SSE connection setup
    const eventSource = new EventSource('/api/chat/stream?message=...');
    
    eventSource.onmessage = function(event) {
        if (event.data === '[DONE]') {
            eventSource.close();
            return;
        }
        
        const data = JSON.parse(event.data);
        if (data.type === 'content') {
            responseContent += data.content;
            document.getElementById('response-content-{message_id}').textContent = responseContent;
        }
    };
</script>
```

### Gateway API Calls

**Location**: `/app/services/web/utils/gateway_client.py`

The web service calls the Gateway Service:

#### **Non-Streaming Request:**
```http
POST https://gateway-url/api/v1/chat
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "message": "Hello, how are you?",
    "model": "claude-sonnet-4-5",
    "stream": false
}
```

#### **Streaming Request:**
```http
POST https://gateway-url/api/v1/chat
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "message": "Hello, how are you?",
    "model": "claude-sonnet-4-5", 
    "stream": true
}
```

### Authentication

- **Session-based**: JWT token stored in `request.session.get("jwt_token")`
- **Header format**: `Authorization: Bearer <jwt_token>`
- **Fallback**: `X-API-Key: <api_key>` for dev/testing

## 2. Gateway Service to Chat Service

### Gateway Service Implementation

**Location**: `/app/gateway/main.py`

The gateway service acts as an **authenticated proxy** that validates users and forwards requests.

### Gateway Chat Endpoints

#### Primary Endpoints:
- **`POST /api/v1/chat`** (lines 1543-1566) - Most commonly used, legacy v1 endpoint
- **`POST /api/v0.2/chat`** (lines 355-413) - Unified v0.2 chat endpoint  
- **`POST /api/v1/chat/completions`** (lines 1568-1590) - OpenAI-compatible endpoint

### Gateway → Chat Service Routing

**Service URL Configuration:**
```python
SERVICE_URLS = {
    "chat": settings.CHAT_SERVICE_URL  # "http://chat-service:8000" or "https://gaia-chat-dev.fly.dev"
}
```

**Endpoint Mapping:**
- `POST /api/v1/chat` → `POST http://chat-service:8000/chat/unified`
- `POST /api/v0.2/chat` → `POST http://chat-service:8000/api/v0.2`

### Request Processing

**Key Function**: `forward_request_to_service()` (lines 126-264)

1. **Authentication Validation**: Uses `get_current_auth_legacy()` or `get_current_auth_unified()`
2. **Auth Injection**: Adds `_auth` object to request body
3. **Header Cleaning**: Removes content-length to avoid conflicts
4. **Streaming Detection**: Detects `stream=true` or `text/event-stream` content-type

### Request Format (Gateway → Chat Service)

```json
{
  "message": "User's chat message",
  "stream": false,
  "provider": "claude",
  "model": "claude-3-haiku-20240307",
  "activity": "generic",
  "persona_id": "default",
  "priority": "balanced",
  "_auth": {
    "user_id": "user123",
    "key": "api_key_hash",
    "type": "api_key"
  }
}
```

**Key Addition**: Gateway adds `_auth` object containing validated authentication info.

## 3. Chat Service Processing

### Chat Service Implementation

**Location**: `/app/services/chat/main.py`

The chat service handles LLM orchestration, conversation management, and tool integration.

### Chat Service Endpoints

#### Main Router (`/chat` prefix):
- **`POST /chat/unified`** (lines 142-236) - Intelligent routing endpoint
- **`POST /chat/`** (lines 41-140, 543-654) - Legacy chat completion
- **`POST /chat/multi-provider`** (lines 294-540) - Multi-provider with streaming
- **`GET /chat/status`** (lines 254-292) - Chat history status
- **`DELETE /chat/history`** (lines 685-721) - Clear chat history

#### v0.2 Router (`/api/v0.2` prefix):
- **`POST /api/v0.2`** (lines 35-319) - Unified v0.2 chat endpoint
- **`GET /api/v0.2/status`** (lines 321-362) - v0.2 status
- **`DELETE /api/v0.2/history`** (lines 364-394) - v0.2 clear history

### Chat Service Processing Flow

1. **Request Validation**: Extracts and validates request parameters
2. **Auth Extraction**: Uses `_auth` from request body for user identification
3. **Tool Integration**: Calls `ToolProvider.get_tools_for_activity()` for available tools
4. **Provider Selection**: Uses intelligent model selection based on message context
5. **LLM Orchestration**: Routes to appropriate LLM provider (Claude, OpenAI, etc.)
6. **Response Processing**: Formats response according to API version

### Key Integration Points

#### Chat History Management:
- Maintains in-memory chat histories per user
- Uses `auth_key` from `_auth` for user isolation
- Supports clearing and reloading system prompts

#### Tool Integration:
- Formats tools for LLM provider APIs
- Handles tool calls and responses
- Supports KB tools, MCP-agent integration

#### Provider Selection:
- Uses `chat_service.chat_completion()` for provider routing
- Supports fallback between providers
- Tracks usage and performance metrics

## 4. Response Formats

### Non-Streaming Response (Chat Service → Gateway)

```json
{
  "response": "AI assistant's response text",
  "provider": "claude", 
  "model": "claude-3-haiku-20240307",
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 123,
    "total_tokens": 168
  },
  "response_time_ms": 1247,
  "reasoning": "Selected haiku for speed",
  "fallback_used": false
}
```

### Streaming Response (Chat Service → Gateway)

**Content-Type:** `text/event-stream`

**Format:** Server-Sent Events (SSE) with OpenAI-compatible chunks

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"claude-3-haiku-20240307","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"claude-3-haiku-20240307","choices":[{"index":0,"delta":{"content":" there!"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"claude-3-haiku-20240307","choices":[{"index":0,"delta":{"content":" How can I help you today?"},"finish_reason":"stop"}]}

data: [DONE]
```

## 5. Gateway Response Processing

### Non-Streaming Responses
- **Direct Forwarding**: Gateway forwards JSON response directly to client
- **No Transformation**: Preserves all fields (response, provider, model, usage, etc.)
- **Header Preservation**: Maintains original content-type and headers

### Streaming Responses
- **StreamingResponse Creation**: Gateway creates proper SSE response
- **SSE Headers**: Sets required Server-Sent Events headers:
  ```python
  headers={
      "Cache-Control": "no-cache",
      "Connection": "keep-alive", 
      "X-Accel-Buffering": "no"
  }
  ```
- **Direct Forwarding**: Streams chunks from chat service to client without modification

## 6. Error Handling

### Gateway Level Errors
- **HTTP Timeouts**: Based on `GATEWAY_REQUEST_TIMEOUT` setting
- **Service Unavailable (503)**: When chat service is unreachable
- **Authentication Errors (401)**: When auth validation fails
- **Malformed Requests (400)**: Invalid request format or missing parameters

### Chat Service Level Errors
- **Invalid Parameters (400)**: Missing required fields or invalid values
- **Processing Errors (500)**: LLM provider errors or internal processing failures
- **Model Selection Failures**: Automatic fallback to alternative providers
- **Tool Execution Errors**: Graceful handling of tool call failures

### Web UI Error Display

```html
<div class="flex justify-start mb-4">
    <div class="bg-red-900/50 border border-red-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
        <div class="flex items-center justify-between">
            <div class="flex items-center">
                <span class="mr-2">❌</span>
                <span>Connection error. Please try again.</span>
            </div>
            <button onclick="retry_function()" class="ml-3 px-3 py-1 bg-white bg-opacity-20 hover:bg-opacity-30 rounded text-sm font-medium">
                Retry
            </button>
        </div>
    </div>
</div>
```

## 7. Performance Characteristics

### Response Times
- **KB Operations**: ~100-300ms (HTTP + search/file I/O)
- **MCP Agent**: ~1-3s (hot-loaded agents)
- **Simple Chat**: ~1-2s (direct LLM call)
- **Complex Workflows**: ~2-5s (multi-tool orchestration)

### Optimization Features
- **Redis Caching**: 97% performance improvement for repeated queries
- **Hot-Loading**: Pre-initialized MCP agents reduce response time
- **Connection Pooling**: Persistent connections to LLM providers
- **Streaming Responses**: Real-time user experience

## 8. Security Considerations

### Authentication Flow
1. **Client Authentication**: JWT tokens or API keys validated at gateway
2. **Inter-Service Communication**: `_auth` object passed securely between services
3. **User Isolation**: Chat histories and tool access scoped by user ID
4. **RBAC Integration**: Role-based access control for advanced features

### Data Privacy
- **Conversation Isolation**: Each user's chat history is completely isolated
- **Memory Management**: In-memory storage with configurable TTL
- **Tool Access Control**: User permissions enforced for KB and system tools

## 9. Monitoring and Debugging

### Key Logs to Monitor
- **Gateway Access Logs**: Request routing and authentication
- **Chat Service Logs**: Provider selection and response times
- **Tool Execution Logs**: KB searches and MCP agent calls
- **Error Logs**: Failed requests and fallback usage

### Debugging Commands
```bash
# Test complete flow
./scripts/test.sh --local chat "test message"

# Check service health
./scripts/test.sh --local health

# Monitor specific service logs
docker compose logs -f gateway
docker compose logs -f chat-service
docker compose logs -f web-service
```

## 10. Future Enhancements

### Planned Improvements
- **WebSocket Support**: Real-time bidirectional communication
- **Enhanced Conversation Management**: Delete, rename, search functionality
- **Advanced Memory Systems**: PostgreSQL-based persistent chat memory
- **Multi-Agent Orchestration**: Coordinated multi-agent workflows

### Performance Optimizations
- **Response Caching**: Intelligent caching of common responses
- **Load Balancing**: Multiple chat service instances
- **Provider Optimization**: Dynamic provider selection based on performance
- **Batch Processing**: Efficient handling of multiple concurrent requests

---

This documentation provides a complete overview of the chat request/response flow in the GAIA platform. For specific implementation details, refer to the source code files mentioned throughout this document.