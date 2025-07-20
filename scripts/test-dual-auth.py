#!/usr/bin/env python3
"""
Test dual authentication (API Key + Supabase JWT) in the gateway.
"""
import asyncio
import httpx
import json
import sys
from datetime import datetime, timedelta
import jwt

# Test configuration
GATEWAY_URL = "http://localhost:8666"
API_KEY = "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"
SUPABASE_JWT_SECRET = "your-secret-key-at-least-32-characters-long"  # From .env

def create_test_jwt():
    """Create a test JWT token that mimics Supabase format."""
    payload = {
        "sub": "test-user-123",  # Supabase user ID
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "user_metadata": {
            "name": "Test User"
        }
    }
    
    # Read the actual JWT secret from .env
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('SUPABASE_JWT_SECRET='):
                    secret = line.split('=', 1)[1].strip().strip('"')
                    return jwt.encode(payload, secret, algorithm="HS256")
    except:
        print("⚠️  Could not read SUPABASE_JWT_SECRET from .env")
        # Return a dummy token for testing
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"

async def test_api_key_auth():
    """Test API key authentication."""
    print("\n🔑 Testing API Key Authentication")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        response = await client.get(
            f"{GATEWAY_URL}/health",
            headers={"X-API-Key": API_KEY}
        )
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print("✅ API key auth works for health endpoint")
        else:
            print(f"❌ Failed: {response.text}")
        
        # Test streaming status
        response = await client.get(
            f"{GATEWAY_URL}/api/v0.2/chat/stream/status",
            headers={"X-API-Key": API_KEY}
        )
        print(f"\nStreaming status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API key auth works for streaming endpoints")
            print(f"   Status: {data.get('status')}")
        else:
            print(f"❌ Failed: {response.text}")

async def test_jwt_auth():
    """Test JWT authentication."""
    print("\n🔐 Testing JWT Authentication")
    print("=" * 50)
    
    jwt_token = create_test_jwt()
    print(f"Generated test JWT: {jwt_token[:50]}...")
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint (doesn't require auth)
        response = await client.get(
            f"{GATEWAY_URL}/health",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        print(f"\nHealth check: {response.status_code}")
        
        # Test streaming status
        response = await client.get(
            f"{GATEWAY_URL}/api/v0.2/chat/stream/status",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        print(f"\nStreaming status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ JWT auth works for streaming endpoints")
            print(f"   Status: {data.get('status')}")
        else:
            print(f"❌ Failed: {response.text}")

async def test_no_auth():
    """Test endpoints without authentication."""
    print("\n❌ Testing Without Authentication")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Health should work without auth
        response = await client.get(f"{GATEWAY_URL}/health")
        print(f"Health check (no auth): {response.status_code}")
        
        # Streaming endpoints should fail
        response = await client.get(f"{GATEWAY_URL}/api/v0.2/chat/stream/status")
        print(f"\nStreaming status (no auth): {response.status_code}")
        if response.status_code == 401:
            print("✅ Correctly rejected unauthenticated request")
        else:
            print(f"❌ Expected 401, got {response.status_code}")

async def test_chat_stream():
    """Test actual chat streaming with both auth methods."""
    print("\n💬 Testing Chat Streaming")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test with API key
        print("\nTesting chat with API key:")
        response = await client.post(
            f"{GATEWAY_URL}/api/v0.2/chat/stream",
            headers={"X-API-Key": API_KEY},
            json={
                "message": "Hello, this is a test",
                "model": "claude-3-haiku-20240307"
            }
        )
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Chat streaming works with API key")
        else:
            print(f"❌ Failed: {response.text}")

async def main():
    """Run all authentication tests."""
    print("🧪 Dual Authentication Test Suite")
    print("Testing API Key + Supabase JWT support")
    
    try:
        await test_api_key_auth()
        await test_jwt_auth()
        await test_no_auth()
        await test_chat_stream()
        
        print("\n✅ Test suite complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())