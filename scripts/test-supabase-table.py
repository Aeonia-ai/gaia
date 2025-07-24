#!/usr/bin/env python3
"""
Test if the API keys table exists in Supabase.
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def test_supabase_table():
    """Test if we can access the api_keys table."""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_anon_key:
        print("❌ SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        return
    
    print(f"Connecting to Supabase: {supabase_url}")
    
    try:
        # Create client with anon key
        supabase: Client = create_client(supabase_url, supabase_anon_key)
        
        # Try to query the api_keys table
        response = supabase.table('api_keys').select('*').limit(1).execute()
        
        print("✅ Successfully connected to api_keys table!")
        print(f"   Found {len(response.data)} records")
        
    except Exception as e:
        error_msg = str(e)
        if "api_keys" in error_msg and "does not exist" in error_msg:
            print("❌ Table 'api_keys' does not exist in Supabase")
            print("   Please run the migration SQL in Supabase dashboard")
            print("   Migration file: migrations/supabase_api_keys.sql")
        else:
            print(f"❌ Error: {error_msg}")

if __name__ == "__main__":
    print("Testing Supabase Table Access")
    print("=============================")
    test_supabase_table()