#!/usr/bin/env python3
"""
Get a JWT token for a specific existing user by signing them in.

Usage:
    python tests/manual/get_user_jwt.py jason@aeonia.ai
    export TEST_JWT_TOKEN=$(python tests/manual/get_user_jwt.py jason@aeonia.ai password)
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
from tests.fixtures.test_auth import TestUserFactory

# Load environment
load_dotenv()


def get_jwt_for_user(email: str, password: str) -> str:
    """Get JWT token by signing in with email/password."""
    factory = TestUserFactory()

    try:
        # Sign in with provided credentials
        response = factory.client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if response.session:
            print(f"✅ Logged in as: {email}", file=sys.stderr)
            print(f"🔑 User ID: {response.user.id}", file=sys.stderr)
            print(f"⏰ Token expires: {response.session.expires_at}", file=sys.stderr)
            print(file=sys.stderr)
            # Return just the token to stdout (for export)
            return response.session.access_token
        else:
            print("❌ Login failed: No session returned", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"❌ Login failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python get_user_jwt.py <email> [password]", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  python get_user_jwt.py jason@aeonia.ai mypassword", file=sys.stderr)
        print("  export TEST_JWT_TOKEN=$(python get_user_jwt.py jason@aeonia.ai mypassword)", file=sys.stderr)
        sys.exit(1)

    email = sys.argv[1]

    # Get password from args or prompt
    if len(sys.argv) >= 3:
        password = sys.argv[2]
    else:
        import getpass
        password = getpass.getpass(f"Password for {email}: ")

    # Check for required Supabase credentials
    if not os.getenv("SUPABASE_SERVICE_KEY"):
        print("❌ SUPABASE_SERVICE_KEY not found in environment", file=sys.stderr)
        print("Please add it to your .env file", file=sys.stderr)
        sys.exit(1)

    print("=" * 60, file=sys.stderr)
    print(f"Getting JWT Token for: {email}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(file=sys.stderr)

    token = get_jwt_for_user(email, password)

    # Output just the token to stdout
    print(token)

    print(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("✅ Token generated successfully!", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(file=sys.stderr)
    print("To use with WebSocket test:", file=sys.stderr)
    print(f"  export TEST_JWT_TOKEN=$(python tests/manual/get_user_jwt.py {email} {password})", file=sys.stderr)
    print("  python tests/manual/test_websocket_experience.py", file=sys.stderr)


if __name__ == "__main__":
    main()
