"""
Shared security utilities for Gaia Platform services.
Maintains compatibility with LLM Platform authentication patterns.
Supports both global API keys and user-associated API keys.
Includes Redis caching for performance optimization.
"""
import jwt
import os
import logging
import hashlib
from fastapi import HTTPException, Security, Depends, status, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Union, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.shared.redis_client import redis_client, CacheManager

logger = logging.getLogger(__name__)

# Security schemes
oauth2_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class AuthenticationResult:
    """Standard authentication result across all services."""
    
    def __init__(self, auth_type: str, user_id: Optional[str] = None, api_key: Optional[str] = None, 
                 api_key_id: Optional[str] = None, scopes: Optional[list] = None):
        self.auth_type = auth_type  # "jwt", "api_key", or "user_api_key"
        self.user_id = user_id
        self.api_key = api_key
        self.api_key_id = api_key_id  # For user-associated API keys
        self.scopes = scopes or []
        self.authenticated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "auth_type": self.auth_type,
            "user_id": self.user_id,
            "api_key": self.api_key,
            "api_key_id": self.api_key_id,
            "scopes": self.scopes,
            "authenticated_at": self.authenticated_at.isoformat()
        }
    
    def has_scope(self, scope: str) -> bool:
        """Check if the authentication has a specific scope."""
        if self.auth_type == "jwt":
            return True  # JWT tokens have full access
        if not self.scopes:
            return True  # No scopes means full access (for backward compatibility)
        return scope in self.scopes

def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()

def validate_api_key(api_key: Optional[str], expected_key: Optional[str]) -> bool:
    """
    Validate API key with clear, testable logic.
    Identical to LLM Platform implementation for compatibility.
    """
    if not expected_key:
        return False
    return api_key == expected_key

async def validate_user_api_key(api_key: str, db: Session) -> Optional[AuthenticationResult]:
    """
    Validate a user-associated API key from the database.
    Includes Redis caching for performance optimization.
    Returns AuthenticationResult if valid, None if invalid.
    """
    from sqlalchemy import text
    
    try:
        # Hash the provided API key
        key_hash = hash_api_key(api_key)
        cache_key = CacheManager.api_key_cache_key(key_hash[:16])
        
        # Try to get cached validation result
        if redis_client.is_connected():
            try:
                cached_result = redis_client.get_json(cache_key)
                if cached_result:
                    logger.debug("User API key validation cache hit")
                    return AuthenticationResult(
                        auth_type="user_api_key",
                        user_id=cached_result["user_id"],
                        api_key=api_key,
                        api_key_id=cached_result["api_key_id"],
                        scopes=cached_result.get("scopes", [])
                    )
            except Exception as e:
                logger.warning(f"API key cache lookup failed: {e}")
        
        # Look up the API key in the database using raw SQL for compatibility
        result = db.execute(
            text("""
                SELECT id, user_id, permissions, is_active, expires_at, last_used_at
                FROM api_keys
                WHERE key_hash = :key_hash AND is_active = true
            """),
            {"key_hash": key_hash}
        ).fetchone()
        
        if not result:
            return None
            
        # Check if the key is expired
        if result.expires_at and result.expires_at < datetime.utcnow():
            return None
            
        # Update last used timestamp
        db.execute(
            text("UPDATE api_keys SET last_used_at = NOW() WHERE id = :id"),
            {"id": result.id}
        )
        db.commit()
        
        # Create authentication result
        auth_result = AuthenticationResult(
            auth_type="user_api_key",
            user_id=str(result.user_id),
            api_key=api_key,
            api_key_id=str(result.id),
            scopes=result.permissions or []
        )
        
        # Cache successful validation for 10 minutes
        if redis_client.is_connected():
            try:
                cache_data = {
                    "user_id": str(result.user_id),
                    "api_key_id": str(result.id),
                    "scopes": result.permissions or []
                }
                redis_client.set_json(cache_key, cache_data, ex=600)  # 10 minutes
                logger.debug("User API key validation cached")
            except Exception as e:
                logger.warning(f"API key cache set failed: {e}")
        
        return auth_result
        
    except Exception as e:
        logger.error(f"Error validating user API key: {str(e)}")
        return None

def get_api_key(
    api_key_header: Optional[str] = Security(APIKeyHeader(name="X-API-Key", auto_error=False))
) -> str:
    """
    Validate API key for endpoint access.
    Compatible with LLM Platform implementation.
    """
    try:
        expected_key = os.getenv('API_KEY')
        
        if validate_api_key(api_key_header, expected_key):
            return api_key_header
        
        raise HTTPException(
            status_code=403, 
            detail="Could not validate credentials"
        )
        
    except HTTPException as e:
        if e.status_code == 500:
            raise HTTPException(
                status_code=500,
                detail="API Key not configured in environment"
            )
        raise e

async def validate_supabase_jwt(
    credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme)
) -> dict:
    """
    Validates a Supabase JWT token and returns its payload.
    Includes Redis caching for performance optimization.
    Identical to LLM Platform implementation for compatibility.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate cache key from token hash
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()[:16]
    cache_key = CacheManager.auth_cache_key(token_hash)
    
    # Try to get cached validation result
    if redis_client.is_connected():
        try:
            cached_payload = redis_client.get_json(cache_key)
            if cached_payload:
                logger.debug("JWT validation cache hit")
                return cached_payload
        except Exception as e:
            logger.warning(f"JWT cache lookup failed: {e}")
    
    try:
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if not jwt_secret:
            logger.error("SUPABASE_JWT_SECRET environment variable not set.")
            raise ValueError("SUPABASE_JWT_SECRET environment variable not set.")

        payload = jwt.decode(
            credentials.credentials,
            jwt_secret,
            audience="authenticated",
            algorithms=["HS256"]
        )
        
        # Cache successful validation for 15 minutes
        if redis_client.is_connected():
            try:
                redis_client.set_json(cache_key, payload, ex=900)  # 15 minutes
                logger.debug("JWT validation cached")
            except Exception as e:
                logger.warning(f"JWT cache set failed: {e}")
        
        return payload
    except jwt.PyJWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during JWT validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication",
        )

async def get_current_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme),
    api_key_header: Optional[str] = Security(api_key_header),
    db: Session = None
) -> AuthenticationResult:
    """
    Provides authentication for JWT, global API keys, or user-associated API keys.
    Returns AuthenticationResult object with standardized format.
    Compatible with LLM Platform behavior.
    """
    logger.debug(f"Authentication attempt. JWT: {credentials is not None}, API Key: {api_key_header is not None}")

    # Try JWT authentication first if credentials are provided
    if credentials:
        try:
            jwt_payload = await validate_supabase_jwt(credentials)
            user_id = jwt_payload.get('sub')
            logger.debug(f"Authenticated via JWT: {user_id}")
            return AuthenticationResult(auth_type="jwt", user_id=user_id)
        except HTTPException as e:
            logger.debug(f"JWT validation failed: {e.detail}")
            # Continue to API key validation
    
    # Try API key authentication
    if api_key_header:
        try:
            # First try global API key (backward compatibility)
            expected_key = os.getenv('API_KEY')
            logger.debug(f"API Key validation attempt")
            
            is_valid_global_api_key = validate_api_key(api_key_header, expected_key)

            if is_valid_global_api_key:
                logger.debug("Authenticated via global API Key")
                return AuthenticationResult(auth_type="api_key", api_key=api_key_header)
            
            # If global API key failed, try user-associated API key
            if db is not None:
                logger.debug("Trying user-associated API key validation")
                user_api_result = await validate_user_api_key(api_key_header, db)
                
                if user_api_result:
                    logger.debug(f"Authenticated via user API key: {user_api_result.user_id}")
                    return user_api_result
            
            # If both failed, raise error
            logger.warning("Invalid API Key provided.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials"
            )
            
        except HTTPException as e:
            if e.status_code == 500:
                logger.error("API Key not configured.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="API Key not configured in environment"
                )
            raise e
        except Exception as e:
            logger.error(f"Unexpected error during API Key validation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during API Key authentication"
            )
    
    logger.warning("No authentication credentials provided.")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Provide a valid JWT or API Key."
    )

# Authentication validation for inter-service communication
async def validate_auth_for_service(auth_data: Dict[str, Any]) -> AuthenticationResult:
    """
    Validate authentication data passed between services.
    Used for service-to-service authentication validation.
    """
    auth_type = auth_data.get("auth_type")
    
    if auth_type == "jwt":
        user_id = auth_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid JWT authentication data"
            )
        return AuthenticationResult(auth_type="jwt", user_id=user_id)
    
    elif auth_type == "api_key":
        api_key = auth_data.get("api_key")
        expected_key = os.getenv('API_KEY')
        
        if not validate_api_key(api_key, expected_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key in service authentication"
            )
        return AuthenticationResult(auth_type="api_key", api_key=api_key)
    
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown authentication type"
        )

# Utility function for services to check authentication
def require_authentication(auth_result: AuthenticationResult) -> AuthenticationResult:
    """
    Ensure authentication is valid.
    Can be used as a dependency in service endpoints.
    """
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return auth_result

# For backward compatibility with LLM Platform clients
async def get_current_auth_legacy(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme),
    api_key_header: Optional[str] = Security(api_key_header)
) -> dict:
    """
    Legacy authentication format for backward compatibility.
    Returns dict format identical to LLM Platform.
    """
    # Get database session using proper dependency injection
    from app.shared.database import get_db
    
    # Get database session generator and use it
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        auth_result = await get_current_auth(request, credentials, api_key_header, db)
        
        if auth_result.auth_type == "jwt":
            return {"auth_type": "jwt", "user_id": auth_result.user_id}
        elif auth_result.auth_type == "user_api_key":
            return {"auth_type": "user_api_key", "user_id": auth_result.user_id, "key": auth_result.api_key}
        else:
            return {"auth_type": "api_key", "key": auth_result.api_key}
    finally:
        # Clean up the database session
        try:
            next(db_gen)
        except StopIteration:
            pass

# API Key management functions
def generate_api_key(prefix: str = "gaia") -> str:
    """
    Generate a new API key with the specified prefix.
    Format: prefix_environment_random_string
    """
    import secrets
    import string
    
    environment = os.getenv("ENVIRONMENT", "dev")
    random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    return f"{prefix}_{environment}_{random_part}"

async def create_user_api_key(user_id: str, name: str, db: Session, 
                            scopes: Optional[list] = None, 
                            expires_at: Optional[datetime] = None) -> tuple[str, str]:
    """
    Create a new API key for a user.
    Returns (api_key, api_key_id) tuple.
    """
    from app.shared.models.api_keys import APIKey
    
    # Generate new API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    # Create database record
    api_key_record = APIKey(
        user_id=user_id,
        key_hash=key_hash,
        name=name,
        scopes=scopes or [],
        expires_at=expires_at
    )
    
    db.add(api_key_record)
    db.commit()
    db.refresh(api_key_record)
    
    return api_key, str(api_key_record.id)

async def revoke_user_api_key(user_id: str, api_key_id: str, db: Session) -> bool:
    """
    Revoke (delete) a user's API key.
    Returns True if successful, False if not found.
    """
    from app.shared.models.api_keys import APIKey
    
    api_key_record = db.query(APIKey).filter(
        APIKey.id == api_key_id,
        APIKey.user_id == user_id
    ).first()
    
    if not api_key_record:
        return False
    
    db.delete(api_key_record)
    db.commit()
    return True

async def get_user_api_keys(user_id: str, db: Session) -> list:
    """
    Get all API keys for a user.
    Returns list of APIKeyResponse objects.
    """
    from app.shared.models.api_keys import APIKey, APIKeyResponse
    
    api_keys = db.query(APIKey).filter(APIKey.user_id == user_id).all()
    return [APIKeyResponse(api_key) for api_key in api_keys]
