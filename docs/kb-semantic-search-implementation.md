# KB Semantic Search Implementation Guide

## Overview
Semantic search for the GAIA Knowledge Base using the aifs library with ChromaDB for vector embeddings.

## Key Features
- ✅ Natural language search across KB content
- ✅ Namespace-aware indexing (user/team isolation)
- ✅ Non-blocking background indexing
- ✅ Progress monitoring
- ✅ Persistent index caching
- ✅ Redis result caching

## Architecture

### Components
1. **aifs library** - Handles document chunking and embedding generation
2. **ChromaDB** - Vector database for semantic similarity search
3. **Background indexer** - Non-blocking indexing with progress tracking
4. **Redis cache** - Caches search results with TTL

### Index Files
- Location: `{namespace}/_.aifs` (e.g., `/kb/_.aifs`)
- Format: JSON with embeddings and document chunks
- Persistence: Survives container restarts
- Size: ~2.6MB for 76 files

## API Endpoints

### Search
```
POST /search/semantic
{
  "message": "your natural language query"
}
```

Returns semantically similar documents with relevance scores.

### Monitor Progress
```
GET /search/semantic/progress/{namespace}
```

Returns:
```json
{
  "status": "indexing|ready|not_indexed",
  "indexed": true/false,
  "total_files": 76,
  "elapsed_seconds": 45.2,
  "index_size": 2646047,
  "message": "Status message"
}
```

### Reindex
```
POST /search/semantic/reindex
```

Forces reindexing of namespace.

### Statistics
```
GET /search/semantic/stats
```

Returns indexing queue size and status.

## Configuration

### Environment Variables
```bash
# Enable semantic search
KB_SEMANTIC_SEARCH_ENABLED=true

# Cache TTL in seconds (default: 3600)
KB_SEMANTIC_CACHE_TTL=3600

# KB path
KB_PATH=/kb
```

### Docker Requirements
The following system packages are required in Dockerfile.kb:
```dockerfile
RUN apt-get update && apt-get install -y \
    poppler-utils \      # PDF processing
    tesseract-ocr \      # OCR support
    libmagic-dev \       # File type detection
    qpdf                 # PDF manipulation
```

## Bug Fixes Applied

### 1. aifs JSON Serialization Bug
**Problem**: aifs was trying to serialize numpy arrays directly to JSON
**Solution**: Convert numpy arrays to lists before serialization
```python
if embeddings and hasattr(embeddings[0], 'tolist'):
    embeddings = [emb.tolist() for emb in embeddings]
```

### 2. Missing File Metadata
**Problem**: aifs only returned text chunks without source file information
**Solution**: Modified aifs to return both content and source
```python
results_with_sources.append({
    "content": doc,
    "source": source_file
})
```

## Non-Blocking Implementation

### How It Works
1. Check if index exists (`_.aifs` file)
2. If not, queue indexing task and return immediately
3. Background worker processes indexing queue
4. User gets "indexing in progress" response
5. Subsequent searches work once index is ready

### Performance
- Small namespaces (3-5 files): Index in seconds
- Medium namespaces (20-40 files): 1-2 minutes
- Large namespaces (70+ files): 5-10 minutes
- Search response (indexed): <1 second
- Search response (not indexed): Returns immediately with "indexing" status

## Monitoring Indexing Progress

### Real-time Progress
The `/search/semantic/progress/{namespace}` endpoint provides:
- Current status (indexing, ready, not_indexed)
- Number of files being processed
- Time elapsed
- Estimated time per file
- Final index size when complete

### Example Monitoring Script
```bash
#!/bin/bash
NAMESPACE="root"
API_KEY="your-key"

while true; do
  STATUS=$(curl -s -H "X-API-Key: $API_KEY" \
    "http://localhost:8001/search/semantic/progress/$NAMESPACE" | jq -r '.status')
  
  if [ "$STATUS" = "ready" ]; then
    echo "Indexing complete!"
    break
  fi
  
  echo "Status: $STATUS"
  sleep 5
done
```

## Troubleshooting

### Index Not Creating
- Check CPU usage: `docker stats kb-service`
- Check logs: `docker compose logs kb-service`
- Verify aifs is installed: `pip list | grep aifs`

### Slow Indexing
- Normal for large directories (70+ files)
- CPU should be at 90-100% during indexing
- Memory usage increases during indexing
- Consider breaking into smaller namespaces

### Search Returns No Results
1. Check index exists: `ls -la /kb/_.aifs`
2. Verify index is valid JSON
3. Check namespace path is correct
4. Review logs for errors

## Best Practices

### 1. Pre-index Before Deployment
```bash
# Index during build or deployment
docker compose exec kb-service python3 -c "
from aifs import search
search('', path='/kb')  # Triggers indexing
"
```

### 2. Use Namespaces for Large KBs
Break content into logical namespaces:
- `/kb/users/{email}/` - User content
- `/kb/teams/{team}/` - Team content
- `/kb/shared/` - Shared content

### 3. Monitor Background Indexing
Always check progress endpoint after triggering indexing.

### 4. Cache Warming
After deployment, trigger common searches to warm Redis cache.

## Future Improvements

### Potential Enhancements
1. Incremental indexing (only reindex changed files)
2. Distributed indexing across multiple workers
3. WebSocket notifications for indexing progress
4. Search result snippets with highlighting
5. Relevance feedback and tuning
6. Multi-language support

### Known Limitations
- aifs indexes entire directory (no incremental updates)
- Large directories (100+ files) can take 10+ minutes
- No search within specific file types
- Limited to markdown and text files primarily