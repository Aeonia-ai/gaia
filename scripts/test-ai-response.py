#!/usr/bin/env python3
"""Test if AI responses are now showing up"""

import requests
import time

BASE_URL = "http://localhost:8080"

def test_ai_response():
    """Test AI response display"""
    
    print("🤖 Testing AI Response Display")
    print("=" * 60)
    
    session = requests.Session()
    
    # Login
    print("\n1. Logging in...")
    session.post(f"{BASE_URL}/auth/login", 
                data={"email": "dev@gaia.local", "password": "test"},
                allow_redirects=False)
    session.get(f"{BASE_URL}/chat")
    print("   ✓ Logged in")
    
    # Create new chat to ensure clean state
    print("\n2. Creating new chat...")
    session.post(f"{BASE_URL}/chat/new")
    
    # Send a simple math question
    print("\n3. Sending test message: 'What is 5 + 3?'")
    response = session.post(
        f"{BASE_URL}/api/chat/send",
        data={"message": "What is 5 + 3?"}
    )
    
    if response.status_code == 200:
        print("   ✓ Message sent successfully")
        
        # Extract conversation ID
        import re
        conv_match = re.search(r'conversation_id=([^"&]+)', response.text)
        if conv_match:
            conv_id = conv_match.group(1)
            print(f"   📌 Conversation ID: {conv_id}")
            
            # Wait a moment for response to process
            print("\n4. Waiting for AI response...")
            time.sleep(3)
            
            # Load the conversation to check messages
            print("\n5. Loading conversation to check messages...")
            conv_response = session.get(f"{BASE_URL}/chat/{conv_id}")
            
            # Count message types
            user_count = conv_response.text.count('from-purple-600 to-pink-600')
            ai_count = conv_response.text.count('bg-slate-700')
            
            print(f"\n   📊 Message Count:")
            print(f"      User messages: {user_count}")
            print(f"      AI messages: {ai_count}")
            
            # Check if "8" appears in response (5+3=8)
            if "8" in conv_response.text:
                print("\n   ✅ AI response contains the answer '8'")
            else:
                print("\n   ❌ AI response doesn't contain expected answer")
                
            # Extract actual AI message if present
            ai_match = re.search(r'bg-slate-700.*?>(.*?)</div>', conv_response.text, re.DOTALL)
            if ai_match:
                content = ai_match.group(1)
                # Look for the actual message content
                msg_match = re.search(r'break-words">(.*?)</div>', content)
                if msg_match:
                    print(f"\n   💬 AI Response: '{msg_match.group(1)}'")
    
    print("\n\n💡 Next Steps:")
    print("1. Open http://localhost:8080 in your browser")
    print("2. Login and check if AI responses are visible")
    print("3. If not visible, check browser console for errors")

if __name__ == "__main__":
    test_ai_response()