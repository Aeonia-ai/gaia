"""
Shared test user management for the entire test suite.

Creates a single test user (pytest@aeonia.ai) at the start of the test run
and reuses it for all tests, dramatically reducing email sending.
"""
import os
import logging
from typing import Dict, Optional
from tests.fixtures.test_auth import TestUserFactory

logger = logging.getLogger(__name__)

# Global shared test user
_SHARED_TEST_USER: Optional[Dict[str, str]] = None
_TEST_USER_EMAIL = "pytest@aeonia.ai"
_TEST_USER_PASSWORD = "PyTest-Aeonia-2025!"


class SharedTestUser:
    """Manages a single shared test user for the entire test run."""
    
    @classmethod
    def get_or_create(cls) -> Dict[str, str]:
        """
        Get or create the shared test user.
        
        Returns:
            Dict with user_id, email, password
        """
        global _SHARED_TEST_USER
        
        if _SHARED_TEST_USER is not None:
            logger.debug(f"Reusing shared test user: {_TEST_USER_EMAIL}")
            return _SHARED_TEST_USER
        
        try:
            # Create the shared test user
            factory = TestUserFactory()
            
            # First, try to delete any existing user with this email
            # This handles cases where previous test runs didn't clean up
            try:
                # Note: We can't easily check if user exists without trying to create
                # So we'll just try to create and handle the error
                pass
            except Exception:
                pass
            
            logger.info(f"Creating shared test user: {_TEST_USER_EMAIL}")
            user = factory.create_verified_test_user(
                email=_TEST_USER_EMAIL,
                password=_TEST_USER_PASSWORD,
                role="user"
            )
            
            _SHARED_TEST_USER = user
            logger.info(f"Shared test user created successfully: {user['user_id']}")
            
            return user
            
        except Exception as e:
            # If user already exists, that's fine - just use it
            if "already registered" in str(e).lower() or "already exists" in str(e).lower():
                logger.info(f"Shared test user already exists: {_TEST_USER_EMAIL}")
                _SHARED_TEST_USER = {
                    "email": _TEST_USER_EMAIL,
                    "password": _TEST_USER_PASSWORD,
                    "user_id": "existing"  # We don't know the ID, but that's ok
                }
                return _SHARED_TEST_USER
            else:
                logger.error(f"Failed to create shared test user: {e}")
                raise
    
    @classmethod
    def get_credentials(cls) -> Dict[str, str]:
        """Get email and password for the shared test user."""
        user = cls.get_or_create()
        return {
            "email": user["email"],
            "password": user["password"]
        }
    
    @classmethod
    def cleanup(cls):
        """
        Cleanup the shared test user.
        Note: We intentionally DON'T delete the user to avoid recreation on next run.
        """
        global _SHARED_TEST_USER
        if _SHARED_TEST_USER and _SHARED_TEST_USER.get("user_id") != "existing":
            logger.info(f"Keeping shared test user for future runs: {_TEST_USER_EMAIL}")
        _SHARED_TEST_USER = None


# Pytest fixtures
import pytest

@pytest.fixture(scope="session")
def shared_test_user():
    """
    Session-scoped fixture that provides the shared test user.
    Created once per test run, reused by all tests.
    """
    user = SharedTestUser.get_or_create()
    yield user
    # Don't cleanup - keep for next run
    SharedTestUser.cleanup()


@pytest.fixture(scope="function")
def test_user_credentials(shared_test_user):
    """
    Function-scoped fixture for easy access to credentials.
    """
    return {
        "email": shared_test_user["email"],
        "password": shared_test_user["password"]
    }


# For backward compatibility
def get_test_user_credentials() -> Dict[str, str]:
    """Get credentials for the shared test user (for non-fixture usage)."""
    return SharedTestUser.get_credentials()