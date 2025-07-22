"""
Supabase-based authentication for API keys.
Provides centralized API key validation across all environments.
"""
import os
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from supabase import create_client, Client
from app.shared.security import AuthenticationResult

logger = logging.getLogger(__name__)

class SupabaseAuthClient:
    """Client for Supabase-based authentication operations."""
    
    def __init__(self):
        """Initialize Supabase client with service role key for auth operations."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")  # Service role key for backend
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")  # Fallback to anon key
        
        if not supabase_url:
            raise ValueError("SUPABASE_URL must be set")
        
        # Use service key if available, otherwise use anon key
        supabase_key = supabase_service_key or supabase_anon_key
        if not supabase_key:
            raise ValueError("Either SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        logger.info(f"Supabase auth client initialized (using {'service' if supabase_service_key else 'anon'} key)")
    
    async def validate_api_key(self, api_key: str) -> Optional[AuthenticationResult]:
        """
        Validate an API key against Supabase.
        
        Args:
            api_key: The raw API key to validate
            
        Returns:
            AuthenticationResult if valid, None if invalid
        """
        try:
            # Hash the API key
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Call the validate_api_key function in Supabase
            # Try the simple version first (works with anon key)
            try:
                response = self.client.rpc(
                    'validate_api_key_simple',
                    {'key_hash_input': key_hash}
                ).execute()
            except Exception:
                # Fall back to full version if available
                response = self.client.rpc(
                    'validate_api_key',
                    {'key_hash_input': key_hash}
                ).execute()
            
            if response.data and len(response.data) > 0:
                result = response.data[0]
                
                # Check if key is valid
                if result.get('is_valid', False):
                    logger.debug(f"Valid API key for user: {result['user_id']}")
                    
                    return AuthenticationResult(
                        auth_type="user_api_key",
                        user_id=result['user_id'],
                        api_key=api_key,
                        permissions=result.get('permissions', {})
                    )
                else:
                    logger.warning("API key is inactive or expired")
                    return None
            else:
                logger.warning("API key not found in Supabase")
                return None
                
        except Exception as e:
            logger.error(f"Error validating API key in Supabase: {str(e)}")
            return None
    
    async def create_api_key(
        self, 
        user_id: str, 
        key_name: str,
        permissions: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None
    ) -> Optional[str]:
        """
        Create a new API key for a user.
        
        Args:
            user_id: The user's UUID
            key_name: A descriptive name for the key
            permissions: Optional permissions dict
            expires_in_days: Optional expiration in days
            
        Returns:
            The raw API key if created, None on error
        """
        try:
            # Generate a secure random API key
            import secrets
            api_key = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Prepare data
            data = {
                'user_id': user_id,
                'key_hash': key_hash,
                'name': key_name,
                'permissions': permissions or {},
                'is_active': True
            }
            
            # Add expiration if specified
            if expires_in_days:
                from datetime import timedelta
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
                data['expires_at'] = expires_at.isoformat()
            
            # Insert into Supabase
            response = self.client.table('api_keys').insert(data).execute()
            
            if response.data:
                logger.info(f"Created API key '{key_name}' for user {user_id}")
                return api_key
            else:
                logger.error("Failed to create API key")
                return None
                
        except Exception as e:
            logger.error(f"Error creating API key: {str(e)}")
            return None
    
    async def list_user_api_keys(self, user_id: str) -> list:
        """
        List all API keys for a user.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            List of API key records (without the actual keys)
        """
        try:
            response = self.client.table('api_keys') \
                .select('id, name, permissions, is_active, expires_at, last_used_at, created_at') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error listing API keys: {str(e)}")
            return []
    
    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: The API key UUID
            user_id: The user's UUID (for authorization)
            
        Returns:
            True if revoked, False on error
        """
        try:
            response = self.client.table('api_keys') \
                .update({'is_active': False}) \
                .eq('id', key_id) \
                .eq('user_id', user_id) \
                .execute()
            
            if response.data:
                logger.info(f"Revoked API key {key_id}")
                return True
            else:
                logger.warning(f"Failed to revoke API key {key_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error revoking API key: {str(e)}")
            return False

# Singleton instance
_supabase_auth_client = None

def get_supabase_auth_client() -> SupabaseAuthClient:
    """Get or create the Supabase auth client singleton."""
    global _supabase_auth_client
    if _supabase_auth_client is None:
        _supabase_auth_client = SupabaseAuthClient()
    return _supabase_auth_client

# Convenience functions
async def validate_api_key_supabase(api_key: str) -> Optional[AuthenticationResult]:
    """Validate an API key using Supabase."""
    client = get_supabase_auth_client()
    return await client.validate_api_key(api_key)