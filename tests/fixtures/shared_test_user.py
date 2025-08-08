"""
Shared test user management for the entire test suite.

Creates a single test user from environment variables at the start of the test run
and reuses it for all tests, dramatically reducing email sending.
"""
import os
import logging
import threading
import time
from typing import Dict, Optional
from tests.fixtures.test_auth import TestUserFactory
from gotrue.errors import AuthApiError

logger = logging.getLogger(__name__)

# Global shared test user with thread-safe access
_SHARED_TEST_USER: Optional[Dict[str, str]] = None
_TEST_USER_EMAIL = os.getenv("GAIA_TEST_EMAIL", "test@example.com")
_TEST_USER_PASSWORD = os.getenv("GAIA_TEST_PASSWORD", "default-test-password")
_USER_LOCK = threading.Lock()


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
        
        with _USER_LOCK:
            if _SHARED_TEST_USER is not None:
                logger.debug(f"Reusing shared test user: {_TEST_USER_EMAIL}")
                return _SHARED_TEST_USER
            
            # Create the shared test user
            factory = TestUserFactory()
            
            # First, try to login with existing user
            try:
                logger.info(f"Attempting to login with existing user: {_TEST_USER_EMAIL}")
                response = factory.client.auth.sign_in_with_password({
                    "email": _TEST_USER_EMAIL,
                    "password": _TEST_USER_PASSWORD
                })
                
                if response.user:
                    logger.info(f"Using existing shared test user: {response.user.id}")
                    _SHARED_TEST_USER = {
                        "email": _TEST_USER_EMAIL,
                        "password": _TEST_USER_PASSWORD,
                        "user_id": response.user.id
                    }
                    return _SHARED_TEST_USER
            except Exception as e:
                logger.debug(f"Login failed, will try to create user: {e}")
            
            # If login failed, try to create the user
            try:
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
                # If creation failed due to user existing, try to login instead
                if "already registered" in str(e).lower() or "already exists" in str(e).lower() or "email_exists" in str(e).lower():
                    logger.info(f"User already exists, attempting to login to get user ID")
                    try:
                        # Try to login with the credentials
                        response = factory.client.auth.sign_in_with_password({
                            "email": _TEST_USER_EMAIL,
                            "password": _TEST_USER_PASSWORD
                        })
                        
                        if response.user:
                            logger.info(f"Successfully logged in existing shared test user: {response.user.id}")
                            _SHARED_TEST_USER = {
                                "email": _TEST_USER_EMAIL,
                                "password": _TEST_USER_PASSWORD,
                                "user_id": response.user.id
                            }
                            return _SHARED_TEST_USER
                    except Exception as login_error:
                        logger.warning(f"Failed to login with existing user: {login_error}")
                        
                    # If login failed, return credentials anyway for tests that don't need user ID
                    logger.warning("User exists but login failed, returning credentials without user_id")
                    _SHARED_TEST_USER = {
                        "email": _TEST_USER_EMAIL,
                        "password": _TEST_USER_PASSWORD,
                        "user_id": "existing"
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
        Cleanup the shared test user by deleting it from Supabase.
        """
        global _SHARED_TEST_USER
        if _SHARED_TEST_USER and _SHARED_TEST_USER.get("user_id") not in ["existing", "unknown"]:
            try:
                factory = TestUserFactory()
                factory.cleanup_test_user(_SHARED_TEST_USER["user_id"])
                logger.info(f"Deleted shared test user: {_TEST_USER_EMAIL}")
            except Exception as e:
                logger.warning(f"Failed to delete shared test user: {e}")
        _SHARED_TEST_USER = None


# Pytest fixtures
import pytest

@pytest.fixture(scope="session")
def shared_test_user():
    """
    Session-scoped fixture that provides the shared test user.
    Created once per test run, reused by all tests, deleted at end.
    """
    user = SharedTestUser.get_or_create()
    yield user
    # Cleanup after all tests are done
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