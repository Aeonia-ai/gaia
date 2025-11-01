# GAIA v0.3 Client Specification

**Version**: 0.3.0  
**Date**: 2025-08-15  
**Status**: Stable

## Overview

This specification defines the requirements and recommendations for implementing GAIA v0.3 API clients. It covers authentication, request/response handling, error management, streaming implementation, and best practices for reliable client integration.

## Design Goals

- **Simplicity**: Minimal complexity for client implementations
- **Reliability**: Robust error handling and retry mechanisms
- **Performance**: Efficient request/response handling and streaming
- **Consistency**: Standardized behavior across all client libraries
- **Future-proof**: Extensible design for API evolution

## Client Requirements

### 1. Core Interface

Every GAIA v0.3 client MUST implement the following core interface:

```typescript
interface GaiaV03Client {
  // Basic chat functionality
  chat(message: string, options?: ChatOptions): Promise<ChatResponse>;
  
  // Streaming chat
  streamChat(message: string, options?: StreamChatOptions): AsyncIterable<StreamChunk>;
  
  // Configuration
  setApiKey(apiKey: string): void;
  setBaseUrl(baseUrl: string): void;
  
  // Health check
  healthCheck(): Promise<HealthResponse>;
}

interface ChatOptions {
  conversationId?: string;
  timeout?: number;
}

interface StreamChatOptions extends ChatOptions {
  onChunk?: (chunk: StreamChunk) => void;
  onComplete?: (response: ChatResponse) => void;
  onError?: (error: Error) => void;
}

interface ChatResponse {
  response: string;
  conversationId: string;
  metadata?: ClientMetadata;
}

interface StreamChunk {
  type: 'content' | 'done';
  content?: string;
  conversationId?: string;
}

interface ClientMetadata {
  requestId?: string;
  responseTime?: number;
  cached?: boolean;
}
```

### 2. Authentication

#### API Key Management

```typescript
class GaiaV03Client {
  private apiKey: string;
  
  constructor(apiKey: string, baseUrl?: string) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl || 'https://api.gaia-platform.com';
  }
  
  setApiKey(apiKey: string): void {
    if (!apiKey || typeof apiKey !== 'string') {
      throw new Error('API key must be a non-empty string');
    }
    this.apiKey = apiKey;
  }
}
```

#### Authentication Headers

All requests MUST include:
```http
X-API-Key: {apiKey}
Content-Type: application/json
User-Agent: gaia-client/{version} {language}/{language-version}
```

### 3. Request Handling

#### Basic Chat Request

```typescript
async chat(message: string, options: ChatOptions = {}): Promise<ChatResponse> {
  if (!message || typeof message !== 'string') {
    throw new ValidationError('Message must be a non-empty string');
  }
  
  const request: ChatRequest = {
    message: message.trim(),
    stream: false
  };
  
  if (options.conversationId) {
    request.conversation_id = options.conversationId;
  }
  
  const response = await this.makeRequest('/api/v0.3/chat', {
    method: 'POST',
    body: JSON.stringify(request),
    timeout: options.timeout || this.defaultTimeout
  });
  
  return this.parseChatResponse(response);
}
```

#### Request Validation

Clients MUST validate:
- Message is non-empty string
- Conversation ID format (if provided): `/^conv-[a-zA-Z0-9]{12,}$/`
- Timeout is positive number
- Stream flag is boolean

```typescript
private validateMessage(message: string): void {
  if (!message) {
    throw new ValidationError('Message cannot be empty');
  }
  if (typeof message !== 'string') {
    throw new ValidationError('Message must be a string');
  }
  if (message.trim().length === 0) {
    throw new ValidationError('Message cannot be only whitespace');
  }
  if (message.length > 32768) { // 32KB limit
    throw new ValidationError('Message exceeds maximum length');
  }
}

private validateConversationId(conversationId?: string): void {
  if (conversationId && !/^conv-[a-zA-Z0-9]{12,}$/.test(conversationId)) {
    throw new ValidationError('Invalid conversation ID format');
  }
}
```

### 4. Response Processing

#### Standard Response Parsing

```typescript
private parseChatResponse(response: Response): ChatResponse {
  if (!response.ok) {
    throw this.createErrorFromResponse(response);
  }
  
  const data = response.json();
  
  // Validate response structure
  if (!data.response || typeof data.response !== 'string') {
    throw new ParseError('Invalid response format: missing response field');
  }
  
  if (!data.conversation_id || typeof data.conversation_id !== 'string') {
    throw new ParseError('Invalid response format: missing conversation_id field');
  }
  
  return {
    response: data.response,
    conversationId: data.conversation_id,
    metadata: this.extractMetadata(response)
  };
}

private extractMetadata(response: Response): ClientMetadata {
  const requestId = response.headers.get('X-Request-ID');
  const responseTime = response.headers.get('X-Response-Time');
  const cached = response.headers.get('X-Cache-Status') === 'HIT';
  
  return {
    requestId: requestId || undefined,
    responseTime: responseTime ? parseInt(responseTime) : undefined,
    cached
  };
}
```

### 5. Streaming Implementation

#### Server-Sent Events Processing

```typescript
async *streamChat(message: string, options: StreamChatOptions = {}): AsyncIterable<StreamChunk> {
  const request: StreamChatRequest = {
    message: message.trim(),
    stream: true
  };
  
  if (options.conversationId) {
    request.conversation_id = options.conversationId;
  }
  
  const response = await this.makeRequest('/api/v0.3/chat', {
    method: 'POST',
    body: JSON.stringify(request),
    timeout: options.timeout || this.streamTimeout
  });
  
  if (!response.ok) {
    throw this.createErrorFromResponse(response);
  }
  
  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  
  if (!reader) {
    throw new StreamError('Response body is not readable');
  }
  
  let buffer = '';
  let conversationId = '';
  
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const chunk = this.parseStreamChunk(line.slice(6));
          
          if (chunk.type === 'content') {
            options.onChunk?.(chunk);
            yield chunk;
          } else if (chunk.type === 'done') {
            conversationId = chunk.conversationId || '';
            options.onComplete?.({
              response: this.getAccumulatedResponse(),
              conversationId
            });
            yield chunk;
            return;
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

private parseStreamChunk(data: string): StreamChunk {
  try {
    const parsed = JSON.parse(data);
    
    if (parsed.type === 'content') {
      if (typeof parsed.content !== 'string') {
        throw new ParseError('Content chunk must contain string content');
      }
      return { type: 'content', content: parsed.content };
    }
    
    if (parsed.type === 'done') {
      return { 
        type: 'done', 
        conversationId: parsed.conversation_id || undefined 
      };
    }
    
    throw new ParseError(`Unknown chunk type: ${parsed.type}`);
  } catch (error) {
    throw new ParseError(`Invalid stream chunk: ${error.message}`);
  }
}
```

### 6. Error Handling

#### Error Types

```typescript
class GaiaError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode?: number,
    public requestId?: string
  ) {
    super(message);
    this.name = 'GaiaError';
  }
}

class ValidationError extends GaiaError {
  constructor(message: string) {
    super(message, 'VALIDATION_ERROR');
    this.name = 'ValidationError';
  }
}

class AuthenticationError extends GaiaError {
  constructor(message: string, requestId?: string) {
    super(message, 'AUTHENTICATION_ERROR', 401, requestId);
    this.name = 'AuthenticationError';
  }
}

class RateLimitError extends GaiaError {
  constructor(
    message: string,
    public retryAfter: number,
    requestId?: string
  ) {
    super(message, 'RATE_LIMIT_ERROR', 429, requestId);
    this.name = 'RateLimitError';
  }
}

class StreamError extends GaiaError {
  constructor(message: string) {
    super(message, 'STREAM_ERROR');
    this.name = 'StreamError';
  }
}

class ParseError extends GaiaError {
  constructor(message: string) {
    super(message, 'PARSE_ERROR');
    this.name = 'ParseError';
  }
}
```

#### Error Response Processing

```typescript
private createErrorFromResponse(response: Response): GaiaError {
  const requestId = response.headers.get('X-Request-ID');
  
  switch (response.status) {
    case 400:
      return new ValidationError(
        'Bad request: Check your message format'
      );
      
    case 401:
      return new AuthenticationError(
        'Invalid API key',
        requestId
      );
      
    case 429:
      const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
      return new RateLimitError(
        'Rate limit exceeded',
        retryAfter,
        requestId
      );
      
    case 500:
      return new GaiaError(
        'Internal server error',
        'SERVER_ERROR',
        500,
        requestId
      );
      
    default:
      return new GaiaError(
        `HTTP ${response.status}: ${response.statusText}`,
        'HTTP_ERROR',
        response.status,
        requestId
      );
  }
}
```

### 7. Retry Logic

#### Automatic Retry Implementation

```typescript
class RetryConfig {
  maxRetries: number = 3;
  baseDelay: number = 1000;
  maxDelay: number = 30000;
  backoffMultiplier: number = 2;
  retryableStatusCodes: Set<number> = new Set([429, 500, 502, 503, 504]);
}

async makeRequestWithRetry<T>(
  url: string,
  options: RequestOptions
): Promise<T> {
  let lastError: Error;
  
  for (let attempt = 0; attempt <= this.retryConfig.maxRetries; attempt++) {
    try {
      return await this.makeRequest<T>(url, options);
    } catch (error) {
      lastError = error;
      
      if (!this.shouldRetry(error, attempt)) {
        throw error;
      }
      
      const delay = this.calculateDelay(attempt);
      await this.sleep(delay);
    }
  }
  
  throw lastError;
}

private shouldRetry(error: Error, attempt: number): boolean {
  if (attempt >= this.retryConfig.maxRetries) {
    return false;
  }
  
  if (error instanceof RateLimitError) {
    return true;
  }
  
  if (error instanceof GaiaError && error.statusCode) {
    return this.retryConfig.retryableStatusCodes.has(error.statusCode);
  }
  
  // Network errors (timeout, connection refused, etc.)
  if (error.name === 'TypeError' || error.name === 'AbortError') {
    return true;
  }
  
  return false;
}

private calculateDelay(attempt: number): number {
  const delay = this.retryConfig.baseDelay * 
    Math.pow(this.retryConfig.backoffMultiplier, attempt);
  
  // Add jitter to prevent thundering herd
  const jitter = delay * 0.1 * Math.random();
  
  return Math.min(delay + jitter, this.retryConfig.maxDelay);
}
```

### 8. Configuration Management

#### Client Configuration

```typescript
interface ClientConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
  streamTimeout?: number;
  retryConfig?: RetryConfig;
  userAgent?: string;
  defaultHeaders?: Record<string, string>;
}

class GaiaV03Client {
  private config: Required<ClientConfig>;
  
  constructor(config: ClientConfig) {
    this.config = {
      apiKey: config.apiKey,
      baseUrl: config.baseUrl || 'https://api.gaia-platform.com',
      timeout: config.timeout || 30000,
      streamTimeout: config.streamTimeout || 60000,
      retryConfig: config.retryConfig || new RetryConfig(),
      userAgent: config.userAgent || this.getDefaultUserAgent(),
      defaultHeaders: config.defaultHeaders || {}
    };
    
    this.validateConfig();
  }
  
  private validateConfig(): void {
    if (!this.config.apiKey) {
      throw new ValidationError('API key is required');
    }
    
    if (this.config.timeout <= 0) {
      throw new ValidationError('Timeout must be positive');
    }
    
    try {
      new URL(this.config.baseUrl);
    } catch {
      throw new ValidationError('Invalid base URL');
    }
  }
}
```

### 9. Conversation Management

#### Conversation State Tracking

```typescript
class ConversationManager {
  private conversations = new Map<string, ConversationState>();
  
  createConversation(): string {
    const id = this.generateConversationId();
    this.conversations.set(id, {
      id,
      createdAt: new Date(),
      messageCount: 0,
      lastActivity: new Date()
    });
    return id;
  }
  
  updateConversation(id: string, response: ChatResponse): void {
    const conversation = this.conversations.get(id);
    if (conversation) {
      conversation.messageCount++;
      conversation.lastActivity = new Date();
    }
  }
  
  getConversation(id: string): ConversationState | undefined {
    return this.conversations.get(id);
  }
  
  clearOldConversations(maxAge: number = 24 * 60 * 60 * 1000): void {
    const cutoff = new Date(Date.now() - maxAge);
    for (const [id, conversation] of this.conversations) {
      if (conversation.lastActivity < cutoff) {
        this.conversations.delete(id);
      }
    }
  }
}

interface ConversationState {
  id: string;
  createdAt: Date;
  messageCount: number;
  lastActivity: Date;
}
```

### 10. Health Monitoring

#### Health Check Implementation

```typescript
interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  responseTime: number;
  version?: string;
}

async healthCheck(): Promise<HealthResponse> {
  const startTime = Date.now();
  
  try {
    const response = await this.makeRequest('/health', {
      method: 'GET',
      timeout: 5000
    });
    
    const responseTime = Date.now() - startTime;
    const data = await response.json();
    
    return {
      status: data.status || 'unknown',
      timestamp: data.timestamp || new Date().toISOString(),
      responseTime,
      version: data.version
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      responseTime: Date.now() - startTime
    };
  }
}
```

### 11. Testing Requirements

#### Unit Test Coverage

Clients MUST include tests for:

```typescript
describe('GaiaV03Client', () => {
  describe('chat', () => {
    it('should send basic message and receive response');
    it('should include conversation ID in subsequent messages');
    it('should validate message input');
    it('should handle server errors gracefully');
  });
  
  describe('streamChat', () => {
    it('should stream response chunks');
    it('should handle stream completion');
    it('should handle stream errors');
    it('should clean up resources on abort');
  });
  
  describe('error handling', () => {
    it('should throw ValidationError for invalid input');
    it('should throw AuthenticationError for invalid API key');
    it('should throw RateLimitError with retry-after');
    it('should retry on server errors');
  });
  
  describe('configuration', () => {
    it('should validate configuration on creation');
    it('should use default values appropriately');
    it('should allow configuration updates');
  });
});
```

### 12. Language-Specific Requirements

#### JavaScript/TypeScript

```typescript
// Package exports
export { GaiaV03Client } from './client';
export * from './types';
export * from './errors';

// Browser compatibility
// Must work in: Chrome 80+, Firefox 78+, Safari 14+, Edge 80+

// Node.js compatibility  
// Must work in: Node.js 14+

// Bundle size target: < 50KB minified
```

#### Python

```python
# Package structure
# gaia_client/
#   __init__.py
#   client.py
#   types.py
#   errors.py
#   async_client.py

# Python versions: 3.8+
# Dependencies: httpx, typing_extensions (if needed)
# Async support: Required

from gaia_client import GaiaV03Client
from gaia_client.async_client import AsyncGaiaV03Client
```

### 13. Performance Requirements

#### Response Time Targets

- **Connection establishment**: < 500ms
- **Non-streaming requests**: < 2s for simple queries
- **Stream initialization**: < 1s
- **Memory usage**: < 50MB for typical usage
- **CPU usage**: < 5% during idle

#### Caching Recommendations

```typescript
interface CacheConfig {
  enableResponseCache?: boolean;
  cacheMaxAge?: number;
  cacheMaxSize?: number;
}

class ResponseCache {
  private cache = new Map<string, CachedResponse>();
  
  get(key: string): ChatResponse | null {
    const cached = this.cache.get(key);
    if (!cached || Date.now() > cached.expiresAt) {
      this.cache.delete(key);
      return null;
    }
    return cached.response;
  }
  
  set(key: string, response: ChatResponse, ttl: number): void {
    this.cache.set(key, {
      response,
      expiresAt: Date.now() + ttl
    });
  }
}
```

### 14. Security Requirements

#### API Key Handling

```typescript
class SecureStorage {
  // NEVER log API keys
  private static redactApiKey(apiKey: string): string {
    if (!apiKey || apiKey.length < 8) return '[REDACTED]';
    return apiKey.slice(0, 4) + '...' + apiKey.slice(-4);
  }
  
  // Validate API key format
  static validateApiKey(apiKey: string): boolean {
    return /^[A-Za-z0-9_-]{20,}$/.test(apiKey);
  }
}
```

#### Request Security

- **TLS 1.2+**: All requests must use HTTPS
- **Certificate validation**: Must verify server certificates
- **Timeout enforcement**: All requests must have timeouts
- **Input sanitization**: Validate all user inputs
- **No credential logging**: Never log API keys or tokens

### 15. Documentation Requirements

Each client library MUST include:

1. **README.md** - Installation, quick start, examples
2. **API Reference** - Complete method documentation  
3. **Migration Guide** - From other clients/APIs
4. **Examples** - Common use cases and patterns
5. **Changelog** - Version history and breaking changes
6. **Contributing Guide** - Development setup and guidelines

### 16. Version Compatibility

#### Semantic Versioning

- **Major version**: Breaking API changes
- **Minor version**: New features, backward compatible
- **Patch version**: Bug fixes, backward compatible

#### API Version Support

- **Current**: v0.3 (full support)
- **Legacy**: v1 (compatibility mode)
- **Deprecated**: v0.2 (removed)

### 17. Release Checklist

Before releasing a new client version:

- [ ] All unit tests pass
- [ ] Integration tests pass against staging API
- [ ] Performance benchmarks meet requirements
- [ ] Documentation is updated
- [ ] Examples work with new version
- [ ] Security review completed
- [ ] Breaking changes documented
- [ ] Migration guide updated (if needed)

---

## Implementation Examples

### Minimal JavaScript Implementation

```javascript
class SimpleGaiaClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseUrl = 'https://api.gaia-platform.com';
  }
  
  async chat(message, conversationId = null) {
    const response = await fetch(`${this.baseUrl}/api/v0.3/chat`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        stream: false
      })
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
  }
}
```

### Minimal Python Implementation

```python
import httpx
import json

class SimpleGaiaClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.gaia-platform.com"
    
    def chat(self, message: str, conversation_id: str = None) -> dict:
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": message,
            "stream": False
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        response = httpx.post(
            f"{self.base_url}/api/v0.3/chat",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        
        response.raise_for_status()
        return response.json()
```

This specification provides a comprehensive guide for implementing robust, consistent GAIA v0.3 API clients across all programming languages and platforms.