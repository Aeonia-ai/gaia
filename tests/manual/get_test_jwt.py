#!/usr/bin/env python3
"""
Get a JWT token for manual WebSocket testing.

This script creates or reuses a test user and obtains a JWT token
that can be used with the WebSocket test client.

Usage:
    python tests/manual/get_test_jwt.py

    # Export the token for use with test_websocket_experience.py
    export TEST_JWT_TOKEN=$(python tests/manual/get_test_jwt.py)
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
from tests.fixtures.test_auth import TestUserFactory

# Load environment
load_dotenv()


def get_jwt_token_for_user(email: str, password: str) -> str:
    """Get JWT token by signing in with email/password."""
    factory = TestUserFactory()

    try:
        # Try to sign in
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
        print(file=sys.stderr)
        print("Creating new test user...", file=sys.stderr)

        # Create new user
        try:
            user = factory.create_verified_test_user(
                email=email,
                password=password,
                role="user"
            )
            print(f"✅ Created user: {user['email']}", file=sys.stderr)
            print(f"🔑 User ID: {user['user_id']}", file=sys.stderr)

            # Now login to get token
            response = factory.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.session:
                print(f"✅ Logged in successfully", file=sys.stderr)
                print(file=sys.stderr)
                return response.session.access_token
            else:
                print("❌ Failed to get session after creation", file=sys.stderr)
                sys.exit(1)

        except Exception as create_error:
            print(f"❌ Failed to create user: {create_error}", file=sys.stderr)
            sys.exit(1)


def main():
    """Main entry point."""
    # Check for command-line arguments first, fall back to env vars
    if len(sys.argv) >= 2:
        email = sys.argv[1]
        password = sys.argv[2] if len(sys.argv) >= 3 else os.getenv("GAIA_TEST_PASSWORD", "WebSocket-Test-123!")
    else:
        # Use environment variables or defaults
        email = os.getenv("GAIA_TEST_EMAIL", "websocket-test@example.com")
        password = os.getenv("GAIA_TEST_PASSWORD", "WebSocket-Test-123!")

    # Check for required Supabase credentials
    if not os.getenv("SUPABASE_SERVICE_KEY"):
        print("❌ SUPABASE_SERVICE_KEY not found in environment", file=sys.stderr)
        print("Please add it to your .env file", file=sys.stderr)
        sys.exit(1)

    print("=" * 60, file=sys.stderr)
    print("WebSocket Test JWT Token Generator", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(file=sys.stderr)

    token = get_jwt_token_for_user(email, password)

    # Output just the token to stdout
    print(token)

    print(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("✅ Token generated successfully!", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(file=sys.stderr)
    print("Usage:", file=sys.stderr)
    print(f"  export TEST_JWT_TOKEN=\"{token[:30]}...\"", file=sys.stderr)
    print("  python tests/manual/test_websocket_experience.py", file=sys.stderr)
    print(file=sys.stderr)
    print("Or in one command:", file=sys.stderr)
    print("  export TEST_JWT_TOKEN=$(python tests/manual/get_test_jwt.py)", file=sys.stderr)


if __name__ == "__main__":
    main()
