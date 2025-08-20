# GAIA v0.3 API Documentation

**The Clean, Simple AI Chat API**

## Overview

The GAIA v0.3 API provides a clean, simplified interface for AI chat interactions. It hides all internal complexity (provider selection, model details, routing decisions) and presents a consistent, easy-to-use format for both developers and end-users.

### Design Principles

- **Simple request/response format** - Minimal required fields
- **No provider/model selection exposed** - Server makes optimal choices automatically  
- **Consistent streaming and non-streaming formats** - Same structure for both modes
- **Server-side intelligence hidden** - Internal routing and optimization transparent to clients
- **Clean response format** - No technical metadata in responses

## Authentication

The v0.3 API provides complete authentication endpoints for user management. You can either:

1. **Use API keys** for service-to-service communication:
```http
X-API-Key: your-api-key-here
Content-Type: application/json
```

2. **Use JWT tokens** obtained from login:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

## Base URL

```
https://your-gaia-instance.com/api/v0.3
```

## Authentication Endpoints

### POST `/api/v0.3/auth/login`

Authenticate a user and receive access tokens.

#### Request Format
```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

#### Response Format
```json
{
  "session": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600,
    "token_type": "bearer"
  },
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "email_confirmed_at": "2025-08-20T01:30:00Z"
  }
}
```

### POST `/api/v0.3/auth/register`

Create a new user account.

#### Request Format
```json
{
  "email": "newuser@example.com",
  "password": "secure-password"
}
```

#### Response Format
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "email": "newuser@example.com",
    "email_confirmed_at": null,
    "created_at": "2025-08-20T01:30:00Z"
  },
  "message": "User created successfully. Please check your email for verification."
}
```

### POST `/api/v0.3/auth/validate`

Validate an access token.

#### Request Format
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response Format
```json
{
  "valid": true,
  "auth_type": "jwt",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": null
}
```

### POST `/api/v0.3/auth/refresh`

Refresh an expired access token using a refresh token.

#### Request Format
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response Format
```json
{
  "session": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600,
    "token_type": "bearer"
  }
}
```

### POST `/api/v0.3/auth/logout`

Invalidate the current session.

#### Request Format
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response Format
```json
{
  "success": true,
  "message": "Successfully logged out"
}
```

## Chat Endpoint

### POST `/api/v0.3/chat`

Send a message and get an AI response with automatic conversation management.

#### Request Format

```json
{
  "message": "Your question or message here",
  "conversation_id": "optional-conversation-id", 
  "stream": false
}
```

**Required Fields:**
- `message` (string): The message to send to the AI

**Optional Fields:**
- `conversation_id` (string): ID of existing conversation for context. If omitted, a new conversation is created.
- `stream` (boolean): Enable Server-Sent Events streaming. Defaults to `false`.

#### Response Format (Non-Streaming)

```json
{
  "response": "AI response here",
  "conversation_id": "conv-abc123def456"
}
```

**Response Fields:**
- `response` (string): The AI's response to your message
- `conversation_id` (string): ID of the conversation for future messages

#### Response Format (Streaming)

When `stream: true`, responses are delivered as Server-Sent Events:

```
data: {"type": "content", "content": "Hello"}
data: {"type": "content", "content": " there!"}
data: {"type": "content", "content": " How"}
data: {"type": "content", "content": " can"}
data: {"type": "content", "content": " I help?"}
data: {"type": "done", "conversation_id": "conv-abc123def456"}
```

**Event Types:**
- `content`: Contains partial response content
- `done`: Indicates end of response, includes conversation_id

## Examples

### Basic Chat Message

```bash
curl -X POST https://your-gaia-instance.com/api/v0.3/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the capital of France?"
  }'
```

**Response:**
```json
{
  "response": "The capital of France is Paris.",
  "conversation_id": "conv-abc123def456"
}
```

### Continuing a Conversation

```bash
curl -X POST https://your-gaia-instance.com/api/v0.3/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is its population?",
    "conversation_id": "conv-abc123def456"
  }'
```

**Response:**
```json
{
  "response": "Paris has a metropolitan area population of approximately 12.2 million people, while the city proper has about 2.1 million residents.",
  "conversation_id": "conv-abc123def456"
}
```

### Streaming Response

```bash
curl -X POST https://your-gaia-instance.com/api/v0.3/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about machine learning",
    "stream": true
  }'
```

**Response (Server-Sent Events):**
```
data: {"type": "content", "content": "Machine learning is a subset"}
data: {"type": "content", "content": " of artificial intelligence that"}
data: {"type": "content", "content": " enables computers to learn"}
data: {"type": "content", "content": " and improve from experience..."}
data: {"type": "done", "conversation_id": "conv-xyz789abc123"}
```

### JavaScript Example

```javascript
async function sendMessage(message, conversationId = null) {
  const response = await fetch('https://your-gaia-instance.com/api/v0.3/chat', {
    method: 'POST',
    headers: {
      'X-API-Key': 'your-api-key',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: message,
      conversation_id: conversationId,
      stream: false
    })
  });
  
  const data = await response.json();
  return data;
}

// Usage
const result = await sendMessage("Hello, how are you?");
console.log('AI Response:', result.response);
console.log('Conversation ID:', result.conversation_id);

// Continue conversation
const followUp = await sendMessage("Tell me a joke", result.conversation_id);
console.log('Follow-up Response:', followUp.response);
```

### Python Example

```python
import requests
import json

def send_message(message, conversation_id=None, stream=False):
    url = "https://your-gaia-instance.com/api/v0.3/chat"
    headers = {
        "X-API-Key": "your-api-key",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": message,
        "stream": stream
    }
    
    if conversation_id:
        payload["conversation_id"] = conversation_id
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

# Usage
result = send_message("What is quantum computing?")
print("AI Response:", result["response"])
print("Conversation ID:", result["conversation_id"])

# Continue conversation
follow_up = send_message("How does it work?", result["conversation_id"])
print("Follow-up Response:", follow_up["response"])
```

## Error Handling

### Error Response Format

```json
{
  "error": "Error message here"
}
```

### Common Error Codes

**400 Bad Request**
```json
{
  "error": "Missing required field: message"
}
```

**401 Unauthorized** 
```json
{
  "error": "Invalid API key"
}
```

**429 Too Many Requests**
```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```

**500 Internal Server Error**
```json
{
  "error": "Internal server error. Please try again."
}
```

## Rate Limits

- **Standard**: 60 requests per minute per API key
- **Burst**: Up to 10 requests per second for short periods
- **Streaming**: Each streaming connection counts as 1 request

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995200
```

## Best Practices

### 1. Conversation Management
- Always include `conversation_id` for follow-up messages
- Store conversation IDs client-side for user sessions
- Create new conversations for distinct topics

### 2. Error Handling
```javascript
try {
  const result = await sendMessage("Hello");
  console.log(result.response);
} catch (error) {
  if (error.status === 401) {
    console.error("Invalid API key");
  } else if (error.status === 429) {
    console.error("Rate limit exceeded, please wait");
  } else {
    console.error("Unexpected error:", error.message);
  }
}
```

### 3. Streaming Implementation
```javascript
async function streamMessage(message) {
  const response = await fetch('/api/v0.3/chat', {
    method: 'POST',
    headers: {
      'X-API-Key': 'your-api-key',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: message,
      stream: true
    })
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  let conversationId = null;
  let fullResponse = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const lines = decoder.decode(value).split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        if (data.type === 'content') {
          fullResponse += data.content;
          console.log(data.content); // Display chunk
        } else if (data.type === 'done') {
          conversationId = data.conversation_id;
        }
      }
    }
  }
  
  return { response: fullResponse, conversation_id: conversationId };
}
```

## Comparison with v1 API

| Feature | v1 API (OpenAI Compatible) | v0.3 API (Clean) |
|---------|----------------------------|------------------|
| **Purpose** | OpenAI compatibility | Clean, simple interface |
| **Request Format** | Complex OpenAI format | Simple message format |
| **Response Metadata** | Detailed usage, timing | Clean response only |
| **Provider Details** | Exposed in metadata | Hidden from client |
| **Conversation Management** | Manual conversation_id | Automatic management |
| **Streaming Format** | OpenAI SSE format | Simple content chunks |

### When to Use v0.3

- ✅ **New applications** - Start with the clean format
- ✅ **Simple chat interfaces** - Minimal complexity needed
- ✅ **Mobile applications** - Reduced payload size
- ✅ **Prototyping** - Quick integration and testing
- ✅ **Client applications** - Hide AI complexity from users

### When to Use v1

- ✅ **OpenAI migration** - Drop-in replacement needs
- ✅ **Advanced integration** - Need detailed metadata
- ✅ **Analytics/monitoring** - Require usage statistics
- ✅ **Legacy compatibility** - Existing OpenAI-format code

## Advanced Features

### Conversation Context

The v0.3 API automatically maintains conversation context without exposing internal complexity:

```bash
# First message
curl -X POST /api/v0.3/chat -d '{"message": "My name is Alice"}'
# Response: {"response": "Hello Alice! Nice to meet you.", "conversation_id": "conv-123"}

# Context is maintained automatically
curl -X POST /api/v0.3/chat -d '{
  "message": "What did I just tell you?",
  "conversation_id": "conv-123"
}'
# Response: {"response": "You told me your name is Alice.", "conversation_id": "conv-123"}
```

### Intelligent Routing

The v0.3 API uses internal intelligence to:
- **Route simple queries** directly for sub-second responses
- **Use specialized tools** for complex analysis automatically
- **Select optimal models** based on query complexity
- **Manage resources** for consistent performance

All of this happens transparently - you just send messages and get responses.

## SDK Libraries

### Official SDKs
- **JavaScript/TypeScript**: `npm install @gaia/api-client`
- **Python**: `pip install gaia-api-client`
- **Go**: `go get github.com/gaia-platform/go-client`

### Community SDKs
- **Ruby**: `gem install gaia-rb`
- **PHP**: `composer require gaia/api-client`
- **Java**: Available on Maven Central

## Support

- **Documentation**: https://docs.gaia-platform.com
- **API Reference**: https://api.gaia-platform.com/docs
- **Support**: support@gaia-platform.com
- **Status**: https://status.gaia-platform.com

## Changelog

### v0.3.0 (Current)
- Clean, simplified API format
- Automatic conversation management
- Streaming support with simple format
- Hidden provider complexity
- Sub-second response times for simple queries

---

*This documentation covers GAIA v0.3 API. For v1 (OpenAI-compatible) API documentation, see [v1 API Docs](v01-api-documentation.md).*