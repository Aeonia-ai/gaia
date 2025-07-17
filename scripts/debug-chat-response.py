#!/usr/bin/env python3
"""Debug script to check chat response handling"""

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:8080"

def debug_chat_response():
    """Debug the chat response flow"""
    
    print("🔍 Debugging Chat Response Flow")
    print("=" * 60)
    
    # Create session
    session = requests.Session()
    
    # Login
    print("\n1. Logging in...")
    session.post(f"{BASE_URL}/auth/login", 
                data={"email": "dev@gaia.local", "password": "testtest"},
                allow_redirects=False)
    session.get(f"{BASE_URL}/chat")
    print("   ✓ Logged in")
    
    # Send a message
    print("\n2. Sending a test message...")
    response = session.post(
        f"{BASE_URL}/api/chat/send",
        data={"message": "What is 2+2?"}
    )
    
    print(f"   Status: {response.status_code}")
    print(f"\n   Raw HTML Response:\n{'-'*50}")
    print(response.text[:1000])
    print(f"{'-'*50}")
    
    # Parse the response to check HTMX attributes
    if response.status_code == 200:
        # Look for hx-get attribute
        if 'hx-get="/api/chat/response' in response.text:
            print("\n   ✓ Found HTMX get request to /api/chat/response")
            
            # Extract the URL
            import re
            match = re.search(r'hx-get="([^"]+)"', response.text)
            if match:
                response_url = match.group(1)
                print(f"   Response URL: {response_url}")
                
                # Try to fetch the response manually
                print("\n3. Manually fetching AI response...")
                ai_response = session.get(f"{BASE_URL}{response_url}")
                print(f"   Status: {ai_response.status_code}")
                print(f"\n   AI Response:\n{'-'*50}")
                print(ai_response.text[:500])
                print(f"{'-'*50}")
        else:
            print("\n   ❌ No HTMX get request found in response")
    
    # Check conversation messages
    print("\n4. Checking stored messages...")
    conv_response = session.get(f"{BASE_URL}/api/conversations")
    if 'href="/chat/' in conv_response.text:
        # Extract first conversation ID
        match = re.search(r'href="/chat/([^"]+)"', conv_response.text)
        if match:
            conv_id = match.group(1)
            print(f"   Found conversation: {conv_id}")
            
            # Load the conversation
            conv_detail = session.get(f"{BASE_URL}/chat/{conv_id}")
            
            # Count messages
            user_msgs = conv_detail.text.count('justify-end')  # User messages
            ai_msgs = conv_detail.text.count('justify-start')  # AI messages
            
            print(f"   User messages: {user_msgs}")
            print(f"   AI messages: {ai_msgs}")

if __name__ == "__main__":
    debug_chat_response()