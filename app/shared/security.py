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
from fastapi import HTTPException, Security, Depends, status, Request, WebSocket
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
                 api_key_id: Optional[str] = None, scopes: Optional[list] = None, email: Optional[str] = None):
        self.auth_type = auth_type  # "jwt", "api_key", or "user_api_key"
        self.user_id = user_id
        self.api_key = api_key
        self.api_key_id = api_key_id  # For user-associated API keys
        self.scopes = scopes or []
        self.email = email  # User email address for KB path mapping
        self.authenticated_at = datetime.now()
    
    def get(self, key: str, default=None):
        """Dict-like get method for backward compatibility."""
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "auth_type": self.auth_type,
            "user_id": self.user_id,
            "api_key": self.api_key,
            "api_key_id": self.api_key_id,
            "scopes": self.scopes,
            "email": self.email,
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
        cache_key = CacheManager.api_key_cache_key(key_hash)
        
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
                        scopes=cached_result.get("scopes", []),
                        email=cached_result.get("email")
                    )
            except Exception as e:
                logger.warning(f"API key cache lookup failed: {e}")
        
        # Look up the API key in the database using raw SQL for compatibility
        result = db.execute(
            text("""
                SELECT ak.id, ak.user_id, ak.permissions, ak.is_active, ak.expires_at, ak.last_used_at, u.email
                FROM api_keys ak
                JOIN users u ON ak.user_id = u.id
                WHERE ak.key_hash = :key_hash AND ak.is_active = true
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
            scopes=result.permissions or [],
            email=result.email
        )
        
        # Cache successful validation for 10 minutes
        if redis_client.is_connected():
            try:
                cache_data = {
                    "user_id": str(result.user_id),
                    "api_key_id": str(result.id),
                    "scopes": result.permissions or [],
                    "email": result.email
                }
                redis_client.set_json(cache_key, cache_data, ex=600)  # 10 minutes
                logger.debug("User API key validation cached")
            except Exception as e:
                logger.warning(f"API key cache set failed: {e}")
        
        return auth_result
        
    except Exception as e:
        logger.error(f"Error validating user API key: {str(e)}")
        return None


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
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
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

async def get_current_user_ws(websocket: WebSocket, token: str) -> dict:
    """
    Validate JWT token for WebSocket connections.

    WebSocket-specific authentication that validates JWT from query parameters.
    Returns the JWT payload if valid, closes WebSocket with error if invalid.

    Args:
        websocket: FastAPI WebSocket connection
        token: JWT token string from query params

    Returns:
        JWT payload dict containing user_id, email, etc.

    Raises:
        HTTPException: If token is invalid (also closes WebSocket)
    """
    if not token:
        logger.error("WebSocket authentication failed: no token provided")
        await websocket.close(code=1008, reason="Authentication required")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided"
        )

    # Generate cache key from token hash
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    cache_key = CacheManager.auth_cache_key(token_hash)

    # Try to get cached validation result
    if redis_client.is_connected():
        try:
            cached_payload = redis_client.get_json(cache_key)
            if cached_payload:
                logger.debug("WebSocket JWT validation cache hit")
                return cached_payload
        except Exception as e:
            logger.warning(f"WebSocket JWT cache lookup failed: {e}")

    try:
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if not jwt_secret:
            logger.error("SUPABASE_JWT_SECRET environment variable not set")
            await websocket.close(code=1011, reason="Server configuration error")
            raise ValueError("SUPABASE_JWT_SECRET environment variable not set")

        payload = jwt.decode(
            token,
            jwt_secret,
            audience="authenticated",
            algorithms=["HS256"]
        )

        # Cache successful validation for 15 minutes
        if redis_client.is_connected():
            try:
                redis_client.set_json(cache_key, payload, ex=900)  # 15 minutes
                logger.debug("WebSocket JWT validation cached")
            except Exception as e:
                logger.warning(f"WebSocket JWT cache set failed: {e}")

        return payload

    except jwt.PyJWTError as e:
        logger.error(f"WebSocket JWT validation error: {str(e)}")
        await websocket.close(code=1008, reason="Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    except Exception as e:
        logger.error(f"Unexpected error during WebSocket JWT validation: {str(e)}")
        await websocket.close(code=1011, reason="Authentication error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )

async def get_current_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme),
    api_key_header: Optional[str] = Security(api_key_header)
) -> AuthenticationResult:
    """
    Provides authentication for JWT or user-associated API keys.
    Returns AuthenticationResult object with standardized format.
    Compatible with LLM Platform behavior.
    All API keys are validated through database for consistency.
    """
    logger.debug(f"Authentication attempt. JWT: {credentials is not None}, API Key: {api_key_header is not None}")

    # Try JWT authentication first if credentials are provided
    if credentials:
        try:
            jwt_payload = await validate_supabase_jwt(credentials)
            user_id = jwt_payload.get('sub')
            email = jwt_payload.get('email')
            logger.debug(f"Authenticated via JWT: {user_id}, email: {email}")
            return AuthenticationResult(auth_type="jwt", user_id=user_id, email=email)
        except HTTPException as e:
            logger.debug(f"JWT validation failed: {e.detail}")
            # Continue to API key validation
    
    # Try user-associated API key authentication
    if api_key_header:
        try:
            # Check if we should use Supabase for API key validation
            auth_backend = os.getenv("AUTH_BACKEND", "postgres")
            
            if auth_backend == "supabase" or os.getenv("SUPABASE_AUTH_ENABLED", "false").lower() == "true":
                # Use Supabase exclusively when configured - no PostgreSQL fallback
                logger.debug("Validating API key in Supabase (exclusive mode)")
                try:
                    from app.shared.supabase_auth import validate_api_key_supabase
                    supabase_result = await validate_api_key_supabase(api_key_header)
                    
                    if supabase_result:
                        logger.debug(f"Authenticated via Supabase API key for user: {supabase_result.user_id}, email: {supabase_result.email}")
                        return supabase_result
                    else:
                        logger.warning("Invalid API Key provided - not found in Supabase")
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Could not validate credentials"
                        )
                except HTTPException:
                    raise  # Re-raise HTTP exceptions
                except Exception as e:
                    logger.error(f"Supabase auth check failed: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Authentication service error"
                    )
            else:
                # Use PostgreSQL only when Supabase is explicitly disabled
                from app.shared.database import get_database_session
                db_gen = get_database_session()
                db = next(db_gen)
                
                logger.debug("Validating API key in PostgreSQL database")
                user_api_result = await validate_user_api_key(api_key_header, db)
                
                if user_api_result:
                    logger.debug(f"Authenticated via PostgreSQL API key for user: {user_api_result.user_id}")
                    return user_api_result
                else:
                    logger.warning("Invalid API Key provided - not found in PostgreSQL")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Could not validate credentials"
                    )
        except HTTPException:
            raise  # Re-raise HTTP exceptions as-is
        except Exception as e:
            logger.error(f"Error during API Key validation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during authentication"
            )
        finally:
            if 'db' in locals() and db:
                db.close()
    
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
    Supports JWT tokens for both user authentication and service-to-service auth.
    """
    auth_type = auth_data.get("auth_type")
    
    if auth_type == "jwt":
        user_id = auth_data.get("user_id")
        email = auth_data.get("email")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid JWT authentication data"
            )
        return AuthenticationResult(auth_type="jwt", user_id=user_id, email=email)
    
    elif auth_type == "service_jwt":
        # New: Service-to-service JWT validation
        service_name = auth_data.get("service")
        if not service_name:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service JWT authentication data"
            )
        return AuthenticationResult(
            auth_type="service_jwt", 
            user_id=f"service:{service_name}",  # Use service: prefix for service accounts
            scopes=["service:all"]  # Grant full service permissions
        )
    
    elif auth_type == "user_api_key":
        user_id = auth_data.get("user_id")
        api_key = auth_data.get("api_key") or auth_data.get("key")  # Support both formats
        api_key_id = auth_data.get("api_key_id")
        email = auth_data.get("email")

        if not user_id or not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user API key authentication data"
            )
        return AuthenticationResult(
            auth_type="user_api_key",
            user_id=user_id,
            api_key=api_key,
            api_key_id=api_key_id,
            email=email
        )
    
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

# Unified authentication supporting both API keys and Supabase JWTs
async def get_current_auth_unified(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme),
    api_key_header: Optional[str] = Security(api_key_header)
) -> dict:
    """
    Unified authentication that supports both:
    1. API Keys (X-API-Key header) - for backward compatibility
    2. Supabase JWTs (Authorization: Bearer) - for web/mobile clients
    
    Returns dict format identical to LLM Platform for compatibility.
    """
    # First try Supabase JWT if Bearer token is provided
    if credentials and credentials.credentials:
        try:
            # Validate Supabase JWT
            jwt_payload = await validate_supabase_jwt(credentials)
            
            # Convert JWT payload to legacy format
            return {
                "user_id": jwt_payload.get("sub"),  # Supabase user ID
                "email": jwt_payload.get("email"),
                "auth_type": "supabase_jwt",
                "role": jwt_payload.get("role", "authenticated"),
                "metadata": jwt_payload.get("user_metadata", {})
            }
        except HTTPException as e:
            # JWT validation failed, try API key next
            logger.debug(f"JWT validation failed: {e.detail}")
            pass
    
    # Fall back to API key authentication
    if api_key_header:
        from app.shared.database import get_database_session
        db = get_database_session()
        try:
            auth_result = validate_user_api_key(api_key_header, db)
            if auth_result:
                return {
                    "user_id": auth_result.user_id,
                    "api_key": auth_result.api_key,
                    "api_key_id": auth_result.api_key_id,
                    "auth_type": "user_api_key",
                    "scopes": auth_result.scopes
                }
        finally:
            db.close()
    
    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Provide a valid JWT or API Key."
    )

# For backward compatibility with LLM Platform clients
async def get_current_auth_legacy(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme),
    api_key_header: Optional[str] = Security(api_key_header)
) -> dict:
    """
    Legacy authentication format for backward compatibility.
    Returns dict format identical to LLM Platform.
    Checks .env API key first for local development, then falls back to database validation.
    
    Note: Redis caching is handled gracefully in the underlying validation functions
    (validate_user_api_key and validate_supabase_jwt) with try/except blocks.
    """
    from app.shared.config import settings
    
    # Note: Removed hardcoded .env API key check - all API keys now validated through Supabase
    
    # Otherwise use the standard authentication flow
    # This ensures production uses database validation
    try:
        from app.shared.database import get_database_session
        
        # Get database session
        db_gen = get_database_session()
        db = next(db_gen)
        
        try:
            auth_result = await get_current_auth(request, credentials, api_key_header)
            
            if auth_result.auth_type == "jwt":
                return {"auth_type": "jwt", "user_id": auth_result.user_id, "email": auth_result.email}
            elif auth_result.auth_type == "user_api_key":
                return {
                    "auth_type": "user_api_key", 
                    "user_id": auth_result.user_id, 
                    "key": auth_result.api_key,
                    "email": auth_result.email
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unsupported auth type: {auth_result.auth_type}"
                )
        finally:
            # Clean up the database session
            if db:
                db.close()
    except Exception as e:
        # Note: Removed hardcoded .env API key fallback - Supabase should always be available
        logger.error(f"Authentication failed: {e}")
        raise

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
