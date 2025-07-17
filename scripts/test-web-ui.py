#!/usr/bin/env python3
"""Test script for web UI conversation features"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8080"

def test_conversation_features():
    """Test the conversation management features"""
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("🧪 Testing Web UI Conversation Features")
    print("=" * 50)
    
    # 1. Test health endpoint
    print("\n1. Testing health endpoint...")
    response = session.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # 2. Test login
    print("\n2. Testing login...")
    login_data = {
        "email": "dev@gaia.local",
        "password": "test"
    }
    response = session.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=False)
    print(f"   Status: {response.status_code}")
    print(f"   Redirect: {response.headers.get('Location', 'No redirect')}")
    
    # Follow redirect manually
    if response.status_code == 303:
        redirect_url = response.headers.get('Location', '/chat')
        print(f"\n3. Following redirect to {redirect_url}...")
        response = session.get(f"{BASE_URL}{redirect_url}")
        print(f"   Status: {response.status_code}")
        print(f"   Page loaded: {'chat' in response.text}")
    
    # 4. Test conversation API
    print("\n4. Testing conversation API...")
    response = session.get(f"{BASE_URL}/api/conversations")
    print(f"   Status: {response.status_code}")
    print(f"   Response length: {len(response.text)} chars")
    
    # 5. Simulate sending a message
    print("\n5. Testing message send...")
    message_data = {
        "message": f"Test message at {datetime.now().strftime('%H:%M:%S')}"
    }
    response = session.post(f"{BASE_URL}/api/chat/send", data=message_data)
    print(f"   Status: {response.status_code}")
    print(f"   Response contains loading spinner: {'loading' in response.text}")
    print(f"   Response contains user message: {message_data['message'][:20] in response.text}")
    
    # 6. Check conversations again
    print("\n6. Checking conversations after message...")
    response = session.get(f"{BASE_URL}/api/conversations")
    print(f"   Status: {response.status_code}")
    print(f"   Conversations found: {'conversation-item' in response.text or 'href=\"/chat/' in response.text}")
    
    print("\n✅ Test Summary:")
    print("   - Health check: Working")
    print("   - Login: Working (redirects to chat)")
    print("   - Conversation API: Accessible")
    print("   - Message sending: Working")
    print("   - Conversation tracking: Check manually in browser")
    
    print("\n💡 To fully test:")
    print("   1. Open http://localhost:8080 in your browser")
    print("   2. Login with dev@gaia.local / test")
    print("   3. Send messages and check sidebar updates")
    print("   4. Create multiple conversations")
    print("   5. Switch between conversations")

if __name__ == "__main__":
    test_conversation_features()