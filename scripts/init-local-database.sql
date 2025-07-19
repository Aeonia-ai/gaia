-- Gaia Platform Local Database Initialization
-- Creates user-associated authentication schema for Docker development

BEGIN;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create API keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255),
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);

-- Create conversations table (required for chat messages)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    preview TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_is_active ON conversations(is_active);

-- Create chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    model VARCHAR(100),
    provider VARCHAR(50),
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);

-- LLM Platform Compatible Asset Tables
-- Note: Vector extension disabled for local development - can be enabled in production

-- Asset sources table
CREATE TABLE IF NOT EXISTS asset_sources (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL, -- 'open_source', 'community', 'generated'
    source_name VARCHAR(100) NOT NULL, -- 'poly_haven', 'freesound', 'community'
    api_endpoint VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    rate_limit_per_minute INTEGER DEFAULT NULL,
    requires_attribution BOOLEAN DEFAULT false,
    cost_per_request DECIMAL(10, 6) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Main assets table with vector embeddings and storage references
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id INTEGER REFERENCES asset_sources(id),
    external_id VARCHAR(255),
    category VARCHAR(50) NOT NULL, -- 'environment', 'character', 'prop', 'audio', 'texture', 'animation'
    title VARCHAR(255) NOT NULL,
    description TEXT,
    style_tags TEXT[],
    
    -- Storage configuration
    file_url TEXT NOT NULL, -- Either Supabase Storage URL or external URL
    storage_type VARCHAR(20) NOT NULL, -- 'supabase', 'external', 'generated'
    file_size_mb FLOAT,
    file_format VARCHAR(10), -- 'gltf', 'fbx', 'wav', 'png', etc.
    preview_image_url TEXT, -- Always stored in Supabase for consistency
    
    -- Quality and licensing
    quality_score FLOAT DEFAULT 0.0 CHECK (quality_score >= 0 AND quality_score <= 1),
    download_count INTEGER DEFAULT 0,
    license_type VARCHAR(50), -- 'creative_commons', 'public_domain', 'custom', 'commercial', 'proprietary'
    attribution_required BOOLEAN DEFAULT false,
    
    -- Search and metadata
    metadata JSONB DEFAULT '{}',
    -- embedding VECTOR(384), -- Semantic search embedding (disabled for local dev)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_category CHECK (category IN ('environment', 'character', 'prop', 'audio', 'texture', 'animation', 'image')),
    CONSTRAINT valid_storage_type CHECK (storage_type IN ('supabase', 'external', 'generated')),
    CONSTRAINT valid_license CHECK (license_type IN ('creative_commons', 'public_domain', 'custom', 'commercial', 'proprietary'))
);

-- Asset generation history table for tracking AI generations
CREATE TABLE IF NOT EXISTS asset_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    generation_prompt TEXT NOT NULL,
    generation_service VARCHAR(50) NOT NULL, -- 'meshy', 'midjourney', 'mubert', etc.
    generation_cost DECIMAL(10, 4) NOT NULL,
    generation_time_ms INTEGER NOT NULL,
    session_id VARCHAR(255),
    user_id VARCHAR(255), -- For user tracking
    generation_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Asset modifications history table for tracking hybrid approach
CREATE TABLE IF NOT EXISTS asset_modifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    modified_asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    modifications TEXT[] NOT NULL, -- Array of modification descriptions
    modification_service VARCHAR(50) NOT NULL,
    modification_cost DECIMAL(10, 4) NOT NULL,
    modification_time_ms INTEGER NOT NULL,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    modification_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Asset usage analytics table
CREATE TABLE IF NOT EXISTS asset_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    usage_type VARCHAR(50) NOT NULL, -- 'download', 'view', 'request'
    cost_incurred DECIMAL(10, 4) DEFAULT 0.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Performance indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category);
CREATE INDEX IF NOT EXISTS idx_assets_style_tags ON assets USING GIN(style_tags);
CREATE INDEX IF NOT EXISTS idx_assets_quality ON assets(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_assets_storage_type ON assets(storage_type);
CREATE INDEX IF NOT EXISTS idx_assets_license ON assets(license_type);
CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assets_download_count ON assets(download_count DESC);

-- Vector similarity search index (disabled for local development)
-- CREATE INDEX IF NOT EXISTS idx_assets_embedding ON assets USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Indexes for foreign key relationships
CREATE INDEX IF NOT EXISTS idx_assets_source_id ON assets(source_id);
CREATE INDEX IF NOT EXISTS idx_asset_generations_asset_id ON asset_generations(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_generations_session_id ON asset_generations(session_id);
CREATE INDEX IF NOT EXISTS idx_asset_modifications_base_asset_id ON asset_modifications(base_asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_modifications_modified_asset_id ON asset_modifications(modified_asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_usage_asset_id ON asset_usage(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_usage_user_id ON asset_usage(user_id);

-- Full-text search indexes for title and description
CREATE INDEX IF NOT EXISTS idx_assets_title_fts ON assets USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_assets_description_fts ON assets USING gin(to_tsvector('english', description));

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_assets_category_quality ON assets(category, quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_assets_category_created ON assets(category, created_at DESC);

-- Insert default asset sources
INSERT INTO asset_sources (source_type, source_name, api_endpoint, is_active, rate_limit_per_minute, requires_attribution) VALUES
    ('open_source', 'poly_haven', 'https://api.polyhaven.com', true, 60, true),
    ('open_source', 'freesound', 'https://freesound.org/apiv2', true, 60, true),
    ('open_source', 'opengameart', 'https://opengameart.org', true, 30, true),
    ('community', 'community_uploads', NULL, true, NULL, false),
    ('generated', 'meshy_ai', 'https://api.meshy.ai', true, 10, false),
    ('generated', 'midjourney', NULL, true, 5, false),
    ('generated', 'mubert', 'https://api.mubert.com', true, 20, false),
    ('generated', 'openai', 'https://api.openai.com', true, 50, false),
    ('generated', 'stability', 'https://api.stability.ai', true, 50, false)
ON CONFLICT DO NOTHING;

-- Insert default development user
INSERT INTO users (email, name) 
VALUES ('dev@gaia.local', 'Local Development User')
ON CONFLICT (email) DO NOTHING;

-- Insert API key for development (API_KEY from .env: FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE)
-- SHA256 hash: 8065e7a7dd9a5d02ea3a79cea93036e7092910c309bb3e43070826f3b939f661
DO $$
DECLARE
    dev_user_id UUID;
    dev_conversation_id UUID;
BEGIN
    SELECT id INTO dev_user_id FROM users WHERE email = 'dev@gaia.local';
    
    -- Create a default conversation for the dev user
    INSERT INTO conversations (user_id, title, preview)
    VALUES (dev_user_id, 'Welcome to Gaia', 'Your first conversation')
    ON CONFLICT DO NOTHING
    RETURNING id INTO dev_conversation_id;
    
    -- Insert API key for development user
    INSERT INTO api_keys (user_id, key_hash, name, permissions, is_active)
    VALUES (
        dev_user_id,
        '8065e7a7dd9a5d02ea3a79cea93036e7092910c309bb3e43070826f3b939f661',
        'Local Development API Key',
        '{"admin": true, "environment": "local"}'::jsonb,
        true
    )
    ON CONFLICT (key_hash) DO UPDATE
    SET updated_at = CURRENT_TIMESTAMP,
        is_active = true;
END$$;

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to tables
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_api_keys_updated_at ON api_keys;
CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_assets_updated_at ON assets;
CREATE TRIGGER update_assets_updated_at BEFORE UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_asset_sources_updated_at ON asset_sources;
CREATE TRIGGER update_asset_sources_updated_at BEFORE UPDATE ON asset_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;

-- Verification
SELECT 'Local database initialized successfully' as status;
SELECT 'Users:' as info, COUNT(*) as count FROM users;
SELECT 'API keys:' as info, COUNT(*) as count FROM api_keys;
SELECT 'Dev user:' as info, email, name FROM users WHERE email = 'dev@gaia.local';