# pgvector Migration Plan



## Executive Summary

**Recommendation**: Switch from ChromaDB to pgvector for semantic search.

**Why**:
- Simpler architecture (one database vs two)
- Better performance at our scale (9.81s vs 23.08s - Perplexity benchmark)
- Transactional consistency (atomic updates without sync complexity)
- Already have PostgreSQL infrastructure
- No vendor lock-in

**Current State**:
- ChromaDB: Ephemeral storage, 10,200 chunks indexed, reindexes on every restart (~53 min)
- PostgreSQL: Migration 006 applied with metadata tables ready

**Migration Effort**: ~2-3 hours
**Ideal Timing**: NOW (migration done, no implementation committed)

---

## Phase 1: Enable pgvector Extension

### Step 1.1: Check if pgvector is available
```bash
docker exec gaia-db-1 psql -U postgres -d llm_platform -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
```

### Step 1.2: Install pgvector (if not available)
```bash
# Add to Dockerfile or use existing PostgreSQL image with pgvector
# pgvector is included in postgres:15 official image as of recent versions
docker exec gaia-db-1 psql -U postgres -d llm_platform -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Step 1.3: Verify installation
```bash
docker exec gaia-db-1 psql -U postgres -d llm_platform -c "\dx vector"
```

---

## Phase 2: Create Migration 007 - Add Embeddings Column

**File**: `migrations/007_add_pgvector_embeddings.sql`

```sql
-- Migration 007: Add pgvector Embeddings to Semantic Search
-- Created: 2025-10-16
-- Purpose: Add vector embeddings directly to PostgreSQL using pgvector
--          Replaces ChromaDB with native PostgreSQL vector storage

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to metadata table
ALTER TABLE kb_semantic_index_metadata
ADD COLUMN embedding vector(384);  -- all-MiniLM-L6-v2 produces 384-dimensional vectors

-- Create index for vector similarity search (using HNSW for speed)
CREATE INDEX IF NOT EXISTS idx_semantic_embedding_hnsw
    ON kb_semantic_index_metadata
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Add chunk content and embedding to chunk IDs table
ALTER TABLE kb_semantic_chunk_ids
ADD COLUMN chunk_text TEXT,
ADD COLUMN embedding vector(384);

-- Create index for chunk-level vector search
CREATE INDEX IF NOT EXISTS idx_chunk_embedding_hnsw
    ON kb_semantic_chunk_ids
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Comments for documentation
COMMENT ON COLUMN kb_semantic_index_metadata.embedding IS
    'Vector embedding for entire document (aggregated from chunks)';

COMMENT ON COLUMN kb_semantic_chunk_ids.chunk_text IS
    'Original text content of the chunk';

COMMENT ON COLUMN kb_semantic_chunk_ids.embedding IS
    'Vector embedding for this specific chunk (384-dim from all-MiniLM-L6-v2)';

-- Performance tuning for vector operations
-- Increase maintenance_work_mem for faster index building
-- SET maintenance_work_mem = '512MB';  -- Uncomment for production
```

**Why HNSW index**:
- Faster than IVFFlat for < 1M vectors (we have 10,200)
- Parameters: m=16 (graph connections), ef_construction=64 (build quality)
- Trade-off: Slower inserts, much faster searches (perfect for read-heavy workload)

---

## Phase 3: Update Semantic Search Code

### File Changes:

**3.1: Update `kb_semantic_search.py`**

Replace ChromaDB logic with pgvector queries:

```python
# OLD (ChromaDB):
collection = chromadb_manager.get_or_create_collection(namespace)
results = collection.query(query_texts=[query], n_results=limit)

# NEW (pgvector):
from sentence_transformers import SentenceTransformer

# Initialize model (same as ChromaDB uses)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate query embedding
query_embedding = model.encode(query).tolist()

# Search using pgvector
async with db_pool.acquire() as conn:
    results = await conn.fetch("""
        SELECT
            c.chunk_text,
            c.relative_path,
            m.namespace,
            1 - (c.embedding <=> $1::vector) AS similarity
        FROM kb_semantic_chunk_ids c
        JOIN kb_semantic_index_metadata m ON c.relative_path = m.relative_path
        WHERE m.namespace = $2
        ORDER BY c.embedding <=> $1::vector
        LIMIT $3
    """, query_embedding, namespace, limit)
```

**3.2: Update `kb_chromadb_manager.py`**

Option A: Rename to `kb_embedding_manager.py` and replace ChromaDB with sentence-transformers
Option B: Delete entirely and add embedding logic directly to `kb_semantic_search.py`

Recommend Option B for simplicity.

**3.3: Update `main.py`**

Remove ChromaDB manager initialization:
```python
# OLD:
from app.services.kb.kb_chromadb_manager import chromadb_manager

# NEW:
# No manager needed - embeddings generated inline
```

---

## Phase 4: Update Indexing Logic

**File**: `kb_semantic_search.py` (update `_run_chromadb_index`)

```python
def _run_pgvector_index(self, path: Path, namespace: str):
    """Run pgvector indexing (blocking operation)."""
    from sentence_transformers import SentenceTransformer
    import asyncio

    logger.info(f"Starting pgvector indexing for path: {path}")
    start_time = time.time()

    # Initialize embedding model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Process files
    md_files = list(path.rglob("*.md"))
    total_files = len(md_files)

    for md_file in md_files:
        relative_path = str(md_file.relative_to(path))

        # Check if file needs reindexing (mtime changed)
        current_mtime = md_file.stat().st_mtime

        existing = await db_pool.fetchrow(
            "SELECT mtime FROM kb_semantic_index_metadata WHERE relative_path = $1",
            relative_path
        )

        if existing and existing['mtime'] == current_mtime:
            logger.debug(f"Skipping unchanged file: {relative_path}")
            continue

        # File changed or new - reindex
        content = md_file.read_text(encoding='utf-8')
        chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip() and len(chunk) > 50]

        # Delete old chunks if file was previously indexed
        if existing:
            await db_pool.execute(
                "DELETE FROM kb_semantic_index_metadata WHERE relative_path = $1",
                relative_path
            )

        # Generate embeddings for all chunks
        embeddings = model.encode(chunks).tolist()

        # Insert metadata
        await db_pool.execute("""
            INSERT INTO kb_semantic_index_metadata (relative_path, namespace, mtime, num_chunks)
            VALUES ($1, $2, $3, $4)
        """, relative_path, namespace, current_mtime, len(chunks))

        # Insert chunks with embeddings
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{namespace}_{relative_path}_{idx}"
            await db_pool.execute("""
                INSERT INTO kb_semantic_chunk_ids (relative_path, chunk_id, chunk_index, chunk_text, embedding)
                VALUES ($1, $2, $3, $4, $5)
            """, relative_path, chunk_id, idx, chunk, embedding)

    elapsed = time.time() - start_time
    logger.info(f"pgvector indexing completed in {elapsed:.1f}s")
    logger.info(f"Indexed {sum(len(chunks) for chunks in ...)} chunks from {total_files} files")
```

**Key Improvement**: Incremental indexing! Only reindexes files with changed `mtime`.

---

## Phase 5: Remove ChromaDB Dependencies

### 5.1: Update `requirements.txt`
```diff
- chromadb==0.4.22
+ pgvector==0.2.4
  sentence-transformers==2.2.2  # Keep (used for embeddings)
```

### 5.2: Update `docker-compose.yml`
```yaml
# No changes needed - pgvector runs inside PostgreSQL
# Can remove any ChromaDB-specific environment variables if they exist
```

### 5.3: Delete Files
- `app/services/kb/kb_chromadb_manager.py` (no longer needed)

---

## Phase 6: Testing

### 6.1: Unit Tests
```python
# tests/unit/test_pgvector_search.py
async def test_semantic_search_with_pgvector():
    """Test vector search returns relevant results"""
    results = await semantic_search.search("AI game design", namespace="root", limit=5)
    assert len(results) <= 5
    assert all(r['similarity'] >= 0.0 for r in results)

async def test_incremental_indexing():
    """Test only changed files are reindexed"""
    # Index once
    await semantic_search.index(path, namespace="root")
    first_count = await count_chunks()

    # Touch one file
    md_file.touch()

    # Reindex
    await semantic_search.index(path, namespace="root")
    second_count = await count_chunks()

    # Should only reindex the touched file
    assert second_count == first_count  # Same total chunks
```

### 6.2: Integration Tests
```python
# tests/integration/test_pgvector_e2e.py
async def test_full_index_search_workflow():
    """Test complete workflow: index → search → verify results"""
    # Similar to existing ChromaDB tests
```

---

## Phase 7: Deployment

### 7.1: Local Deployment
```bash
# Apply migration 007
docker exec gaia-db-1 psql -U postgres -d llm_platform -f /app/migrations/007_add_pgvector_embeddings.sql

# Rebuild kb-docs service
docker compose build kb-docs
docker compose up -d kb-docs

# Verify indexing
curl http://localhost:8005/search/semantic/progress/root
```

### 7.2: Remote Deployment
```bash
# Apply migration to dev database
./scripts/apply_remote_migrations.py --env dev --migration migrations/007_add_pgvector_embeddings.sql

# Deploy updated service
fly deploy --config fly.kb-docs.dev.toml --remote-only
```

---

## Migration Checklist

- [ ] Phase 1: Enable pgvector extension
- [ ] Phase 2: Create migration 007
- [ ] Phase 3: Update semantic search code
- [ ] Phase 4: Update indexing logic
- [ ] Phase 5: Remove ChromaDB dependencies
- [ ] Phase 6: Write and run tests
- [ ] Phase 7: Deploy locally
- [ ] Phase 8: Deploy to dev/staging/prod

---

## Rollback Plan

If issues occur:

1. **Keep migration 006** - Metadata tables are useful for both approaches
2. **Revert code changes** - Git reset to before pgvector implementation
3. **Re-add ChromaDB dependency** - `pip install chromadb==0.4.22`
4. **Keep migration 007** - Vector columns don't hurt, just unused

**Low risk**: Can run both ChromaDB and pgvector in parallel during transition.

---

## Performance Expectations

**Before (ChromaDB ephemeral)**:
- Startup: 53 minutes (full reindex every restart)
- Search: Unknown (not benchmarked)
- Storage: In-memory (lost on restart)

**After (pgvector)**:
- Startup: ~30 seconds (incremental reindex only changed files)
- Search: ~9.81s for 10,200 chunks (Perplexity benchmark)
- Storage: PostgreSQL disk (persistent)

**Estimated Improvement**: ~100x faster startup, persistent storage, incremental updates.
