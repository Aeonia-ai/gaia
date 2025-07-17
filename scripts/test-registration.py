#!/usr/bin/env python3
"""Test user registration functionality"""

import requests
import time
import random

BASE_URL = "http://localhost:8080"

def test_registration():
    """Test the registration flow"""
    
    print("🔐 Testing User Registration")
    print("=" * 60)
    
    session = requests.Session()
    
    # Generate a test email
    random_num = random.randint(1000, 9999)
    test_email = f"test.user{random_num}@example.com"
    test_password = "TestPassword123!"
    
    print(f"\n1. Testing registration with email: {test_email}")
    
    # Try to register
    response = session.post(
        f"{BASE_URL}/auth/register",
        data={
            "email": test_email,
            "password": test_password
        },
        allow_redirects=False
    )
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 303:
        print("   ✅ Registration successful! Redirecting to chat...")
        
        # Follow redirect
        chat_response = session.get(f"{BASE_URL}/chat")
        if chat_response.status_code == 200:
            print("   ✅ Successfully logged in after registration")
            
            # Try sending a message
            print("\n2. Testing if new user can send messages...")
            msg_response = session.post(
                f"{BASE_URL}/api/chat/send",
                data={"message": "Hello! I just registered!"}
            )
            if msg_response.status_code == 200:
                print("   ✅ New user can send messages")
    else:
        # Check for error message
        if "error" in response.text or "alert" in response.text:
            print("   ❌ Registration failed")
            # Extract error message
            import re
            error_match = re.search(r'(⚠️[^<]+)', response.text)
            if error_match:
                print(f"   Error: {error_match.group(1)}")
            else:
                print(f"   Response: {response.text[:200]}...")
    
    print("\n3. Testing registration with invalid email...")
    response2 = session.post(
        f"{BASE_URL}/auth/register",
        data={
            "email": "not-an-email",
            "password": "password123"
        }
    )
    
    if "valid email" in response2.text.lower():
        print("   ✅ Correctly rejects invalid email")
    else:
        print("   ❌ Should reject invalid email format")
    
    print("\n4. Testing registration with weak password...")
    response3 = session.post(
        f"{BASE_URL}/auth/register",
        data={
            "email": "another@example.com",
            "password": "weak"
        }
    )
    
    if "password" in response3.text.lower() and ("weak" in response3.text.lower() or "short" in response3.text.lower()):
        print("   ✅ Correctly rejects weak password")
    else:
        print("   ❌ Should reject weak password")
    
    print("\n\n📝 Summary:")
    print("Registration is integrated with Supabase authentication.")
    print("\nNote: Registration may fail if:")
    print("- Supabase has email domain restrictions")
    print("- Email confirmation is required")
    print("- The email is already registered")
    print("\nTo test locally, you may need to:")
    print("1. Use a real email address")
    print("2. Check Supabase dashboard for settings")
    print("3. Disable email confirmation in Supabase (for testing)")

if __name__ == "__main__":
    test_registration()