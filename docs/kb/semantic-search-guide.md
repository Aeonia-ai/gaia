# KB Semantic Search Guide

## Overview

The GAIA Knowledge Base now supports **semantic search** - an AI-powered natural language search capability that goes beyond traditional keyword matching. Using the `aifs` library and local embeddings, semantic search understands the meaning and context of your queries.

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
- Indexes are stored as `_.aifs` files within each namespace directory
- Complete privacy and security between different users' content

### Incremental Updates
- Automatic reindexing when files are added, modified, or deleted
- Git sync triggers reindexing for changed files
- Manual reindexing available via API endpoint

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
- `aifs>=0.0.16` - Core semantic search library
- `chromadb>=0.4.22` - Vector database (required by aifs but not declared as its dependency)
- `unstructured[all-docs]>=0.10.0` - Document parsing for various formats

**Important Note**: The aifs package has a bug where it doesn't declare ChromaDB as a dependency. We explicitly install ChromaDB in our requirements.txt to ensure semantic search works properly.

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

### ChromaDB Integration

**Optimized Implementation** (GAIA Platform):
- Uses a **singleton ChromaDB manager** that persists across requests
- Collections are cached per namespace to avoid recreation overhead
- Embeddings stay in memory between searches (3x faster than recreating)
- Similar to our MCP-Agent hot loading pattern

**How it works**:
- `chromadb.Client()` creates an in-memory database (ephemeral mode)
- No separate ChromaDB server is needed
- Embeddings are computed in-process using ONNX models
- The embedding model (all-MiniLM-L6-v2) is cached locally in `~/.cache/chroma/`

### Indexing Process

1. **Initial Indexing**: When semantic search is first enabled, namespaces are indexed in the background
2. **File Parsing**: Documents are parsed and chunked semantically based on file type  
3. **Embedding Generation**: Text chunks are converted to vector embeddings using ChromaDB's embedded model
4. **Index Storage**: Embeddings are stored in `_.aifs` files (Git-ignored) for persistence

### Search Process

1. **Query Embedding**: Your natural language query is converted to a vector
2. **Similarity Search**: The system finds the most similar document chunks
3. **Result Ranking**: Results are ranked by relevance score (0-1)
4. **Caching**: Results are cached in Redis for faster repeated searches

### Automatic Reindexing Triggers

- **Git Sync**: When pulling changes from Git repository
- **File Operations**: When files are created, updated, or deleted via API
- **Manual Trigger**: Via the `/search/semantic/reindex` endpoint

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
- First-time indexing may take 30 seconds to several minutes depending on content size
- Indexing happens in the background without blocking service startup
- The service returns "indexing" status while processing

### Search Performance
- First search after indexing: 1-3 seconds
- Subsequent searches (cached): < 100ms
- Cache TTL: 1 hour by default

### Storage Requirements
- Index files (_.aifs) typically 10-20% of original content size
- Stored within namespace directories
- Never committed to Git (included in .gitignore)

### Memory Usage
- Embeddings are loaded into memory during search
- Memory usage scales with index size
- Monitor with `/search/semantic/stats` endpoint

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
- **aifs**: Local semantic search library
- **ChromaDB**: Embedded vector database (runs in-memory, no server needed)
- **ONNX Runtime**: Powers the all-MiniLM-L6-v2 embedding model
- **Unstructured**: Document parsing and chunking
- **Redis**: Result caching

### File Types Supported

#### Standard Build (Dockerfile.kb)
Full support for:
- Markdown (`.md`)
- Text (`.txt`)
- YAML (`.yml`, `.yaml`)
- JSON (`.json`)
- PDF (`.pdf`) - including OCR for scanned PDFs
- HTML (`.html`)
- Images with text (`.jpg`, `.png`) - OCR extraction

Limited/No support for (requires Dockerfile.kb.full):
- Word Documents (`.docx`) - requires LibreOffice
- PowerPoint (`.pptx`) - requires LibreOffice
- Excel (`.xlsx`) - requires LibreOffice
- RTF, EPUB, Open Office - requires pandoc

#### Full Build (Dockerfile.kb.full)
Complete support for all document types including Office formats.
Note: This build is ~2GB vs ~500MB for the standard build.

### Security & Privacy
- Complete namespace isolation
- No cross-namespace search possible
- Indexes never leave your infrastructure
- Git-ignored to prevent accidental commits

## Future Enhancements

### Planned Features
1. **Hybrid Search**: Combine semantic and keyword search
2. **Query Expansion**: Automatically expand queries with synonyms
3. **Feedback Loop**: Learn from user interactions
4. **Custom Embeddings**: Support for domain-specific models
5. **Similarity Threshold**: Configurable minimum relevance scores

### API Evolution
- `/search/hybrid` - Combined semantic + keyword search
- `/search/similar` - Find documents similar to a given document
- `/search/explain` - Explain why results matched

## Migration Guide

### Enabling Semantic Search

1. **Update environment variables**:
   ```bash
   KB_SEMANTIC_SEARCH_ENABLED=true
   ```

2. **Restart KB service**:
   ```bash
   docker compose restart kb-service
   ```

3. **Initial indexing** (automatic):
   - Service starts immediately (non-blocking)
   - Background indexing begins
   - Check status: `GET /search/semantic/stats`

4. **Start searching**:
   - Use `/search/semantic` endpoint
   - Natural language queries work immediately
   - Results improve as indexing completes

### Rollback Procedure

If you need to disable semantic search:

1. **Update environment**:
   ```bash
   KB_SEMANTIC_SEARCH_ENABLED=false
   ```

2. **Restart service**:
   ```bash
   docker compose restart kb-service
   ```

3. **Clean up indexes** (optional):
   ```bash
   find /kb -name "_.aifs" -delete
   find /kb -name ".aifs" -type d -exec rm -rf {} +
   ```

## Support

For issues or questions about semantic search:
1. Check the stats endpoint for indexing status
2. Review logs: `docker compose logs kb-service`
3. Try manual reindexing
4. Contact the development team with specific error messages