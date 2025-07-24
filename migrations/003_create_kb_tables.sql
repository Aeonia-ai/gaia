-- KB Document Storage Tables
-- Migration 003: Create knowledge base document storage tables
-- Date: 2025-07-19

-- Main document storage table
CREATE TABLE IF NOT EXISTS kb_documents (
    path TEXT PRIMARY KEY,
    document JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    locked_by TEXT,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT path_not_empty CHECK (LENGTH(path) > 0),
    CONSTRAINT version_positive CHECK (version > 0)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_kb_path_pattern ON kb_documents (path text_pattern_ops);
CREATE INDEX IF NOT EXISTS idx_kb_updated_at ON kb_documents (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_kb_version ON kb_documents (version);
CREATE INDEX IF NOT EXISTS idx_kb_locked ON kb_documents (locked_by, locked_until) WHERE locked_by IS NOT NULL;

-- JSONB indexes for document content and metadata
CREATE INDEX IF NOT EXISTS idx_kb_metadata ON kb_documents USING GIN ((document->'metadata'));
CREATE INDEX IF NOT EXISTS idx_kb_keywords ON kb_documents USING GIN ((document->'keywords'));
CREATE INDEX IF NOT EXISTS idx_kb_content_search ON kb_documents USING GIN (to_tsvector('english', document->>'content'));

-- Search optimization table for faster text search
CREATE TABLE IF NOT EXISTS kb_search_index (
    path TEXT REFERENCES kb_documents(path) ON DELETE CASCADE,
    line_number INTEGER,
    content_excerpt TEXT,
    search_vector tsvector,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (path, line_number)
);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_kb_search_vector ON kb_search_index USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_kb_search_keywords ON kb_search_index USING GIN (keywords);

-- Context loading optimization table
CREATE TABLE IF NOT EXISTS kb_context_cache (
    context_name TEXT PRIMARY KEY,
    file_paths TEXT[] NOT NULL,
    total_size INTEGER DEFAULT 0,
    keywords TEXT[],
    entities JSONB,
    last_accessed TIMESTAMP DEFAULT NOW(),
    last_modified TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT context_name_not_empty CHECK (LENGTH(context_name) > 0)
);

-- Index for context queries
CREATE INDEX IF NOT EXISTS idx_kb_context_accessed ON kb_context_cache (last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_kb_context_keywords ON kb_context_cache USING GIN (keywords);

-- Version history table for document revisions
CREATE TABLE IF NOT EXISTS kb_document_history (
    id SERIAL PRIMARY KEY,
    path TEXT NOT NULL,
    version INTEGER NOT NULL,
    document JSONB NOT NULL,
    change_type TEXT NOT NULL, -- 'create', 'update', 'delete', 'move'
    changed_by TEXT,
    change_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Foreign key to current document
    FOREIGN KEY (path) REFERENCES kb_documents(path) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT change_type_valid CHECK (change_type IN ('create', 'update', 'delete', 'move')),
    CONSTRAINT version_positive_history CHECK (version > 0)
);

-- Indexes for history queries
CREATE INDEX IF NOT EXISTS idx_kb_history_path ON kb_document_history (path, version DESC);
CREATE INDEX IF NOT EXISTS idx_kb_history_created ON kb_document_history (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kb_history_user ON kb_document_history (changed_by, created_at DESC);

-- Sharing and permissions table (for multi-user future)
CREATE TABLE IF NOT EXISTS kb_permissions (
    id SERIAL PRIMARY KEY,
    resource_path TEXT NOT NULL,
    resource_type TEXT NOT NULL DEFAULT 'file', -- 'file', 'directory', 'context'
    principal_id TEXT NOT NULL, -- user_id, team_id, or 'public'
    principal_type TEXT NOT NULL DEFAULT 'user', -- 'user', 'team', 'public'
    permissions TEXT[] NOT NULL DEFAULT ARRAY['read'], -- 'read', 'write', 'share', 'admin'
    granted_by TEXT,
    granted_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT resource_type_valid CHECK (resource_type IN ('file', 'directory', 'context')),
    CONSTRAINT principal_type_valid CHECK (principal_type IN ('user', 'team', 'public')),
    CONSTRAINT permissions_valid CHECK (permissions <@ ARRAY['read', 'write', 'share', 'admin']),
    
    -- Unique constraint for resource-principal pairs
    UNIQUE (resource_path, principal_id, principal_type)
);

-- Indexes for permission queries
CREATE INDEX IF NOT EXISTS idx_kb_permissions_resource ON kb_permissions (resource_path, resource_type);
CREATE INDEX IF NOT EXISTS idx_kb_permissions_principal ON kb_permissions (principal_id, principal_type);
CREATE INDEX IF NOT EXISTS idx_kb_permissions_expires ON kb_permissions (expires_at) WHERE expires_at IS NOT NULL;

-- Activity log for auditing and monitoring
CREATE TABLE IF NOT EXISTS kb_activity_log (
    id SERIAL PRIMARY KEY,
    action TEXT NOT NULL, -- 'create', 'read', 'update', 'delete', 'search', 'share'
    resource_path TEXT,
    resource_type TEXT DEFAULT 'file',
    actor_id TEXT,
    actor_type TEXT DEFAULT 'user',
    details JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT action_valid CHECK (action IN ('create', 'read', 'update', 'delete', 'search', 'share', 'move'))
);

-- Indexes for activity queries
CREATE INDEX IF NOT EXISTS idx_kb_activity_created ON kb_activity_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kb_activity_actor ON kb_activity_log (actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kb_activity_resource ON kb_activity_log (resource_path, action);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_kb_document_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS trigger_kb_document_updated_at ON kb_documents;
CREATE TRIGGER trigger_kb_document_updated_at
    BEFORE UPDATE ON kb_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_kb_document_timestamp();

-- Function to automatically create history entries
CREATE OR REPLACE FUNCTION create_kb_document_history()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert into history when document is updated
    IF TG_OP = 'UPDATE' THEN
        INSERT INTO kb_document_history (path, version, document, change_type, changed_by, change_message)
        VALUES (NEW.path, NEW.version, NEW.document, 'update', 
                COALESCE(NEW.document->>'changed_by', 'system'),
                COALESCE(NEW.document->>'change_message', 'Updated via API'));
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO kb_document_history (path, version, document, change_type, changed_by, change_message)
        VALUES (NEW.path, NEW.version, NEW.document, 'create',
                COALESCE(NEW.document->>'changed_by', 'system'),
                COALESCE(NEW.document->>'change_message', 'Created via API'));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO kb_document_history (path, version, document, change_type, changed_by, change_message)
        VALUES (OLD.path, OLD.version, OLD.document, 'delete',
                COALESCE(OLD.document->>'changed_by', 'system'),
                COALESCE(OLD.document->>'change_message', 'Deleted via API'));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic history creation
DROP TRIGGER IF EXISTS trigger_kb_document_history ON kb_documents;
CREATE TRIGGER trigger_kb_document_history
    AFTER INSERT OR UPDATE OR DELETE ON kb_documents
    FOR EACH ROW
    EXECUTE FUNCTION create_kb_document_history();

-- Grant permissions to the application user
-- (These should be run with appropriate user credentials)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gaia_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gaia_user;

-- Insert initial metadata
INSERT INTO kb_activity_log (action, resource_type, actor_id, details) 
VALUES ('create', 'schema', 'migration', '{"migration": "003_create_kb_tables", "version": "1.0.0"}')
ON CONFLICT DO NOTHING;

COMMENT ON TABLE kb_documents IS 'Main KB document storage with JSONB content and versioning';
COMMENT ON TABLE kb_search_index IS 'Optimized search index for fast full-text queries';
COMMENT ON TABLE kb_context_cache IS 'Cached context metadata for fast context loading';
COMMENT ON TABLE kb_document_history IS 'Version history and audit trail for all document changes';
COMMENT ON TABLE kb_permissions IS 'Access control and sharing permissions for multi-user support';
COMMENT ON TABLE kb_activity_log IS 'Activity log for monitoring and analytics';