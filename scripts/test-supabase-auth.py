#\!/usr/bin/env python3
"""Test Supabase authentication directly"""
import os
import sys
import asyncio
import hashlib
from supabase import create_client

# Test configuration
SUPABASE_URL = "https://lbaohvnusingoztdzlmj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxiYW9odm51c2luZ296dGR6bG1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIwNzc3MTksImV4cCI6MjA2NzY1MzcxOX0.HPv55m2XpO4RRxYQKg3C1Zt_96qh54YI-aleSTSsGuI"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"

async def test_supabase_auth():
    """Test API key validation through Supabase"""
    print(f"Testing Supabase authentication...")
    print(f"Supabase URL: {SUPABASE_URL}")
    
    # Create Supabase client
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    
    # Hash the API key
    key_hash = hashlib.sha256(API_KEY.encode()).hexdigest()
    print(f"API Key Hash: {key_hash}")
    
    try:
        # Call the validation function
        response = client.rpc(
            'validate_api_key_simple',
            {'key_hash_input': key_hash}
        ).execute()
        
        print(f"\nValidation Response:")
        print(f"Data: {response.data}")
        
        if response.data and len(response.data) > 0:
            result = response.data[0]
            print(f"\nValidation Result:")
            print(f"  Valid: {result.get('is_valid')}")
            print(f"  User ID: {result.get('user_id')}")
            print(f"  Permissions: {result.get('permissions')}")
        else:
            print("No validation result returned")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        
if __name__ == "__main__":
    asyncio.run(test_supabase_auth())
