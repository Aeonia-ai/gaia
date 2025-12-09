# KB Semantic Search Guide

## Overview

The GAIA Knowledge Base supports **semantic search** - an AI-powered natural language search capability that goes beyond traditional keyword matching. Using **pgvector** (PostgreSQL extension) with **sentence-transformers**, semantic search understands the meaning and context of your queries with persistent, incremental indexing.

## Key Features

### Natural Language Queries
Instead of searching for exact keywords, you can ask questions naturally:
- ❌ Traditional: `authentication JWT token`
- ✅ Semantic: `how do users log in to the system?`

### Conceptual Matching
Semantic search finds related content even when exact words don't match:
- Query: `"user authentication process"`
- Finds: Documents about login, sessions, JWT tokens, OAuth, security

### Namespace Isolation
- Each user/team/workspace has its own isolated semantic index
- Indexes stored in PostgreSQL with namespace column for isolation
- Complete privacy and security between different users' content

### Persistent Storage
- **No re-indexing on restart** - indexes persist in PostgreSQL database
- Survives container restarts and deployments
- Transactional consistency with ACID guarantees

### Incremental Updates
- **Smart mtime comparison** - only reindexes files that changed
- 60-second tolerance handles Docker volume mount delays
- Git sync automatically triggers incremental reindexing
- Manual reindexing available via MCP tool or API endpoint

### New Content Detection

The semantic indexing system automatically detects and processes new KB content through:

**Automatic Detection Mechanism:**
- **File modification time (mtime) tracking** - Each file's last modification time is stored in `kb_semantic_index_metadata` table
- **60-second tolerance** - Files are reindexed if mtime differs by more than 60 seconds (handles Docker volume sync delays)
- **Incremental processing** - Only changed files are reindexed, not the entire knowledge base
- **Background indexing** - Happens during deferred initialization after service startup

**How It Works:**
1. Service startup triggers background indexing task
2. System scans all `.md` files in KB namespaces
3. Compares current file mtime with stored mtime from database
4. Files with mtime differences >60s are queued for reindexing
5. New embeddings are generated and stored in PostgreSQL

**Verification:**
- Check service logs: `docker logs gaia-kb-docs-1 --tail 20`
- Search for recently added content to test indexing
- Indexing status appears in search metadata: `"indexing_status": "ready"`

### High Performance
- **HNSW indexing** for sub-second vector similarity searches
- 384-dimensional embeddings (all-MiniLM-L6-v2 model)
- Cosine distance similarity scoring (0.0-1.0 relevance)

## Configuration

### Environment Variables

```bash
# Enable semantic search (default: false)
KB_SEMANTIC_SEARCH_ENABLED=true

# Cache TTL for search results in seconds (default: 3600)
KB_SEMANTIC_CACHE_TTL=3600
```

### Dependencies

The following are automatically installed with the KB service:
- `pgvector>=0.2.4` - PostgreSQL extension for vector similarity search
- `sentence-transformers>=2.2.2` - Embedding model (all-MiniLM-L6-v2)
- `asyncpg>=0.29.0` - Async PostgreSQL driver with pgvector support

**Database Requirements**:
- PostgreSQL 12+ with pgvector extension enabled
- Docker image: `pgvector/pgvector:pg15` (includes extension pre-installed)

## API Endpoints

### 1. Semantic Search
**POST** `/search/semantic`

Perform a natural language search within your namespace.

```json
{
  "message": "how do users authenticate with the API?"
}
```

**Response:**
```json
{
  "status": "success",
  "response": "🧠 **Semantic Search Results...**",
  "metadata": {
    "search_type": "semantic",
    "total_results": 5,
    "indexing_status": "ready"
  }
}
```

### 2. Manual Reindex
**POST** `/search/semantic/reindex`

Trigger reindexing of your namespace (or specific namespace for admins).

```json
{
  "namespace": "users/john@example.com"  // Optional, admin only
}
```

### 3. Search Statistics
**GET** `/search/semantic/stats`

Get indexing status and statistics for your namespace.

**Response:**
```json
{
  "status": "success",
  "enabled": true,
  "statistics": {
    "indexing_queue_size": 0,
    "namespace": "users/john@example.com",
    "indexed": true,
    "cache_ttl_seconds": 3600
  }
}
```

## How It Works

### pgvector Integration

**Architecture** (GAIA Platform):
- Uses **PostgreSQL with pgvector extension** for native vector storage
- HNSW indexes enable sub-second similarity searches
- sentence-transformers generates 384-dimensional embeddings
- asyncpg with explicit vector type registration for Python ↔ PostgreSQL conversion

**How it works**:
- Files are chunked into semantic segments (paragraphs)
- Each chunk is converted to a 384-dimensional vector using all-MiniLM-L6-v2
- Vectors stored in PostgreSQL with `vector(384)` data type
- HNSW index enables fast cosine distance similarity searches
- Query embeddings compared against stored vectors for relevant matches

### Indexing Process

1. **File Discovery**: System scans namespace directory for markdown files
2. **Incremental Check**: Compares file mtime against stored metadata (60s tolerance)
3. **File Chunking**: Changed files split into semantic paragraphs (50+ chars minimum)
4. **Embedding Generation**: sentence-transformers converts chunks to 384-dim vectors
5. **Database Storage**: Vectors inserted into PostgreSQL with chunk text and metadata
6. **HNSW Indexing**: PostgreSQL builds/updates HNSW index for fast similarity search

### Search Process

1. **Query Embedding**: Your natural language query is converted to a 384-dim vector
2. **Vector Similarity**: PostgreSQL uses HNSW index to find nearest vectors (cosine distance)
3. **Result Ranking**: Results ranked by similarity score (0.0-1.0, higher is more relevant)
4. **Result Formatting**: Chunks returned with source file paths and relevance scores

### Automatic Reindexing Triggers

- **Startup**: Incremental indexing checks all files, only indexes changed ones
- **Git Sync**: When pulling changes from Git repository (mtime changes detected)
- **File Operations**: When files are created, updated, or deleted via API
- **Manual Trigger**: Via the `search_semantic` MCP tool (reindex parameter)

## Usage Examples

### Example 1: Finding Authentication Documentation

```bash
# Traditional keyword search
curl -X POST http://localhost:8000/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "JWT token authentication"}'

# Semantic search - more natural
curl -X POST http://localhost:8000/search/semantic \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "How do users log in to the system?"}'
```

### Example 2: Finding Related Concepts

```bash
# Query about error handling
curl -X POST http://localhost:8000/search/semantic \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "What happens when something goes wrong?"}'

# Finds documents about:
# - Error handling
# - Exception management
# - Logging systems
# - Debugging guides
# - Troubleshooting docs
```

### Example 3: Checking Index Status

```bash
# Check if your namespace is indexed
curl -X GET http://localhost:8000/search/semantic/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Example 4: Force Reindexing

```bash
# Reindex your namespace
curl -X POST http://localhost:8000/search/semantic/reindex \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Performance Considerations

### Initial Indexing
- First-time indexing: Depends on content size (1,825 files = ~80 minutes)
- Subsequent startups: Only changed files indexed (typically < 1 minute)
- Incremental mtime checking prevents unnecessary reindexing
- Background processing doesn't block service startup

### Search Performance
- HNSW index enables sub-second searches even with 50,000+ chunks
- Query embedding generation: ~50-100ms
- Vector similarity search: < 100ms (HNSW optimized)
- Total search time: ~200-500ms per query

### Storage Requirements
- **Metadata table**: Small (file paths, mtime, chunk counts)
- **Chunks table**: ~50KB per 1000 chunks (includes embeddings)
- **Indexes**: HNSW index ~20% overhead on embedding storage
- Example: 55,681 chunks ≈ 2.8MB stored embeddings + 560KB HNSW index

### Memory Usage
- sentence-transformers model: ~100MB (loaded once, kept in memory)
- Embeddings in PostgreSQL, not application memory
- asyncpg connection pool: configurable (default: 10 connections)

## Best Practices

### 1. Query Formulation
- Use natural language questions
- Be specific about what you're looking for
- Include context when helpful

### 2. Index Management
- Let automatic indexing handle most cases
- Manual reindex after bulk changes
- Monitor indexing queue via stats endpoint

### 3. Combining Search Types
- Use traditional `/search` for exact matches
- Use `/search/semantic` for conceptual queries
- Future: `/search/hybrid` will combine both

## Troubleshooting

### "Namespace is being indexed"
- **Cause**: Initial indexing in progress
- **Solution**: Wait a few moments and retry
- **Check status**: Use `/search/semantic/stats`

### No Results Found
- **Cause**: Index may be outdated or query too vague
- **Solution**: 
  1. Trigger reindex with `/search/semantic/reindex`
  2. Refine your query with more specific terms
  3. Check traditional search to verify content exists

### Slow Search Performance
- **Cause**: Large namespace, no cache, or first search
- **Solution**:
  1. Ensure Redis is running for caching
  2. Consider splitting large namespaces
  3. Warm cache with common queries

## Architecture Details

### Technology Stack
- **pgvector**: PostgreSQL extension for vector similarity search
- **sentence-transformers**: Embedding generation (all-MiniLM-L6-v2 model)
- **asyncpg**: Async PostgreSQL driver with pgvector type support
- **PostgreSQL HNSW**: Fast approximate nearest neighbor search
- **Redis**: Result caching (future enhancement)

### File Types Supported

Currently indexes:
- **Markdown (`.md`)** - Primary file type, best performance
- Future: Text, YAML, JSON, code files

**Why only markdown?**
- Markdown is the standard for documentation and knowledge bases
- Simple text chunking works reliably for markdown structure
- Can easily extend to other text formats when needed

**Not supported yet:**
- Binary formats (PDF, Word, etc.) - would require additional parsing
- Code files - would benefit from AST-based chunking (future enhancement)

### Security & Privacy
- Complete namespace isolation via PostgreSQL row-level filtering
- No cross-namespace search possible (enforced at query level)
- Indexes stored in your database infrastructure
- ACID transactional guarantees prevent data corruption
- pgvector extension is open-source and auditable

## Future Enhancements

### Planned Features
1. **Embedding Caching**: Cache query embeddings for frequently searched terms
2. **Hybrid Search**: Combine pgvector semantic + ripgrep keyword search
3. **Multi-file format support**: Extend beyond markdown to code, YAML, JSON
4. **Better chunking**: AST-aware chunking for code files
5. **Similarity Threshold**: Configurable minimum relevance scores
6. **Re-ranking**: Two-stage search with initial retrieval + LLM re-ranking

### Performance Improvements
- **Batch indexing**: Index multiple files in single database transaction
- **Parallel embedding generation**: Use multiple CPU cores for faster indexing
- **IVF index option**: For very large datasets (>1M vectors)
- **Quantization**: Reduce embedding size with minimal accuracy loss

## Migration Guide

### Enabling Semantic Search (New Installation)

1. **Apply database migrations**:
   ```bash
   docker exec gaia-db-1 psql -U postgres -d llm_platform -f migrations/006_create_semantic_search_metadata_tables.sql
   docker exec gaia-db-1 psql -U postgres -d llm_platform -f migrations/007_add_pgvector_embeddings.sql
   ```

2. **Update environment variables**:
   ```bash
   KB_SEMANTIC_SEARCH_ENABLED=true
   ```

3. **Rebuild and restart KB service** (to install sentence-transformers):
   ```bash
   docker compose build kb-docs
   docker compose up -d kb-docs
   ```

4. **Monitor initial indexing**:
   ```bash
   # Watch logs
   docker compose logs -f kb-docs

   # Check if indexing complete
   curl http://localhost:8005/health
   ```

5. **Test semantic search**:
   ```bash
   # Via REST API
   curl -X POST http://localhost:8005/search \
     -H "Content-Type: application/json" \
     -d '{"message":"your search query"}'

   # Via MCP (in Claude Code)
   # search_semantic tool will be available
   ```

### Rollback Procedure

If you need to disable semantic search:

1. **Update environment**:
   ```bash
   KB_SEMANTIC_SEARCH_ENABLED=false
   ```

2. **Restart service**:
   ```bash
   docker compose restart kb-docs
   ```

3. **Optionally drop pgvector data** (frees up space):
   ```sql
   -- Keeps tables but removes data
   TRUNCATE kb_semantic_index_metadata, kb_semantic_chunk_ids;

   -- Or completely remove (requires re-running migrations to re-enable)
   DROP TABLE kb_semantic_chunk_ids;
   DROP TABLE kb_semantic_index_metadata;
   ```

## Support

For issues or questions about semantic search:
1. Check the stats endpoint for indexing status
2. Review logs: `docker compose logs kb-service`
3. Try manual reindexing
4. Contact the development team with specific error messages