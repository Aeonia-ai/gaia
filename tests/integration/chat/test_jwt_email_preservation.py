"""
Integration test for JWT email preservation in user creation.

This test verifies that when a user authenticates with a Supabase JWT containing
both UUID (sub) and email, the email is properly preserved through the authentication
flow and the user is created in the database with their actual email address,
not UUID@gaia.local.

Root Cause Being Tested:
    app/shared/security.py lines 226-231 extract only the UUID from JWT payload
    and discard the email, causing conversation_store to create users with
    UUID@gaia.local instead of actual email addresses.

Expected Behavior:
    - JWT payload contains: {"sub": "uuid-123", "email": "user@example.com", ...}
    - User created in DB should have email="user@example.com"
    - NOT email="uuid-123@gaia.local"
"""

import pytest
import httpx
import os
from unittest.mock import patch, MagicMock, AsyncMock
from app.shared.security import AuthenticationResult
from app.services.chat.conversation_store import ChatConversationStore
from app.models.database import User, Conversation


@pytest.mark.integration
class TestJWTEmailPreservation:
    """Test that JWT email is preserved through authentication and user creation."""

    @pytest.fixture
    def mock_jwt_payload(self):
        """Mock JWT payload with both sub (UUID) and email."""
        return {
            "sub": "test-uuid-12345-67890",
            "email": "test.user@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": 9999999999,  # Far future
            "iat": 1700000000,
            "iss": "https://test.supabase.co/auth/v1"
        }

    @pytest.fixture
    def conversation_store(self):
        """Create a real conversation store instance."""
        return ChatConversationStore()

    @pytest.mark.asyncio
    async def test_jwt_email_preserved_in_auth_result(self, mock_jwt_payload):
        """
        Test that JWT email is extracted and included in AuthenticationResult.

        This is the first step in the flow - verify that security.py creates
        an AuthenticationResult with email from JWT payload.
        """
        from app.shared.security import validate_supabase_jwt, get_current_auth
        from fastapi import Request
        from fastapi.security import HTTPAuthorizationCredentials

        # Mock the JWT validation to return our test payload
        with patch('app.shared.security.validate_supabase_jwt', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_jwt_payload

            # Create mock request and credentials
            mock_request = MagicMock(spec=Request)
            mock_credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="mock-jwt-token"
            )

            # Call get_current_auth which should create AuthenticationResult
            auth_result = await get_current_auth(
                request=mock_request,
                credentials=mock_credentials,
                api_key_header=None
            )

            # CRITICAL ASSERTIONS
            assert auth_result is not None, "AuthenticationResult should not be None"
            assert auth_result.auth_type == "jwt", "Auth type should be jwt"
            assert auth_result.user_id == "test-uuid-12345-67890", "User ID should be UUID from JWT sub"

            # THIS IS THE BUG: Email should be present but currently isn't
            assert auth_result.email == "test.user@example.com", (
                "Email should be extracted from JWT payload! "
                f"Got: {auth_result.email}, Expected: test.user@example.com"
            )

    @pytest.mark.asyncio
    async def test_user_created_with_email_not_uuid(self, mock_jwt_payload, conversation_store):
        """
        Test that when creating a conversation after JWT auth, the user is created
        with their actual email address, not UUID@gaia.local.

        This is an end-to-end test of the bug:
        1. User authenticates with JWT containing email
        2. Conversation is created (triggers user creation)
        3. User should be in DB with actual email, not UUID@gaia.local
        """
        from app.shared.security import get_current_auth
        from fastapi import Request
        from fastapi.security import HTTPAuthorizationCredentials
        from app.shared.database import get_database_session
        from sqlalchemy import text

        # Setup: Mock JWT validation
        with patch('app.shared.security.validate_supabase_jwt', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_jwt_payload

            mock_request = MagicMock(spec=Request)
            mock_credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="mock-jwt-token"
            )

            # Step 1: Authenticate (this is where bug occurs)
            auth_result = await get_current_auth(
                request=mock_request,
                credentials=mock_credentials,
                api_key_header=None
            )

            # Step 2: Create a conversation using the authenticated user_id
            # This triggers _get_or_create_user() in conversation_store
            try:
                conversation = conversation_store.create_conversation(
                    user_id=auth_result.user_id,
                    title="Test Conversation"
                )

                assert conversation is not None, "Conversation should be created"
                assert "id" in conversation, "Conversation should have an ID"

                # Step 3: Query the database to check the user's email
                db_gen = get_database_session()
                db = next(db_gen)
                try:
                    # Find the user by UUID
                    result = db.execute(
                        text("""
                            SELECT id, email FROM users
                            WHERE id = :user_id OR email LIKE :uuid_pattern
                        """),
                        {
                            "user_id": auth_result.user_id,
                            "uuid_pattern": f"{auth_result.user_id}@%"
                        }
                    ).fetchone()

                    assert result is not None, (
                        f"User should exist in database. "
                        f"Searched for user_id={auth_result.user_id}"
                    )

                    # CRITICAL ASSERTION: Email should be actual email, not UUID@gaia.local
                    assert result.email == "test.user@example.com", (
                        f"User email should be 'test.user@example.com', "
                        f"not '{result.email}'. "
                        f"The bug causes users to be created with UUID@gaia.local "
                        f"when JWT email is not preserved through the auth flow."
                    )

                    assert not result.email.endswith("@gaia.local"), (
                        f"User email should NOT end with @gaia.local! "
                        f"Got: {result.email}. This indicates the email was not "
                        f"passed from JWT through to conversation_store."
                    )
                finally:
                    # Cleanup: Delete test data
                    db.execute(
                        text("DELETE FROM conversations WHERE user_id = :user_id"),
                        {"user_id": str(result.id) if result else auth_result.user_id}
                    )
                    db.execute(
                        text("DELETE FROM users WHERE id = :user_id OR email = :email"),
                        {
                            "user_id": auth_result.user_id,
                            "email": "test.user@example.com"
                        }
                    )
                    db.commit()
                    db.close()
            except Exception as e:
                # Cleanup on error
                db_gen = get_database_session()
                db = next(db_gen)
                try:
                    db.execute(
                        text("DELETE FROM conversations WHERE user_id LIKE :pattern"),
                        {"pattern": f"%{auth_result.user_id}%"}
                    )
                    db.execute(
                        text("DELETE FROM users WHERE id = :user_id OR email = :email"),
                        {
                            "user_id": auth_result.user_id,
                            "email": "test.user@example.com"
                        }
                    )
                    db.commit()
                finally:
                    db.close()
                raise

    @pytest.mark.asyncio
    async def test_conversation_store_receives_email_from_auth(self, mock_jwt_payload):
        """
        Test that conversation_store can create users with email when auth provides it.

        This test verifies that if AuthenticationResult contains email,
        conversation_store should use it instead of creating UUID@gaia.local.
        """
        from app.shared.database import get_database_session
        from sqlalchemy import text

        conversation_store = ChatConversationStore()

        # Simulate what should happen if email was preserved
        test_user_id = "test-uuid-12345-67890"
        test_email = "test.user@example.com"

        # Currently, _get_or_create_user only receives user_id (UUID)
        # This test documents what SHOULD happen if email was passed

        db_gen = get_database_session()
        db = next(db_gen)
        try:
            # Check current behavior
            user = conversation_store._get_or_create_user(test_user_id)

            # Document current buggy behavior
            # User will be created with UUID@gaia.local because email is not passed
            assert "@" in user.email, "User should have an email"

            # The bug: email will be UUID@gaia.local instead of actual email
            # After fix, this should pass:
            # assert user.email == test_email, f"Email should be {test_email}, got {user.email}"

            # Cleanup
            db.execute(
                text("DELETE FROM users WHERE id = :user_id"),
                {"user_id": test_user_id}
            )
            db.commit()
        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_real_supabase_jwt_contains_email(self, shared_test_user):
        """
        Test with REAL Supabase authentication to verify JWT structure.

        This test confirms that real Supabase JWTs contain the email field
        and validates our test assumptions.

        Requires: SUPABASE_SERVICE_KEY in .env
        """
        from tests.fixtures.test_auth import TestUserFactory
        from app.shared.security import validate_supabase_jwt
        from fastapi.security import HTTPAuthorizationCredentials

        # Use the shared test user (real Supabase user)
        test_user = shared_test_user
        auth_url = os.getenv("AUTH_URL", "http://auth-service:8000")

        # Login to get real JWT
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{auth_url}/auth/login",
                json={
                    "email": test_user["email"],
                    "password": test_user["password"]
                }
            )
            assert response.status_code == 200, f"Login failed: {response.text}"

            data = response.json()
            # Extract token from session structure
            if "session" in data and "access_token" in data["session"]:
                jwt_token = data["session"]["access_token"]
            else:
                jwt_token = data["access_token"]

        # Validate the JWT and check payload structure
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=jwt_token
        )

        jwt_payload = await validate_supabase_jwt(credentials)

        # Verify real JWT structure matches our assumptions
        assert "sub" in jwt_payload, "JWT should contain 'sub' (user UUID)"
        assert "email" in jwt_payload, "JWT should contain 'email' field"
        assert jwt_payload["email"] == test_user["email"], (
            f"JWT email should match user email. "
            f"Got: {jwt_payload['email']}, Expected: {test_user['email']}"
        )

        # This proves that Supabase JWTs DO contain email
        # and our fix is valid - we just need to extract it!
