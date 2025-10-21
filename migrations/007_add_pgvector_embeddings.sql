-- Migration 007: Add pgvector Embeddings to Semantic Search
-- Created: 2025-10-16
-- Purpose: Add vector embeddings directly to PostgreSQL using pgvector
--          Replaces ChromaDB with native PostgreSQL vector storage

-- ============================================================================
-- Enable pgvector Extension
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Add embedding column to chunk IDs table
-- Purpose: Store vector embeddings for semantic search
-- ============================================================================
ALTER TABLE kb_semantic_chunk_ids
ADD COLUMN IF NOT EXISTS chunk_text TEXT,
ADD COLUMN IF NOT EXISTS embedding vector(384);  -- all-MiniLM-L6-v2 = 384 dimensions

-- ============================================================================
-- Create HNSW index for fast similarity search
-- Purpose: Accelerate cosine similarity queries
-- ============================================================================
-- HNSW parameters:
--   m = 16: Number of bidirectional links per layer (default: 16, range: 2-100)
--   ef_construction = 64: Size of dynamic candidate list during index build (default: 64)
-- Higher values = better recall, slower inserts
CREATE INDEX IF NOT EXISTS idx_chunk_embedding_hnsw
    ON kb_semantic_chunk_ids
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- Add composite index for filtered searches
-- Purpose: Efficient queries filtering by namespace + similarity
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_chunk_path_for_namespace_lookup
    ON kb_semantic_chunk_ids(relative_path);

-- ============================================================================
-- Comments for documentation
-- ============================================================================
COMMENT ON COLUMN kb_semantic_chunk_ids.chunk_text IS
    'Original text content of the chunk (for retrieval and display)';

COMMENT ON COLUMN kb_semantic_chunk_ids.embedding IS
    'Vector embedding for this chunk (384-dim from all-MiniLM-L6-v2 model)';

COMMENT ON INDEX idx_chunk_embedding_hnsw IS
    'HNSW index for fast approximate nearest neighbor search using cosine similarity';

-- ============================================================================
-- Performance Notes
-- ============================================================================
-- HNSW vs IVFFlat:
-- - HNSW is faster for < 1M vectors (we have 10,200)
-- - HNSW: Better recall, faster queries, slower inserts
-- - IVFFlat: Faster inserts, requires more tuning
--
-- Cosine Similarity Operator: <=>
-- - Returns distance (0 = identical, 2 = opposite)
-- - Use ORDER BY embedding <=> query_vector for nearest neighbors
-- - Use 1 - (embedding <=> query_vector) for similarity score (0-1 range)
--
-- Query Example:
-- SELECT chunk_text, 1 - (embedding <=> $1::vector) AS similarity
-- FROM kb_semantic_chunk_ids
-- WHERE relative_path IN (SELECT relative_path FROM kb_semantic_index_metadata WHERE namespace = 'root')
-- ORDER BY embedding <=> $1::vector
-- LIMIT 10;
