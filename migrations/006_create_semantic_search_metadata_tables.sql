-- Migration 006: Semantic Search Metadata Tracking Tables
-- Created: 2025-10-16
-- Purpose: Add tables for tracking ChromaDB semantic search index metadata
--          Enables incremental updates by tracking file mtimes and chunk IDs

-- ============================================================================
-- Table: kb_semantic_index_metadata
-- Purpose: Track which files have been indexed and when
-- ============================================================================
CREATE TABLE IF NOT EXISTS kb_semantic_index_metadata (
    relative_path TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,
    mtime REAL NOT NULL,  -- File modification time (Unix timestamp)
    num_chunks INTEGER NOT NULL,  -- Number of chunks indexed for this file
    last_indexed TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_semantic_metadata_namespace
    ON kb_semantic_index_metadata(namespace);

CREATE INDEX IF NOT EXISTS idx_semantic_metadata_last_indexed
    ON kb_semantic_index_metadata(last_indexed);

CREATE INDEX IF NOT EXISTS idx_semantic_metadata_namespace_mtime
    ON kb_semantic_index_metadata(namespace, mtime);

-- ============================================================================
-- Table: kb_semantic_chunk_ids
-- Purpose: Track ChromaDB document IDs for each file's chunks
--          Enables efficient deletion when files change or are removed
-- ============================================================================
CREATE TABLE IF NOT EXISTS kb_semantic_chunk_ids (
    id SERIAL PRIMARY KEY,
    relative_path TEXT NOT NULL,
    chunk_id TEXT NOT NULL UNIQUE,  -- ChromaDB document ID
    chunk_index INTEGER NOT NULL,  -- Position of chunk within file
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Foreign key with cascade delete
    CONSTRAINT fk_semantic_chunk_path
        FOREIGN KEY (relative_path)
        REFERENCES kb_semantic_index_metadata(relative_path)
        ON DELETE CASCADE
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_semantic_chunk_path
    ON kb_semantic_chunk_ids(relative_path);

CREATE INDEX IF NOT EXISTS idx_semantic_chunk_id
    ON kb_semantic_chunk_ids(chunk_id);

CREATE INDEX IF NOT EXISTS idx_semantic_chunk_path_index
    ON kb_semantic_chunk_ids(relative_path, chunk_index);

-- ============================================================================
-- Comments for documentation
-- ============================================================================
COMMENT ON TABLE kb_semantic_index_metadata IS
    'Tracks semantic search index metadata for incremental updates';

COMMENT ON COLUMN kb_semantic_index_metadata.relative_path IS
    'File path relative to KB root (e.g., "docs/api/overview.md")';

COMMENT ON COLUMN kb_semantic_index_metadata.namespace IS
    'KB namespace (e.g., "root", "users/email@example.com")';

COMMENT ON COLUMN kb_semantic_index_metadata.mtime IS
    'File modification time as Unix timestamp for change detection';

COMMENT ON COLUMN kb_semantic_index_metadata.num_chunks IS
    'Number of chunks indexed for this file';

COMMENT ON TABLE kb_semantic_chunk_ids IS
    'Maps files to their ChromaDB chunk IDs for efficient deletion';

COMMENT ON COLUMN kb_semantic_chunk_ids.chunk_id IS
    'ChromaDB document ID (unique across all collections)';

COMMENT ON COLUMN kb_semantic_chunk_ids.chunk_index IS
    'Sequential position of chunk within source file (0-based)';
