# KB Semantic Search Implementation Guide (pgvector)

## Overview
Semantic search for the GAIA Knowledge Base using **pgvector** (PostgreSQL extension) with **sentence-transformers** for vector embeddings.

## Key Features
- ✅ Natural language search across KB content
- ✅ Namespace-aware indexing (user/team isolation)
- ✅ Persistent storage in PostgreSQL (survives restarts)
- ✅ Incremental indexing (only changed files)
- ✅ HNSW indexes for sub-second searches
- ✅ MCP tool integration for Claude Code

## Architecture

### Components
1. **pgvector** - PostgreSQL extension for vector similarity search
2. **sentence-transformers** - Embedding generation (all-MiniLM-L6-v2 model)
3. **asyncpg** - Async PostgreSQL driver with vector type support
4. **Background indexer** - Non-blocking incremental indexing
5. **HNSW indexes** - Fast approximate nearest neighbor search

### Database Schema

**Table: kb_semantic_index_metadata**
```sql
CREATE TABLE kb_semantic_index_metadata (
    id SERIAL PRIMARY KEY,
    relative_path TEXT NOT NULL,
    namespace TEXT NOT NULL,
    mtime DOUBLE PRECISION NOT NULL,
    num_chunks INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding vector(384),  -- Document-level embedding (optional)
    UNIQUE(relative_path, namespace)
);

CREATE INDEX idx_semantic_namespace ON kb_semantic_index_metadata(namespace);
CREATE INDEX idx_semantic_mtime ON kb_semantic_index_metadata(mtime);
```

**Table: kb_semantic_chunk_ids**
```sql
CREATE TABLE kb_semantic_chunk_ids (
    id SERIAL PRIMARY KEY,
    relative_path TEXT NOT NULL,
    chunk_id TEXT NOT NULL UNIQUE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (relative_path) REFERENCES kb_semantic_index_metadata(relative_path) ON DELETE CASCADE
);

-- HNSW index for fast vector similarity search
CREATE INDEX idx_chunk_embedding_hnsw
ON kb_semantic_chunk_ids
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**HNSW Parameters**:
- `m = 16` - Number of connections per node (balance between speed and accuracy)
- `ef_construction = 64` - Build quality (higher = better quality, slower build)
- `vector_cosine_ops` - Cosine distance for similarity (0 = identical, 2 = opposite)

## Implementation Details

### File: `app/services/kb/kb_semantic_search.py`

**Key Classes**:

```python
class SemanticSearchIndexer:
    """Manages pgvector semantic search indexing and querying"""

    def __init__(self, kb_path: Path, db_pool: asyncpg.Pool):
        self.kb_path = kb_path
        self.db = db_pool
        self.model = None  # Lazy-loaded sentence-transformers model
        self.indexing_lock = asyncio.Lock()

    async def initialize(self):
        """Initialize sentence-transformers model (lazy load)"""
        if not self.model:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("sentence-transformers model loaded")

    async def index_path(self, path: Path, namespace: str):
        """Index all markdown files in path (incremental)"""
        async with self.indexing_lock:
            await self._run_pgvector_index(path, namespace)

    async def search_semantic(self, query: str, namespace: str, limit: int = 10):
        """Search using pgvector cosine similarity"""
        await self.initialize()

        # Generate query embedding
        query_embedding = self.model.encode(query).tolist()

        # Search using pgvector
        async with self.db.acquire() as conn:
            await register_vector(conn)  # Required for asyncpg

            results = await conn.fetch("""
                SELECT
                    c.chunk_text,
                    c.relative_path,
                    m.namespace,
                    1 - (c.embedding <=> $1::vector) AS similarity
                FROM kb_semantic_chunk_ids c
                JOIN kb_semantic_index_metadata m
                    ON c.relative_path = m.relative_path
                WHERE m.namespace = $2
                ORDER BY c.embedding <=> $1::vector
                LIMIT $3
            """, query_embedding, namespace, limit)

        return [
            {
                "content": r['chunk_text'],
                "source": r['relative_path'],
                "similarity": float(r['similarity'])
            }
            for r in results
        ]
```

**Incremental Indexing Logic**:

```python
async def _run_pgvector_index(self, path: Path, namespace: str):
    """Index with incremental mtime checking"""
    await self.initialize()

    # Get existing file metadata
    async with self.db.acquire() as conn:
        rows = await conn.fetch("""
            SELECT relative_path, mtime, num_chunks
            FROM kb_semantic_index_metadata
            WHERE namespace = $1
        """, namespace)

    existing_metadata = {
        r['relative_path']: (r['mtime'], r['num_chunks'])
        for r in rows
    }

    # Process markdown files
    md_files = list(path.rglob("*.md"))
    files_indexed = 0
    files_skipped = 0
    total_chunks = 0

    for md_file in md_files:
        relative_path = str(md_file.relative_to(path))
        file_mtime = md_file.stat().st_mtime

        # Check if file changed (60s tolerance for Docker volumes)
        if relative_path in existing_metadata:
            stored_mtime, _ = existing_metadata[relative_path]
            mtime_diff = abs(file_mtime - stored_mtime)

            if mtime_diff < 60.0:  # File unchanged
                files_skipped += 1
                continue

        # File changed or new - reindex
        await self._index_single_file(md_file, relative_path, namespace, file_mtime)
        files_indexed += 1

    logger.info(f"Indexed {files_indexed} files, skipped {files_skipped} unchanged")
```

**Single File Indexing**:

```python
async def _index_single_file(self, md_file: Path, relative_path: str,
                              namespace: str, file_mtime: float):
    """Index a single file with chunking and embedding"""

    # Read and chunk file
    content = md_file.read_text(encoding='utf-8')
    chunks = [
        chunk.strip()
        for chunk in content.split('\n\n')
        if chunk.strip() and len(chunk) > 50
    ]

    if not chunks:
        return

    # Generate embeddings
    embeddings = self.model.encode(chunks).tolist()

    # Store in database
    async with self.db.acquire() as conn:
        await register_vector(conn)  # Required for asyncpg

        async with conn.transaction():
            # Delete old chunks if file was previously indexed
            await conn.execute("""
                DELETE FROM kb_semantic_chunk_ids
                WHERE relative_path = $1
            """, relative_path)

            # Insert/update metadata
            await conn.execute("""
                INSERT INTO kb_semantic_index_metadata
                (relative_path, namespace, mtime, num_chunks)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (relative_path, namespace)
                DO UPDATE SET mtime = $3, num_chunks = $4, updated_at = CURRENT_TIMESTAMP
            """, relative_path, namespace, file_mtime, len(chunks))

            # Insert chunks with embeddings
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{namespace}_{relative_path}_{idx}"
                await conn.execute("""
                    INSERT INTO kb_semantic_chunk_ids
                    (relative_path, chunk_id, chunk_index, chunk_text, embedding)
                    VALUES ($1, $2, $3, $4, $5::vector)
                """, relative_path, chunk_id, idx, chunk, embedding)
```

### Critical Implementation Notes

**1. asyncpg Vector Type Registration**

asyncpg requires explicit type registration for pgvector:

```python
from pgvector.asyncpg import register_vector

async with db_pool.acquire() as conn:
    await register_vector(conn)  # REQUIRED for each connection
    # Now can use ::vector cast and vector columns
```

**2. Embedding List Conversion**

sentence-transformers returns numpy arrays, must convert to lists:

```python
# ❌ WRONG - numpy array
embeddings = model.encode(chunks)

# ✅ RIGHT - Python list
embeddings = model.encode(chunks).tolist()
```

**3. Incremental Indexing mtime Tolerance**

Docker volume mounts cause filesystem timestamp discrepancies:

```python
# 60 second tolerance handles Docker sync delays
if abs(file_mtime - stored_mtime) < 60.0:
    skip_file()
```

**4. HNSW vs IVFFlat**

- **HNSW**: Better for < 1M vectors (our use case)
- **IVFFlat**: Better for > 1M vectors, requires training

```sql
-- HNSW (current)
CREATE INDEX USING hnsw (embedding vector_cosine_ops);

-- IVFFlat (alternative for huge datasets)
CREATE INDEX USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## MCP Tool Integration

### File: `app/services/kb/kb_fastmcp_server.py`

```python
@mcp.tool()
async def search_semantic(
    query: str,
    limit: int = 10,
    namespace: str = "root"
) -> Dict[str, Any]:
    """
    Search KB using pgvector semantic search for conceptual/natural language queries.

    Uses sentence transformers to generate embeddings and find semantically similar content
    via vector similarity search (cosine distance) in PostgreSQL with pgvector.

    Args:
        query: Natural language search query (e.g., "how does authentication work?")
        limit: Maximum number of results to return (default: 10)
        namespace: KB namespace to search within (default: "root")

    Returns:
        Search results ranked by semantic similarity with relevance scores

    Example:
        search_semantic(query="chat service architecture", limit=5)
    """
    try:
        from app.services.kb.kb_semantic_search import semantic_indexer

        if not semantic_indexer:
            return {"success": False, "error": "Semantic search not available"}

        result = await semantic_indexer.search_semantic(
            query=query,
            namespace=namespace,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"MCP search_semantic error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

## Performance Characteristics

### Indexing Performance
- **First index**: ~80 minutes for 1,825 files (55,681 chunks)
- **Incremental**: < 1 minute for typical changes (3-5 files)
- **mtime checking**: O(n) file stat calls, very fast
- **Embedding generation**: ~50ms per chunk on CPU

### Search Performance
- **Query embedding**: 50-100ms (sentence-transformers on CPU)
- **Vector search**: < 100ms (HNSW index with 50K+ vectors)
- **Total latency**: 200-500ms per query

### Storage Requirements
- **Embeddings**: ~50KB per 1000 chunks (384 floats × 4 bytes)
- **HNSW index**: ~20% overhead on embedding storage
- **Example**: 55,681 chunks ≈ 2.8MB embeddings + 560KB HNSW index = 3.4MB total

## Troubleshooting

### Indexing Issues

**Problem**: "another operation is in progress"
- **Cause**: Indexing holds database lock
- **Solution**: Wait for indexing to complete, check logs

**Problem**: False positives in incremental indexing (all files re-indexed)
- **Cause**: mtime tolerance too strict
- **Solution**: Increase tolerance in code (currently 60s)

**Problem**: Slow initial indexing
- **Cause**: Normal for large KBs (sentence-transformers on CPU)
- **Solution**: Use GPU for faster embedding generation (future)

### Search Issues

**Problem**: No results for valid query
- **Cause**: Index may be incomplete or query too specific
- **Solution**: Check indexing status, try broader query

**Problem**: Low relevance scores
- **Cause**: Query-document mismatch, different vocabulary
- **Solution**: Rephrase query, use keyword search instead

**Problem**: asyncpg type errors
- **Cause**: Missing `register_vector()` call
- **Solution**: Always call `await register_vector(conn)` after acquiring connection

## Testing

### Unit Tests

See `tests/unit/test_pgvector_semantic_search.py`:

```python
async def test_semantic_search_returns_relevant_results():
    """Test that semantic search finds conceptually similar content"""
    results = await semantic_indexer.search_semantic(
        query="user authentication",
        namespace="root",
        limit=5
    )

    assert len(results) <= 5
    assert all(0.0 <= r['similarity'] <= 1.0 for r in results)
    assert all('content' in r and 'source' in r for r in results)

async def test_incremental_indexing_skips_unchanged():
    """Test that only changed files are reindexed"""
    # Index once
    await semantic_indexer.index_path(kb_path, "root")
    first_count = await count_chunks()

    # Index again without changes
    await semantic_indexer.index_path(kb_path, "root")
    second_count = await count_chunks()

    # Should be same (no re-indexing)
    assert first_count == second_count
```

## Best Practices

1. **Use incremental indexing** - Don't clear indexes on every startup
2. **Monitor mtime tolerance** - Adjust for your environment (Docker vs native)
3. **Batch updates** - Use transactions for multi-file indexing
4. **Monitor HNSW parameters** - Tune for your dataset size and query patterns
5. **Consider IVFFlat** - For > 1M vectors, switch to IVFFlat index

## References

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [sentence-transformers](https://www.sbert.net/)
- [HNSW Algorithm](https://arxiv.org/abs/1603.09320)
- [PostgreSQL HNSW Indexing](https://github.com/pgvector/pgvector#hnsw)
- [asyncpg pgvector Support](https://github.com/pgvector/pgvector-python#asyncpg)
