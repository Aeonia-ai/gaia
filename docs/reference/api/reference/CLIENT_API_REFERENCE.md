# GAIA v0.3 API Reference


**Audience**: External developers integrating with GAIA  
**Focus**: Client SDKs, code examples, practical implementation  
**Recommended Version**: v0.3 for new integrations (cleaner responses)

> **Need Advanced Features?** See [GAIA_API_REFERENCE.md](GAIA_API_REFERENCE.md) for personas and asset management  
> **System Architecture?** See [GAIA_API_MAP.md](GAIA_API_MAP.md) for complete service mapping

## Important: v0.3 vs v1 API

Both API versions use the **same intelligent routing system** internally:
- **v0.3** (Recommended): Clean responses without provider/model details
- **v1**: Backward compatibility, includes provider metadata
- **Both**: Same features, KB access, streaming support

**Base URL:** `https://gaia-gateway-{env}.fly.dev`  
**Environments:** `dev`, `staging`, `prod`  
**API Version:** v0.3

## Authentication

All endpoints except `/health` require authentication via API Key or JWT Bearer token.

```bash
# API Key
curl -H "X-API-Key: YOUR_KEY" https://gaia-gateway-dev.fly.dev/api/v0.3/chat

# JWT Token  
curl -H "Authorization: Bearer YOUR_TOKEN" https://gaia-gateway-dev.fly.dev/api/v0.3/chat
```

## Available Endpoints

### 🟢 Public Endpoints (No Auth Required)

#### `GET /health`
Health check for monitoring and deployment.

```bash
curl https://gaia-gateway-dev.fly.dev/health
```

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

### 🔐 Authentication Endpoints

#### `POST /api/v0.3/auth/login`
Login with email/password to get JWT tokens.

```bash
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

**Response:**
```json
{
  "session": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "expires_in": 3600
  },
  "user": {
    "id": "user-123",
    "email": "user@example.com"
  }
}
```

#### `POST /api/v0.3/auth/register`
Register new user account.

```bash
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "password": "SecurePass123!"}'
```

#### `POST /api/v0.3/auth/validate`
Validate current authentication token.

```bash
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/auth/validate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### `POST /api/v0.3/auth/refresh`
Refresh expired access token.

```bash
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

#### `POST /api/v0.3/auth/logout`
Logout and invalidate tokens.

```bash
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### `POST /api/v0.3/auth/confirm`
Confirm email with verification token.

```bash
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/auth/confirm \
  -H "Content-Type: application/json" \
  -d '{"token": "verification-token-from-email"}'
```

#### `POST /api/v0.3/auth/resend-verification`
Resend email verification.

```bash
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

### 💬 Chat Endpoints

#### `POST /api/v0.3/chat`
Main chat endpoint with clean response format.

**Basic Chat:**
```bash
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/chat \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is quantum computing?",
    "conversation_id": "optional-id"
  }'
```

**Response:**
```json
{
  "response": "Quantum computing is a type of computing that uses quantum mechanics...",
  "message": "What is quantum computing?",
  "conversation_id": "conv-123"
}
```

**Streaming Chat:**
```bash
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/chat \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me a story about robots",
    "stream": true
  }'
```

**Streaming Response (Server-Sent Events):**
```
data: {"type": "content", "content": "Once upon a time"}
data: {"type": "content", "content": " in a digital city"}
data: {"type": "done", "finish_reason": "stop"}
data: [DONE]
```

### 📚 Conversation Management

#### `GET /api/v0.3/conversations`
List all conversations for the authenticated user.

```bash
curl https://gaia-gateway-dev.fly.dev/api/v0.3/conversations \
  -H "X-API-Key: YOUR_KEY"
```

**Response:**
```json
{
  "conversations": [
    {
      "id": "conv-123",
      "title": "Quantum Physics Discussion",
      "created_at": "2025-08-20T10:00:00Z",
      "updated_at": "2025-08-20T11:30:00Z",
      "message_count": 15
    },
    {
      "id": "conv-456",
      "title": "AI Ethics Debate",
      "created_at": "2025-08-19T14:00:00Z",
      "updated_at": "2025-08-19T15:45:00Z",
      "message_count": 23
    }
  ]
}
```

#### `POST /api/v0.3/conversations`
Create a new conversation.

```bash
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/conversations \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "New Research Topic"}'
```

**Response:**
```json
{
  "id": "conv-789",
  "title": "New Research Topic",
  "created_at": "2025-08-20T12:00:00Z",
  "message_count": 0
}
```

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Detailed error message"
}
```

**Common Error Codes:**
- `401` - Unauthorized (missing or invalid auth)
- `404` - Resource not found
- `400` - Bad request (invalid format)
- `429` - Rate limit exceeded
- `500` - Internal server error

## Rate Limits

- **Default:** 60 requests/minute per user (authenticated by API key or JWT)
- **IP-based:** 60 requests/minute for unauthenticated requests
- **Streaming:** Counts as 1 request regardless of duration

## Code Examples

### Python
```python
import requests
import json

class GaiaClient:
    def __init__(self, api_key, base_url="https://gaia-gateway-dev.fly.dev"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    def chat(self, message, conversation_id=None):
        """Send a chat message and get response"""
        data = {"message": message}
        if conversation_id:
            data["conversation_id"] = conversation_id
        
        response = requests.post(
            f"{self.base_url}/api/v0.3/chat",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def stream_chat(self, message):
        """Stream a chat response"""
        response = requests.post(
            f"{self.base_url}/api/v0.3/chat",
            headers=self.headers,
            json={"message": message, "stream": True},
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data != '[DONE]':
                        yield json.loads(data)

# Usage
client = GaiaClient("your-api-key")
response = client.chat("What is the meaning of life?")
print(response["response"])
```

### JavaScript/TypeScript
```typescript
class GaiaClient {
  constructor(
    private apiKey: string,
    private baseUrl = "https://gaia-gateway-dev.fly.dev"
  ) {}

  async chat(message: string, conversationId?: string) {
    const response = await fetch(`${this.baseUrl}/api/v0.3/chat`, {
      method: "POST",
      headers: {
        "X-API-Key": this.apiKey,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId
      })
    });
    
    return response.json();
  }

  async *streamChat(message: string) {
    const response = await fetch(`${this.baseUrl}/api/v0.3/chat`, {
      method: "POST",
      headers: {
        "X-API-Key": this.apiKey,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message,
        stream: true
      })
    });

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") return;
          yield JSON.parse(data);
        }
      }
    }
  }
}

// Usage
const client = new GaiaClient("your-api-key");
const response = await client.chat("Hello!");
console.log(response.response);
```

### cURL Quick Reference
```bash
# Basic chat
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/chat \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'

# List conversations
curl https://gaia-gateway-dev.fly.dev/api/v0.3/conversations \
  -H "X-API-Key: YOUR_KEY"

# Login
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.3/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

## Deployment Endpoints

**Development:** `https://gaia-gateway-dev.fly.dev`  
**Staging:** `https://gaia-gateway-staging.fly.dev`  
**Production:** `https://gaia-gateway-production.fly.dev`  
**Local:** `http://localhost:8666`

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

The API endpoints described in this document have been verified against the gateway's routing implementation.

-   **✅ Authentication Endpoints:**
    *   **Claim:** The document lists endpoints for `/auth/login`, `/register`, `/validate`, `/refresh`, `/logout`, `/confirm`, and `/resend-verification`.
    *   **Code Reference:** `app/gateway/main.py` (lines 1013-1045).
    *   **Verification:** This is **VERIFIED**. The gateway defines all these v0.3 routes and correctly forwards them to the `auth` service.

-   **✅ Chat Endpoints:**
    *   **Claim:** The `POST /api/v0.3/chat` endpoint handles both streaming and non-streaming chat.
    *   **Code Reference:** `app/gateway/main.py` (lines 909-955, `v03_chat` function).
    *   **Verification:** This is **VERIFIED**. The `v03_chat` function forwards requests to the unified chat service and uses helper functions (`_convert_to_clean_streaming_format` and `_convert_to_clean_format`) to provide the clean v0.3 response format.

-   **✅ Conversation Management:**
    *   **Claim:** `GET` and `POST` requests to `/api/v0.3/conversations` are supported for listing and creating conversations.
    *   **Code Reference:** `app/gateway/main.py` (lines 957-1011).
    *   **Verification:** This is **VERIFIED**. The `v03_list_conversations` and `v03_create_conversation` functions correctly forward requests to the `chat` service's conversation endpoints.

-   **✅ Error Responses and Rate Limits:**
    *   **Verification:** The use of FastAPI's exception handling and the `slowapi` limiter in `app/gateway/main.py` confirms the implementation of consistent error responses and rate limiting.

**Overall Conclusion:** The API endpoints and functionality described in this document are accurately implemented in the gateway service. The document provides a reliable reference for client-side developers.