-- Migration 008: Fix Semantic Search Metadata Primary Key
-- Created: 2025-11-03
-- Purpose: Fix primary key to support multiple namespaces with same file paths
--          The original migration 006 used only relative_path as PK, causing
--          duplicate key errors when multiple namespaces had files with the
--          same relative path (e.g., CLAUDE.md in root, teams/*, users/*)

-- ============================================================================
-- Step 1: Clear existing data (it's broken anyway due to duplicate key errors)
-- ============================================================================
TRUNCATE TABLE kb_semantic_chunk_ids CASCADE;
TRUNCATE TABLE kb_semantic_index_metadata CASCADE;

-- ============================================================================
-- Step 2: Drop the old foreign key constraint first
-- ============================================================================
ALTER TABLE kb_semantic_chunk_ids
DROP CONSTRAINT IF EXISTS fk_semantic_chunk_path;

-- ============================================================================
-- Step 3: Drop the old primary key constraint
-- ============================================================================
ALTER TABLE kb_semantic_index_metadata
DROP CONSTRAINT kb_semantic_index_metadata_pkey;

-- ============================================================================
-- Step 4: Add composite primary key (namespace, relative_path)
-- ============================================================================
ALTER TABLE kb_semantic_index_metadata
ADD PRIMARY KEY (namespace, relative_path);

-- ============================================================================
-- Step 5: Update kb_semantic_chunk_ids to support composite foreign key
-- ============================================================================

-- Add namespace column to chunk_ids table if it doesn't exist
-- (needed for the new composite foreign key)
ALTER TABLE kb_semantic_chunk_ids
ADD COLUMN IF NOT EXISTS namespace TEXT;

-- Populate namespace from relative_path for any existing data
-- (should be empty after TRUNCATE, but this handles edge cases)
UPDATE kb_semantic_chunk_ids
SET namespace = COALESCE(namespace, 'root')
WHERE namespace IS NULL;

-- Make namespace NOT NULL
ALTER TABLE kb_semantic_chunk_ids
ALTER COLUMN namespace SET NOT NULL;

-- Add new composite foreign key constraint
ALTER TABLE kb_semantic_chunk_ids
ADD CONSTRAINT fk_semantic_chunk_path
    FOREIGN KEY (namespace, relative_path)
    REFERENCES kb_semantic_index_metadata(namespace, relative_path)
    ON DELETE CASCADE;

-- ============================================================================
-- Step 5: Update indexes for better performance with composite key
-- ============================================================================

-- Drop old index on just namespace
DROP INDEX IF EXISTS idx_semantic_metadata_namespace;

-- Create new composite index (namespace is now part of PK, so this is redundant)
-- But keep separate index on namespace alone for queries that filter by namespace
CREATE INDEX IF NOT EXISTS idx_semantic_metadata_namespace
    ON kb_semantic_index_metadata(namespace);

-- Add index on namespace for chunk_ids table
CREATE INDEX IF NOT EXISTS idx_semantic_chunk_namespace
    ON kb_semantic_chunk_ids(namespace);

-- Composite index for common query pattern (namespace + relative_path)
CREATE INDEX IF NOT EXISTS idx_semantic_chunk_namespace_path
    ON kb_semantic_chunk_ids(namespace, relative_path);

-- ============================================================================
-- Comments for documentation
-- ============================================================================
COMMENT ON CONSTRAINT kb_semantic_index_metadata_pkey ON kb_semantic_index_metadata IS
    'Composite primary key ensures unique file paths per namespace (fixed in migration 008)';

COMMENT ON COLUMN kb_semantic_chunk_ids.namespace IS
    'Namespace for this chunk - must match parent metadata record (added in migration 008)';

-- ============================================================================
-- Migration Notes
-- ============================================================================
-- This migration fixes a bug introduced in migration 006 where the primary key
-- was only on relative_path, not accounting for multiple namespaces having files
-- with the same relative path.
--
-- Impact:
-- - All existing semantic search data is cleared (it was broken anyway)
-- - Service will automatically re-index after this migration
-- - Incremental indexing will work correctly going forward
--
-- The bug caused:
-- - Duplicate key violations when indexing files across namespaces
-- - No embeddings being saved (0 chunks from N files)
-- - Infinite re-indexing loops (no metadata saved = always "new" files)
-- - Service blocked for hours trying to index the same files repeatedly
