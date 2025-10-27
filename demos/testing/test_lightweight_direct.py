#!/usr/bin/env python3
"""
Direct test of lightweight chat functionality without router
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append('/app')

from app.services.chat.lightweight_chat import lightweight_chat_endpoint
from app.models.chat import ChatRequest

async def test_lightweight_direct():
    """Test lightweight chat directly"""
    print("Testing lightweight chat endpoint directly...")
    
    # Create a test request
    request = ChatRequest(
        message="Hello, this is a test message",
        model="claude-sonnet-4-5"
    )
    
    # Mock auth principal
    auth_principal = {"sub": "test-user", "type": "api_key"}
    
    try:
        result = await lightweight_chat_endpoint(request, auth_principal)
        print(f"✅ Success! Response: {result}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_lightweight_direct())
    exit(0 if success else 1)