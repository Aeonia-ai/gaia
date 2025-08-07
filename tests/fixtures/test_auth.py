"""
Test authentication utilities for Gaia platform tests.

Provides both JWT-based auth for unit tests and real Supabase user creation
for integration tests using the service key.
"""
import os
import jwt
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class TestUserFactory:
    """Creates test users with email pre-verified using Supabase service key."""
    
    def __init__(self):
        """Initialize with Supabase admin client using service key."""
        supabase_url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for integration tests")
        
        # Import here to avoid dependency issues in unit tests
        from supabase import create_client
        self.client = create_client(supabase_url, service_key)
        self.created_users: List[str] = []
        
    def create_verified_test_user(self, 
                                 email: Optional[str] = None,
                                 password: Optional[str] = None,
                                 role: str = "user") -> Dict[str, str]:
        """
        Create a test user with email already verified.
        
        Args:
            email: Optional email (generated if not provided)
            password: Optional password (generated if not provided)
            role: User role (user, admin, etc.)
            
        Returns:
            Dict with user_id, email, password
        """
        if not email:
            email = f"test-{uuid.uuid4().hex[:8]}@test.local"
        if not password:
            password = f"Test-{uuid.uuid4().hex[:8]}-123!"
            
        try:
            # Create user with email pre-verified
            response = self.client.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,  # Bypass email verification
                "send_email": False,    # Prevent sending ANY emails
                "user_metadata": {
                    "test_user": True,
                    "role": role,
                    "created_at": datetime.now().isoformat()
                }
            })
            
            user_id = response.user.id
            self.created_users.append(user_id)
            
            logger.info(f"Created test user: {email} with ID: {user_id}")
            
            return {
                "user_id": user_id,
                "email": email,
                "password": password
            }
        except Exception as e:
            logger.error(f"Failed to create test user: {e}")
            raise
            
    def cleanup_test_user(self, user_id: str):
        """Delete a specific test user."""
        try:
            self.client.auth.admin.delete_user(user_id)
            if user_id in self.created_users:
                self.created_users.remove(user_id)
            logger.info(f"Deleted test user: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to delete test user {user_id}: {e}")
    
    def cleanup_user_by_email(self, email: str):
        """Delete a test user by email address."""
        try:
            # First, we need to get the user by email
            # Using the admin API to list users with filter
            response = self.client.auth.admin.list_users()
            
            # Find the user with matching email
            for user in response:
                if user.email == email:
                    self.client.auth.admin.delete_user(user.id)
                    logger.info(f"Deleted test user by email: {email} (ID: {user.id})")
                    return True
                    
            logger.warning(f"No user found with email: {email}")
            return False
        except Exception as e:
            logger.warning(f"Failed to delete test user by email {email}: {e}")
            return False
            
    def cleanup_all(self):
        """Delete all test users created by this factory."""
        for user_id in self.created_users[:]:  # Copy list to avoid modification during iteration
            self.cleanup_test_user(user_id)


class JWTTestAuth:
    """Provides JWT-based authentication for unit tests without Supabase."""
    
    def __init__(self):
        """Initialize with JWT secret from environment."""
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if not self.jwt_secret:
            # Use a test secret for unit tests
            self.jwt_secret = "test-secret-for-unit-tests-only"
            
    def create_test_token(self, 
                         user_id: Optional[str] = None,
                         email: Optional[str] = None,
                         role: str = "authenticated",
                         expires_in: int = 3600) -> str:
        """
        Create a valid JWT token for testing.
        
        Args:
            user_id: User ID (generated if not provided)
            email: User email (generated if not provided)
            role: User role
            expires_in: Token expiration in seconds
            
        Returns:
            JWT token string
        """
        if not user_id:
            user_id = str(uuid.uuid4())
        if not email:
            email = f"test-{uuid.uuid4().hex[:8]}@test.local"
            
        now = int(time.time())
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "aud": "authenticated",
            "iat": now,
            "exp": now + expires_in,
            "email_verified": True,
            "app_metadata": {
                "provider": "email",
                "providers": ["email"]
            },
            "user_metadata": {
                "test_user": True
            }
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        
    def create_auth_headers(self, **kwargs) -> Dict[str, str]:
        """
        Create authorization headers with a test JWT.
        
        Args:
            **kwargs: Arguments passed to create_test_token
            
        Returns:
            Dict with Authorization header
        """
        token = self.create_test_token(**kwargs)
        return {"Authorization": f"Bearer {token}"}
        
    def create_test_api_key(self) -> str:
        """Create a test API key format."""
        # For unit tests, return a recognizable test key
        return f"test_{uuid.uuid4().hex}"


class TestAuthManager:
    """
    Unified test authentication manager that provides appropriate
    auth strategy based on test type.
    """
    
    def __init__(self, test_type: str = "unit"):
        """
        Initialize with test type.
        
        Args:
            test_type: "unit" for JWT-only, "integration" for real Supabase
        """
        self.test_type = test_type
        self.jwt_auth = JWTTestAuth()
        self.user_factory = None
        
        if test_type == "integration":
            try:
                self.user_factory = TestUserFactory()
            except ValueError as e:
                logger.warning(f"Cannot initialize user factory: {e}")
                
    def get_auth_headers(self, **kwargs) -> Dict[str, str]:
        """Get appropriate auth headers for the test type."""
        if self.test_type == "unit":
            return self.jwt_auth.create_auth_headers(**kwargs)
        else:
            # For integration tests, create a real user and login
            if not self.user_factory:
                raise RuntimeError("User factory not available for integration tests")
            user = self.user_factory.create_verified_test_user()
            # Return headers with a real token (would need login endpoint call)
            # For now, return a JWT that matches the created user
            return self.jwt_auth.create_auth_headers(
                user_id=user["user_id"],
                email=user["email"]
            )
            
    def create_test_user(self, **kwargs) -> Dict[str, str]:
        """Create a test user (only for integration tests)."""
        if self.test_type != "integration":
            raise RuntimeError("Test user creation only available in integration tests")
        if not self.user_factory:
            raise RuntimeError("User factory not initialized")
        return self.user_factory.create_verified_test_user(**kwargs)
        
    def cleanup(self):
        """Cleanup any created resources."""
        if self.user_factory:
            self.user_factory.cleanup_all()


# Pre-configured test users for different scenarios
TEST_USERS = {
    "default": {
        "email": "test@test.local",
        "password": "TestPassword123!",
        "role": "user"
    },
    "admin": {
        "email": "admin@test.local", 
        "password": "AdminPassword123!",
        "role": "admin"
    },
    "viewer": {
        "email": "viewer@test.local",
        "password": "ViewerPassword123!",
        "role": "viewer"
    }
}