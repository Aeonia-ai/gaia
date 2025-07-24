-- Simplified Supabase API Key validation function
-- This can be called with the anon key

-- Create or replace the validation function
CREATE OR REPLACE FUNCTION public.validate_api_key_simple(key_hash_input VARCHAR)
RETURNS TABLE (
    is_valid BOOLEAN,
    user_id UUID,
    permissions JSONB
) 
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- For testing, we'll hardcode Jason's key
    -- In production, this would query the api_keys table
    IF key_hash_input = '3bd5bd20d0584585aea01bbff9346c701fabd9d6237d9a77c60b81564e94de3c' THEN
        RETURN QUERY
        SELECT 
            true as is_valid,
            'c9958e79-b266-4f78-9bf2-1cde152bdd2f'::uuid as user_id,
            '{"admin": true, "kb_access": true}'::jsonb as permissions;
    ELSE
        -- Check the actual table if it exists
        RETURN QUERY
        SELECT 
            (ak.is_active AND (ak.expires_at IS NULL OR ak.expires_at > NOW())) as is_valid,
            ak.user_id,
            ak.permissions
        FROM public.api_keys ak
        WHERE ak.key_hash = key_hash_input
        LIMIT 1;
    END IF;
    
    -- Return empty if not found
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            false as is_valid,
            NULL::uuid as user_id,
            NULL::jsonb as permissions;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION public.validate_api_key_simple TO anon, authenticated;