#!/usr/bin/env python3
"""
Test script to verify Supabase service key functionality.
This confirms we can create pre-verified test users.
"""
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_service_key():
    """Test if service key can create and delete users"""
    try:
        from supabase import create_client
        
        # Get credentials
        supabase_url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not service_key:
            print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
            return False
            
        print(f"📡 Connecting to Supabase at {supabase_url[:30]}...")
        
        # Create client with service key
        client = create_client(supabase_url, service_key)
        
        # Try to create a test user
        test_email = f"test-verify-{datetime.now().strftime('%Y%m%d%H%M%S')}@test.local"
        print(f"🧪 Creating test user: {test_email}")
        
        response = client.auth.admin.create_user({
            "email": test_email,
            "password": "TestPassword123!",
            "email_confirm": True,  # This requires service key privileges
            "user_metadata": {
                "test_user": True,
                "created_at": datetime.now().isoformat()
            }
        })
        
        user_id = response.user.id
        print(f"✅ Success! Created user: {response.user.email}")
        print(f"   User ID: {user_id}")
        print(f"   Email verified: {response.user.email_confirmed_at is not None}")
        
        # Clean up - delete the test user
        print(f"🧹 Cleaning up test user...")
        client.auth.admin.delete_user(user_id)
        print("✅ Cleanup successful!")
        
        print("\n🎉 Service key is working correctly!")
        print("   You can now run integration tests with real Supabase users.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPossible issues:")
        print("1. Service key not set or invalid")
        print("2. Supabase URL incorrect")
        print("3. Service key doesn't have admin privileges")
        print("\nMake sure you're using the service role key, not the anon key!")
        return False


if __name__ == "__main__":
    success = test_service_key()
    sys.exit(0 if success else 1)