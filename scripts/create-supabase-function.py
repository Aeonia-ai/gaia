#!/usr/bin/env python3
"""
Create the validate_api_key_simple function in Supabase.
This script shows what SQL to run in Supabase.
"""

print("""
Supabase Function Setup
======================

Please run this SQL in your Supabase SQL Editor:

1. Go to: https://app.supabase.com/project/lbaohvnusingoztdzlmj/sql/new
2. Copy and paste this SQL:

----------------------------------------
-- Simple API key validation function
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
    -- Hardcoded for testing - Jason's API key
    IF key_hash_input = '3bd5bd20d0584585aea01bbff9346c701fabd9d6237d9a77c60b81564e94de3c' THEN
        RETURN QUERY
        SELECT 
            true as is_valid,
            'c9958e79-b266-4f78-9bf2-1cde152bdd2f'::uuid as user_id,
            '{"admin": true, "kb_access": true}'::jsonb as permissions;
    ELSE
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
----------------------------------------

3. Click "Run" to create the function
4. Test with: SELECT * FROM validate_api_key_simple('3bd5bd20d0584585aea01bbff9346c701fabd9d6237d9a77c60b81564e94de3c');

""")