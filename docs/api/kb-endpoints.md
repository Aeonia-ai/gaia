# 📚 Knowledge Base (KB) API Endpoints

📍 **Location:** [Home](../README.md) → [API](README.md) → KB Endpoints

## Overview

The KB service provides comprehensive knowledge base management through 25+ REST endpoints. All endpoints require authentication via API key or JWT token.

## 🔍 **Core KB Operations**

### Search Operations
#### `POST /api/v0.2/kb/search`
Fast full-text search using ripgrep for high-performance document retrieval.

**Request:**
```json
{
  "query": "search terms",
  "max_results": 50,
  "include_content": true
}
```

**Response:**
```json
{
  "results": [
    {
      "file_path": "documents/example.md", 
      "matches": ["line with search terms"],
      "score": 0.95
    }
  ],
  "total_results": 42,
  "search_time_ms": 14
}
```

### Document Operations
#### `POST /api/v0.2/kb/read`
Read a specific document by path.

**Request:**
```json
{
  "file_path": "documents/example.md"
}
```

**Response:**
```json
{
  "content": "Document content here...",
  "metadata": {
    "size": 1024,
    "modified": "2025-07-26T10:30:00Z"
  }
}
```

#### `POST /api/v0.2/kb/write`
Create or update a document.

**Request:**
```json
{
  "file_path": "documents/new-doc.md",
  "content": "# New Document\n\nContent here...",
  "create_dirs": true
}
```

**Response:**
```json
{
  "success": true,
  "file_path": "documents/new-doc.md",
  "bytes_written": 256
}
```

#### `DELETE /api/v0.2/kb/delete`
Delete a document from the KB.

**Request:**
```json
{
  "file_path": "documents/old-doc.md"
}
```

**Response:**
```json
{
  "success": true,
  "deleted_path": "documents/old-doc.md"
}
```

#### `POST /api/v0.2/kb/move`
Move or rename a document.

**Request:**
```json
{
  "source_path": "documents/old-name.md",
  "dest_path": "documents/new-name.md"
}
```

**Response:**
```json
{
  "success": true,
  "source_path": "documents/old-name.md",
  "dest_path": "documents/new-name.md"
}
```

## 🗂️ **Navigation & Context**

#### `POST /api/v0.2/kb/context`
Load a KOS context by name.

**Request:**
```json
{
  "context_name": "development"
}
```

#### `POST /api/v0.2/kb/navigate`
Navigate KB using the manual index system.

**Request:**
```json
{
  "path": "engineering/architecture"
}
```

#### `POST /api/v0.2/kb/list`
List files in a KB directory.

**Request:**
```json
{
  "directory": "documents/",
  "recursive": false
}
```

**Response:**
```json
{
  "files": [
    {
      "name": "example.md",
      "path": "documents/example.md",
      "size": 1024,
      "modified": "2025-07-26T10:30:00Z"
    }
  ],
  "directories": ["subdirectory/"]
}
```

## 🔄 **Git Integration**

#### `GET /api/v0.2/kb/git/status`
Get the current Git status of the KB repository.

**Response:**
```json
{
  "branch": "main",
  "status": "clean",
  "ahead": 0,
  "behind": 0,
  "modified_files": [],
  "untracked_files": []
}
```

#### `POST /sync/from-git` (Hybrid Mode)
Synchronize KB from Git repository.

#### `POST /sync/to-git` (Hybrid Mode)  
Push KB changes to Git repository.

#### `GET /sync/status` (Hybrid Mode)
Get synchronization status.

## ⚡ **Cache Management**

#### `GET /api/v0.2/kb/cache/stats`
Get KB cache statistics.

**Response:**
```json
{
  "cache_hits": 1250,
  "cache_misses": 89,
  "hit_ratio": 0.93,
  "total_entries": 456,
  "memory_usage_mb": 12.4
}
```

#### `POST /api/v0.2/kb/cache/invalidate`
Invalidate KB cache entries.

**Request:**
```json
{
  "pattern": "documents/*.md"
}
```

## 🔍 **Health & Monitoring**

#### `GET /api/v0.2/kb/health`
Get KB service health status.

**Response:**
```json
{
  "status": "healthy",
  "storage_mode": "hybrid",
  "git_repository": "connected",
  "database": "operational",
  "cache": "active",
  "uptime_seconds": 3600
}
```

## 🤖 **AI-Enhanced Chat Integration**

The KB service is **automatically integrated** with the intelligent chat routing system. Users don't need to call KB endpoints directly - they can use natural language with the unified chat endpoint:

### **Automatic KB Integration via Chat**

#### `POST /api/v1/chat` (Recommended)
**Unified chat endpoint with automatic KB integration**

```bash
# KB search via natural language
curl -X POST https://gaia-gateway-dev.fly.dev/api/v1/chat \
  -H "Authorization: Bearer $JWT" \
  -d '{"message": "Search my notes about GAIA architecture"}'

# Context loading
curl -X POST https://gaia-gateway-dev.fly.dev/api/v1/chat \
  -H "Authorization: Bearer $JWT" \
  -d '{"message": "Continue where we left off"}'

# File reading  
curl -X POST https://gaia-gateway-dev.fly.dev/api/v1/chat \
  -H "Authorization: Bearer $JWT" \
  -d '{"message": "Show me the contents of docs/architecture.md"}'
```

**How it works:**
1. Intelligent router detects KB-related requests
2. Automatically provides KB tools to LLM
3. LLM calls appropriate KB functions
4. Results formatted into natural response

### **KB Tools Available to Chat**
- `search_knowledge_base` - Full-text search
- `load_kos_context` - KOS context loading  
- `read_kb_file` - File reading
- `list_kb_directory` - Directory listing
- `synthesize_kb_information` - Cross-domain synthesis

## 🔐 **Authentication**

All KB endpoints require authentication:

**API Key Authentication:**
```bash
curl -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"query": "search terms"}' \
     https://api.gaia.com/api/v0.2/kb/search
```

**JWT Authentication:**
```bash
curl -H "Authorization: Bearer your-jwt-token" \
     -H "Content-Type: application/json" \
     -d '{"query": "search terms"}' \
     https://api.gaia.com/api/v0.2/kb/search
```

## 📊 **Performance Metrics**

- **Search Performance**: 14ms average (PostgreSQL mode)
- **File Operations**: Sub-100ms for standard documents
- **Cache Hit Ratio**: 93%+ typical performance
- **Concurrent Users**: Supports multi-user access with RBAC
- **Storage Modes**: Git (simple), Database (fast), Hybrid (best of both)

## 🛠️ **Storage Modes**

### Git Mode
- Files stored directly in Git repository
- Version control built-in
- Simple setup, good for small teams

### Database Mode  
- Files stored in PostgreSQL
- 79x faster search performance
- Advanced querying and analytics

### Hybrid Mode (Recommended)
- PostgreSQL for performance + Git for backup
- Best of both worlds
- Production recommended

## 🔗 **See Also**

- **[KB Service Guide](../current/kb/)** - Complete KB setup and configuration
- **[Authentication Guide](../current/authentication/)** - API key and JWT setup
- **[Multi-User Setup](../current/kb/multi-user-kb-guide.md)** - Team and RBAC configuration
- **[Git Integration](../current/kb/kb-git-sync-guide.md)** - Repository synchronization

---

**Status**: ✅ **FULLY OPERATIONAL** - All endpoints implemented and tested  
**Version**: v0.2 (stable), v1 (enhanced with AI)  
**Authentication**: Required for all endpoints