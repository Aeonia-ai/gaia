# Gaia Platform Client Usage Guide

This guide explains how client applications interact with the Gaia Platform API.

## Overview

All client applications interact with the Gaia Platform through a single gateway endpoint. The gateway handles authentication, routing, load balancing, and service orchestration.

**Production Gateway URL**: `https://gaia-gateway-dev.fly.dev`

> **Important**: Clients should NEVER call individual microservices directly. All requests must go through the gateway.

## Authentication

The Gaia Platform supports two authentication methods:

### 1. API Key Authentication

For server-to-server communication or trusted clients.

```bash
curl -H "X-API-Key: YOUR_API_KEY" https://gaia-gateway-dev.fly.dev/api/v1/assets
```

### 2. JWT Token Authentication

For user-based authentication via Supabase.

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" https://gaia-gateway-dev.fly.dev/api/v1/assets
```

### 3. User-Associated API Keys

For user-specific API keys created through the platform.

```bash
curl -H "X-API-Key: gaia_dev_abc123..." https://gaia-gateway-dev.fly.dev/api/v1/assets
```

> **Note**: The existing LLM Platform API key continues to work and is now associated with user `jason@aeonia.ai` for proper authentication tracking.

## API Endpoints

### Health Check
Check the health status of all services (no authentication required).

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-09T20:05:04.695387",
  "services": {
    "auth": {"status": "healthy", "response_time": 0.078613},
    "asset": {"status": "healthy", "response_time": 0.006306},
    "chat": {"status": "healthy", "response_time": 0.006}
  },
  "database": {"status": "healthy", "database": "postgresql", "responsive": true},
  "supabase": {"status": "healthy", "service": "supabase", "url": "https://..."},
  "version": "1.0.0"
}
```

### Asset Management

#### Search Assets
```bash
GET /api/v1/assets/search?query={search_term}
```

**Parameters:**
- `query` (required): Search term for assets
- `limit` (optional): Number of results (default: 20, max: 100)
- `offset` (optional): Pagination offset

**Example:**
```bash
curl -X GET "https://gaia-gateway-dev.fly.dev/api/v1/assets/search?query=fantasy+sword" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Generate Asset
```bash
POST /api/v1/assets/generate
```

**Request Body:**
```json
{
  "category": "prop",
  "style": "fantasy",
  "description": "A glowing magical sword with runes",
  "requirements": {
    "platform": "mobile_vr",
    "quality": "medium",
    "polygon_count_max": 5000
  },
  "preferences": {
    "allow_generation": true,
    "max_cost": 0.50,
    "max_wait_time_ms": 30000
  }
}
```

**Example:**
```bash
curl -X POST "https://gaia-gateway-dev.fly.dev/api/v1/assets/generate" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "prop",
    "style": "fantasy",
    "description": "A glowing magical sword with runes"
  }'
```

### Chat & LLM

#### Chat Completion
```bash
POST /api/v1/chat
```

**Request Body:**
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful game design assistant"},
    {"role": "user", "content": "Help me design a VR puzzle room"}
  ],
  "model": "claude-3-opus-20240229",
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**Streaming Example:**
```bash
curl -X POST "https://gaia-gateway-dev.fly.dev/api/v1/chat" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Tell me a story",
    "stream": true
  }'
```

#### List Personas
```bash
GET /api/v1/chat/personas
```

**Example:**
```bash
curl -X GET "https://gaia-gateway-dev.fly.dev/api/v1/chat/personas" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Authentication

#### Validate Token
```bash
POST /api/v1/auth/validate
```

**Request Body:**
```json
{
  "token": "YOUR_JWT_TOKEN"
}
```

#### Refresh Token
```bash
POST /api/v1/auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "YOUR_REFRESH_TOKEN"
}
```

## Client SDK Examples

### JavaScript/TypeScript

```javascript
class GaiaClient {
  constructor(apiKey) {
    this.baseURL = 'https://gaia-gateway-dev.fly.dev';
    this.apiKey = apiKey;
  }

  async request(path, options = {}) {
    const response = await fetch(`${this.baseURL}${path}`, {
      ...options,
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
  }

  // Asset Management
  async searchAssets(query, limit = 20) {
    return this.request(`/api/v1/assets/search?query=${encodeURIComponent(query)}&limit=${limit}`);
  }

  async generateAsset(assetRequest) {
    return this.request('/api/v1/assets/generate', {
      method: 'POST',
      body: JSON.stringify(assetRequest)
    });
  }

  // Chat
  async chat(message, options = {}) {
    return this.request('/api/v1/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        model: options.model || 'claude-3-opus-20240229',
        stream: options.stream || false,
        temperature: options.temperature || 0.7
      })
    });
  }

  async getPersonas() {
    return this.request('/api/v1/chat/personas');
  }
}

// Usage
const gaia = new GaiaClient('YOUR_API_KEY');

// Search for assets
const assets = await gaia.searchAssets('sci-fi environment');

// Generate an asset
const newAsset = await gaia.generateAsset({
  category: 'prop',
  style: 'sci-fi',
  description: 'A futuristic laser rifle'
});

// Chat completion
const response = await gaia.chat('Design a boss battle for my VR game');
```

### Unity C#

```csharp
using System;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;

public class GaiaAPIClient : MonoBehaviour 
{
    private const string BASE_URL = "https://gaia-gateway-dev.fly.dev";
    private string apiKey;

    public GaiaAPIClient(string apiKey) 
    {
        this.apiKey = apiKey;
    }

    // Asset Search
    public async Task<AssetSearchResult> SearchAssets(string query, int limit = 20) 
    {
        string url = $"{BASE_URL}/api/v1/assets/search?query={UnityWebRequest.EscapeURL(query)}&limit={limit}";
        
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            request.SetRequestHeader("X-API-Key", apiKey);
            request.SetRequestHeader("Content-Type", "application/json");
            
            await request.SendWebRequest();
            
            if (request.result != UnityWebRequest.Result.Success)
            {
                throw new Exception($"API Error: {request.error}");
            }
            
            return JsonConvert.DeserializeObject<AssetSearchResult>(request.downloadHandler.text);
        }
    }

    // Asset Generation
    public async Task<AssetResponse> GenerateAsset(AssetRequest assetRequest) 
    {
        string url = $"{BASE_URL}/api/v1/assets/generate";
        string jsonBody = JsonConvert.SerializeObject(assetRequest);
        
        using (UnityWebRequest request = UnityWebRequest.Post(url, jsonBody, "application/json"))
        {
            request.SetRequestHeader("X-API-Key", apiKey);
            
            await request.SendWebRequest();
            
            if (request.result != UnityWebRequest.Result.Success)
            {
                throw new Exception($"API Error: {request.error}");
            }
            
            return JsonConvert.DeserializeObject<AssetResponse>(request.downloadHandler.text);
        }
    }

    // Chat Completion
    public async Task<ChatResponse> SendChatMessage(string message) 
    {
        string url = $"{BASE_URL}/api/v1/chat";
        var requestData = new {
            message = message,
            model = "claude-3-opus-20240229",
            stream = false
        };
        
        string jsonBody = JsonConvert.SerializeObject(requestData);
        
        using (UnityWebRequest request = UnityWebRequest.Post(url, jsonBody, "application/json"))
        {
            request.SetRequestHeader("X-API-Key", apiKey);
            
            await request.SendWebRequest();
            
            if (request.result != UnityWebRequest.Result.Success)
            {
                throw new Exception($"API Error: {request.error}");
            }
            
            return JsonConvert.DeserializeObject<ChatResponse>(request.downloadHandler.text);
        }
    }
}

// Data Models
[Serializable]
public class AssetSearchResult 
{
    public AssetMetadata[] assets;
    public int total_count;
    public int query_time_ms;
}

[Serializable]
public class AssetRequest 
{
    public string category;
    public string style;
    public string description;
    public AssetRequirements requirements;
}

[Serializable]
public class ChatMessage 
{
    public string role;
    public string content;
}
```

### Python

```python
import requests
from typing import List, Dict, Optional

class GaiaClient:
    def __init__(self, api_key: str):
        self.base_url = "https://gaia-gateway-dev.fly.dev"
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def search_assets(self, query: str, limit: int = 20) -> Dict:
        """Search for assets in the database."""
        response = requests.get(
            f"{self.base_url}/api/v1/assets/search",
            params={"query": query, "limit": limit},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def generate_asset(self, asset_request: Dict) -> Dict:
        """Generate a new asset using AI."""
        response = requests.post(
            f"{self.base_url}/api/v1/assets/generate",
            json=asset_request,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def chat(self, message: str, model: str = "claude-3-opus-20240229") -> Dict:
        """Send a chat completion request."""
        response = requests.post(
            f"{self.base_url}/api/v1/chat",
            json={
                "message": message,
                "model": model,
                "stream": False
            },
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_personas(self) -> List[Dict]:
        """Get available chat personas."""
        response = requests.get(
            f"{self.base_url}/api/v1/chat/personas",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage example
if __name__ == "__main__":
    client = GaiaClient("YOUR_API_KEY")
    
    # Search for assets
    results = client.search_assets("fantasy sword")
    print(f"Found {results['total_count']} assets")
    
    # Generate an asset
    new_asset = client.generate_asset({
        "category": "prop",
        "style": "fantasy",
        "description": "A glowing magical staff"
    })
    print(f"Generated asset: {new_asset['asset_id']}")
    
    # Chat completion
    response = client.chat("Design a puzzle for my VR escape room")
    print(response['choices'][0]['message']['content'])
```

## Error Handling

### Common Error Codes

- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Valid auth but insufficient permissions
- **404 Not Found**: Resource or endpoint not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily down

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 401,
  "error_type": "authentication_error"
}
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Default**: 60 requests per minute per API key
- **Burst**: Up to 10 requests per second allowed
- **Headers**: Rate limit info returned in response headers
  - `X-RateLimit-Limit`: Total requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

## Best Practices

1. **Always use HTTPS**: All API calls must use HTTPS
2. **Handle errors gracefully**: Implement exponential backoff for retries
3. **Cache responses**: Cache asset searches and personas when appropriate
4. **Use streaming for long responses**: Enable streaming for chat completions
5. **Respect rate limits**: Monitor rate limit headers and throttle requests
6. **Keep API keys secure**: Never expose API keys in client-side code

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: https://gaia-gateway-dev.fly.dev/docs
- **ReDoc**: https://gaia-gateway-dev.fly.dev/redoc
- **OpenAPI JSON**: https://gaia-gateway-dev.fly.dev/openapi.json

## Migration from LLM Platform

If migrating from the original LLM Platform, simply update your base URL:

```javascript
// Old
const BASE_URL = "https://your-llm-platform.com";

// New
const BASE_URL = "https://gaia-gateway-dev.fly.dev";
```

All endpoints and request/response formats remain 100% compatible.

### API Key Migration

The existing LLM Platform API key continues to work exactly as before, but is now associated with user `jason@aeonia.ai` for proper authentication tracking and management.