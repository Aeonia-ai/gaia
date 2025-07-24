#!/usr/bin/env python3
"""
Add Jason's API key to Supabase for testing.
"""
import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def add_jason_api_key():
    """Add Jason's development API key to Supabase."""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_anon_key:
        print("❌ SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        return
    
    print(f"Connecting to Supabase: {supabase_url}")
    
    try:
        # Create client
        supabase: Client = create_client(supabase_url, supabase_anon_key)
        
        # First, check if Jason exists in Supabase auth.users
        # For now, we'll use a dummy user ID since we can't query auth.users with anon key
        # In production, this would be Jason's actual Supabase user ID
        
        # Check if the API key already exists
        key_hash = '3bd5bd20d0584585aea01bbff9346c701fabd9d6237d9a77c60b81564e94de3c'
        
        existing = supabase.table('api_keys').select('*').eq('key_hash', key_hash).execute()
        
        if existing.data:
            print("✅ Jason's API key already exists in Supabase!")
            print(f"   Key name: {existing.data[0]['name']}")
            print(f"   Active: {existing.data[0]['is_active']}")
        else:
            # Create a test user ID for Jason (in production, this would be from auth.users)
            # Using a deterministic UUID based on email
            import uuid
            jason_user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, 'jason@aeonia.ai'))
            
            # Insert the API key
            api_key_data = {
                'user_id': jason_user_id,
                'key_hash': key_hash,
                'name': 'Jason Development Key',
                'permissions': {'admin': True, 'kb_access': True},
                'is_active': True
            }
            
            response = supabase.table('api_keys').insert(api_key_data).execute()
            
            if response.data:
                print("✅ Successfully added Jason's API key to Supabase!")
                print(f"   User ID: {jason_user_id}")
                print(f"   Key hash: {key_hash}")
                print("   Permissions: admin, kb_access")
            else:
                print("❌ Failed to insert API key")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if "violates row-level security policy" in str(e):
            print("   Note: RLS policies may be preventing insert with anon key")
            print("   You may need to use the service key or disable RLS temporarily")

if __name__ == "__main__":
    print("Adding Jason's API Key to Supabase")
    print("==================================")
    add_jason_api_key()
    print("\nAPI Key for testing: hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY")