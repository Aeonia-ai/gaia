#!/bin/bash

# Initialize local database for Supabase auth

echo "🗄️  Initializing local database for Supabase auth..."

# Create auth schema and tables
docker compose exec -T db psql -U postgres -d gaiaplatform << EOF
-- Create auth schema if not exists
CREATE SCHEMA IF NOT EXISTS auth;

-- Create users table in auth schema
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    encrypted_password VARCHAR(255),
    email_confirmed_at TIMESTAMP,
    raw_user_meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Supabase user (if using Supabase auth, this won't be used locally)
-- But we'll create the structure for compatibility
INSERT INTO auth.users (email, email_confirmed_at, raw_user_meta_data)
VALUES ('jason@aeonia.ai', NOW(), '{"name": "Jason Asbahr"}'::jsonb)
ON CONFLICT (email) DO NOTHING;

-- Also ensure public schema has users table for app compatibility
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sync users from auth to public
INSERT INTO public.users (id, email, name)
SELECT 
    id, 
    email, 
    raw_user_meta_data->>'name' as name
FROM auth.users
ON CONFLICT (email) DO UPDATE
SET name = EXCLUDED.name;

-- Create API keys table
CREATE TABLE IF NOT EXISTS public.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255),
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON public.api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON public.api_keys(key_hash);

-- Get user ID and create API key
DO \$\$
DECLARE
    user_id UUID;
BEGIN
    SELECT id INTO user_id FROM public.users WHERE email = 'jason@aeonia.ai';
    
    IF user_id IS NOT NULL THEN
        INSERT INTO public.api_keys (user_id, key_hash, name, permissions, is_active)
        VALUES (
            user_id,
            'ef6dc9930d5795da9f45e0f95d93fa996bfd94b405549190dafdcfcd517e8507',
            'Local Dev API Key',
            '{"admin": true}'::jsonb,
            true
        )
        ON CONFLICT (key_hash) DO NOTHING;
    END IF;
END\$\$;

\dt auth.*
\dt public.*
EOF

echo "✅ Local database initialized!"
echo "Note: This creates the schema for compatibility, but actual auth goes through Supabase"