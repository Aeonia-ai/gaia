-- Supabase API Keys Table Migration
-- This creates a centralized API keys table in Supabase
-- All environments will use this single source of truth

-- Create API keys table
CREATE TABLE IF NOT EXISTS public.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255),
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON public.api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON public.api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON public.api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON public.api_keys(expires_at) WHERE expires_at IS NOT NULL;

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_api_keys_updated_at 
    BEFORE UPDATE ON public.api_keys
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS)
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own API keys
CREATE POLICY "Users can view own api keys" ON public.api_keys
    FOR SELECT USING (auth.uid() = user_id);

-- Policy: Users can create their own API keys
CREATE POLICY "Users can create own api keys" ON public.api_keys
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own API keys
CREATE POLICY "Users can update own api keys" ON public.api_keys
    FOR UPDATE USING (auth.uid() = user_id);

-- Policy: Users can delete their own API keys
CREATE POLICY "Users can delete own api keys" ON public.api_keys
    FOR DELETE USING (auth.uid() = user_id);

-- Service role can do everything (for backend validation)
CREATE POLICY "Service role has full access" ON public.api_keys
    FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Create a function to validate API keys
CREATE OR REPLACE FUNCTION validate_api_key(key_hash_input VARCHAR)
RETURNS TABLE (
    user_id UUID,
    permissions JSONB,
    is_valid BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ak.user_id,
        ak.permissions,
        (ak.is_active AND (ak.expires_at IS NULL OR ak.expires_at > NOW())) as is_valid
    FROM public.api_keys ak
    WHERE ak.key_hash = key_hash_input
    LIMIT 1;
    
    -- Update last_used_at if key is valid
    UPDATE public.api_keys 
    SET last_used_at = NOW()
    WHERE key_hash = key_hash_input 
        AND is_active = true
        AND (expires_at IS NULL OR expires_at > NOW());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission on the function
GRANT EXECUTE ON FUNCTION validate_api_key TO anon, authenticated, service_role;

-- Create initial API keys for testing
-- Note: These are for development only, replace with secure keys in production
DO $$
DECLARE
    jason_user_id UUID;
BEGIN
    -- Get or create Jason's user ID
    SELECT id INTO jason_user_id 
    FROM auth.users 
    WHERE email = 'jason@aeonia.ai'
    LIMIT 1;
    
    -- Only create if user exists
    IF jason_user_id IS NOT NULL THEN
        -- Jason's development API key (matches local)
        INSERT INTO public.api_keys (
            user_id, 
            key_hash, 
            name, 
            permissions, 
            is_active
        ) VALUES (
            jason_user_id,
            '3bd5bd20d0584585aea01bbff9346c701fabd9d6237d9a77c60b81564e94de3c', -- Hash of hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY
            'Jason Development Key',
            '{"admin": true, "kb_access": true}'::jsonb,
            true
        ) ON CONFLICT (key_hash) DO NOTHING;
    END IF;
END$$;

-- Comments for documentation
COMMENT ON TABLE public.api_keys IS 'Centralized API key storage for all environments';
COMMENT ON COLUMN public.api_keys.permissions IS 'JSONB field for flexible permission storage (e.g., {"admin": true, "kb_access": true})';
COMMENT ON COLUMN public.api_keys.expires_at IS 'Optional expiration timestamp for temporary keys';
COMMENT ON FUNCTION validate_api_key IS 'Validates an API key hash and returns user info if valid';