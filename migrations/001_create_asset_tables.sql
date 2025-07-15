-- Universal Asset Server Database Schema
-- Creates tables for asset management with vector search capabilities

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

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
    embedding VECTOR(384), -- Semantic search embedding (384 dimensions for sentence-transformers)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_category CHECK (category IN ('environment', 'character', 'prop', 'audio', 'texture', 'animation')),
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

-- Vector similarity search index (using IVFFlat for fast approximate search)
CREATE INDEX IF NOT EXISTS idx_assets_embedding ON assets USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

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
    ('generated', 'mubert', 'https://api.mubert.com', true, 20, false)
ON CONFLICT DO NOTHING;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update the updated_at column
CREATE TRIGGER update_assets_updated_at BEFORE UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asset_sources_updated_at BEFORE UPDATE ON asset_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();