#!/usr/bin/env python3
"""Test Supabase keys to diagnose authentication issues"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

print("🔍 Testing Supabase Keys")
print("=" * 50)
print(f"URL: {SUPABASE_URL}")
print(f"Anon Key: {SUPABASE_ANON_KEY[:20]}...")
print(f"Service Key: {SUPABASE_SERVICE_KEY[:20]}...")
print()

# Test 1: Anon key
print("1️⃣ Testing ANON key...")
response = requests.get(
    f"{SUPABASE_URL}/rest/v1/",
    headers={
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print("   ✅ Anon key is VALID")
else:
    print(f"   ❌ Anon key FAILED: {response.text[:100]}")
print()

# Test 2: Service key for admin operations
print("2️⃣ Testing SERVICE key (admin operations)...")
response = requests.get(
    f"{SUPABASE_URL}/auth/v1/admin/users?page=1&per_page=1",
    headers={
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
    }
)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print("   ✅ Service key is VALID")
    data = response.json()
    print(f"   Total users: {len(data.get('users', []))}")
else:
    print(f"   ❌ Service key FAILED: {response.text}")
print()

# Test 3: Try to decode the JWT to see what's in it
print("3️⃣ Decoding service key JWT...")
try:
    import jwt
    # Decode without verification to see the payload
    decoded = jwt.decode(SUPABASE_SERVICE_KEY, options={"verify_signature": False})
    print(f"   Role: {decoded.get('role')}")
    print(f"   Ref: {decoded.get('ref')}")
    print(f"   Issued at: {decoded.get('iat')}")
    print(f"   Expires: {decoded.get('exp')}")
    
    # Check if it matches the URL
    url_project = SUPABASE_URL.split('//')[1].split('.')[0]
    key_project = decoded.get('ref', '')
    if url_project == key_project:
        print(f"   ✅ Key matches URL project: {key_project}")
    else:
        print(f"   ❌ Key/URL mismatch! URL: {url_project}, Key: {key_project}")
except Exception as e:
    print(f"   ❌ Failed to decode: {e}")
print()

# Test 4: Try creating a test user with service key
print("4️⃣ Testing user creation with service key...")
test_user_data = {
    "email": "test-key-check@example.com",
    "password": "TestPassword123!",
    "email_confirm": True
}
response = requests.post(
    f"{SUPABASE_URL}/auth/v1/admin/users",
    headers={
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    },
    json=test_user_data
)
print(f"   Status: {response.status_code}")
if response.status_code in [200, 201]:
    print("   ✅ Can create users!")
    # Try to delete the test user
    user_id = response.json().get("id")
    if user_id:
        del_response = requests.delete(
            f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
            }
        )
        print(f"   Cleanup: {'✅' if del_response.status_code == 200 else '❌'}")
else:
    print(f"   ❌ Cannot create users: {response.text}")

print("\n" + "=" * 50)
print("Summary:")
# Check the actual response status from test 2
if response.status_code in [200, 201]:
    print("✅ Service key is valid and can create users")
else:
    print("❌ Service key is INVALID - E2E tests will fail")
    print("   You need to get the correct service_role key from:")
    print("   Supabase Dashboard → Settings → API → service_role key")