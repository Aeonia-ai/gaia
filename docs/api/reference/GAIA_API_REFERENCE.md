# GAIA Platform API Reference

**Audience**: Platform developers building on advanced features  
**Focus**: Complete API including personas, assets, and OpenAI compatibility  

> **Quick Start?** See [CLIENT_API_REFERENCE.md](CLIENT_API_REFERENCE.md) for client SDK examples  
> **Service Architecture?** See [GAIA_API_MAP.md](GAIA_API_MAP.md) for internal routing

**Version:** 1.0  
**Base URL:** `https://gaia-gateway-{environment}.fly.dev`  
**Environments:** `dev`, `staging`, `prod`

## Authentication

All endpoints except `/health` and auth endpoints require authentication.

### API Key Authentication
```bash
curl -H "X-API-Key: YOUR_API_KEY" https://gaia-gateway-dev.fly.dev/api/v0.3/chat
```

### JWT Authentication
```bash
# 1. Login to get JWT
curl -X POST https://gaia-gateway-dev.fly.dev/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# 2. Use JWT in requests
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" https://gaia-gateway-dev.fly.dev/api/v0.3/chat
```

## Core Endpoints

### Health Check
```bash
GET /health
```
No authentication required. Returns service status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-20T22:07:26.387756",
  "version": "0.2.0",
  "services": {
    "auth": {"status": "healthy", "response_time": 0.007},
    "chat": {"status": "healthy", "response_time": 0.008},
    "kb": {"status": "healthy", "response_time": 0.006},
    "asset": {"status": "healthy", "response_time": 0.005}
  }
}
```

### Chat Completion

#### Basic Chat (v0.3 - Recommended)
```bash
POST /api/v0.3/chat
Content-Type: application/json

{
  "message": "What is the meaning of life?",
  "conversation_id": "optional-conversation-id",
  "stream": false
}
```

**Response:**
```json
{
  "response": "The meaning of life is...",
  "conversation_id": "auto-generated-id",
  "message": "What is the meaning of life?"
}
```

#### Streaming Chat (v0.3)
```bash
POST /api/v0.3/chat
Content-Type: application/json

{
  "message": "Write a story about a robot",
  "stream": true
}
```

**Response:** Server-Sent Events stream
```
data: {"type": "content", "content": "Once upon a time"}
data: {"type": "content", "content": " there was a robot"}
data: {"type": "done", "finish_reason": "stop"}
data: [DONE]
```

#### OpenAI-Compatible Chat (v1)
```bash
POST /api/v1/chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "stream": false
}
```

**Response:** OpenAI-compatible format
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1733856000,
  "model": "claude-3-5-haiku-20241022",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "I'm doing well, thank you!"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}
```

### Conversation Management (v0.3)

#### List Conversations
```bash
GET /api/v0.3/conversations
```

**Response:**
```json
{
  "conversations": [
    {
      "id": "conv-123",
      "created_at": "2025-08-20T10:00:00Z",
      "updated_at": "2025-08-20T11:30:00Z",
      "title": "Discussion about AI",
      "message_count": 5
    }
  ]
}
```

#### Create Conversation
```bash
POST /api/v0.3/conversations
Content-Type: application/json

{
  "title": "New Conversation"
}
```

**Response:**
```json
{
  "id": "conv-456",
  "created_at": "2025-08-20T12:00:00Z",
  "title": "New Conversation"
}
```

### Authentication Endpoints

#### Login
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "session": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "expires_in": 3600,
    "token_type": "bearer"
  },
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "email_confirmed_at": "2025-08-20T10:00:00Z"
  }
}
```

#### Register
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "secure-password"
}
```

**Response:** Same as login

#### Validate Token
```bash
POST /api/v1/auth/validate
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN_OR_API_KEY

{}
```

**Response:**
```json
{
  "valid": true,
  "user_id": "user-123",
  "type": "jwt"
}
```

### Persona Management

#### Get Available Personas
```bash
GET /api/v1/chat/personas
```

**Response:**
```json
{
  "personas": [
    {
      "id": "mu",
      "name": "μ (Mu)",
      "description": "Embodiment of unity consciousness",
      "is_default": true
    },
    {
      "id": "ava",
      "name": "Ava",
      "description": "Quantum mechanics and multiverse researcher"
    }
  ]
}
```

#### Set User Persona
```bash
PUT /api/v1/chat/personas
Content-Type: application/json

{
  "persona_id": "ava"
}
```

### Asset Management

#### List Assets
```bash
GET /api/v1/assets
```

**Response:**
```json
{
  "assets": [
    {
      "id": "asset-123",
      "filename": "image.png",
      "content_type": "image/png",
      "size": 102400,
      "created_at": "2025-08-20T10:00:00Z"
    }
  ]
}
```

#### Upload Asset
```bash
POST /api/v1/assets
Content-Type: multipart/form-data

file=@/path/to/file.png
```

**Response:**
```json
{
  "id": "asset-456",
  "filename": "file.png",
  "url": "/api/v1/assets/asset-456"
}
```

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error message here",
  "type": "error_type",
  "status_code": 400
}
```

Common errors:
- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - Resource doesn't exist
- `400 Bad Request` - Invalid request format
- `500 Internal Server Error` - Server error

## Rate Limits

- **Anonymous:** 10 requests/minute
- **Authenticated:** 100 requests/minute
- **Streaming:** Counts as 1 request regardless of duration

## Code Examples

### Python
```python
import requests

# Setup
api_key = "YOUR_API_KEY"
base_url = "https://gaia-gateway-dev.fly.dev"
headers = {"X-API-Key": api_key}

# Simple chat
response = requests.post(
    f"{base_url}/api/v0.3/chat",
    headers=headers,
    json={"message": "Hello, AI!"}
)
print(response.json()["response"])

# Streaming chat
import sseclient

response = requests.post(
    f"{base_url}/api/v0.3/chat",
    headers=headers,
    json={"message": "Tell me a story", "stream": True},
    stream=True
)

client = sseclient.SSEClient(response)
for event in client.events():
    if event.data != "[DONE]":
        data = json.loads(event.data)
        print(data.get("content", ""), end="", flush=True)
```

### JavaScript/TypeScript
```typescript
// Simple chat
const response = await fetch('https://gaia-gateway-dev.fly.dev/api/v0.3/chat', {
  method: 'POST',
  headers: {
    'X-API-Key': 'YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'Hello, AI!'
  })
});

const data = await response.json();
console.log(data.response);

// Streaming chat
const streamResponse = await fetch('https://gaia-gateway-dev.fly.dev/api/v0.3/chat', {
  method: 'POST',
  headers: {
    'X-API-Key': 'YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'Tell me a story',
    stream: true
  })
});

const reader = streamResponse.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') continue;
      
      const parsed = JSON.parse(data);
      process.stdout.write(parsed.content || '');
    }
  }
}
```

## Testing Your Integration

### Quick Test
```bash
# Test health
curl https://gaia-gateway-dev.fly.dev/health

# Test chat (replace with your API key)
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/chat \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Say hello"}'
```

### Available Environments
- **Development:** `https://gaia-gateway-dev.fly.dev`
- **Staging:** `https://gaia-gateway-staging.fly.dev`
- **Production:** `https://gaia-gateway-prod.fly.dev`

## Support

- **Issues:** https://github.com/your-org/gaia/issues
- **Status:** https://status.gaia.dev
- **Contact:** support@gaia.dev