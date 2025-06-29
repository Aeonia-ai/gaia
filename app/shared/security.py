"""
Shared security utilities for Gaia Platform services.
Maintains compatibility with LLM Platform authentication patterns.
"""
import jwt
import os
import logging
from fastapi import HTTPException, Security, Depends, status, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Union, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Security schemes
oauth2_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class AuthenticationResult:
    """Standard authentication result across all services."""
    
    def __init__(self, auth_type: str, user_id: Optional[str] = None, api_key: Optional[str] = None):
        self.auth_type = auth_type  # "jwt" or "api_key"
        self.user_id = user_id
        self.api_key = api_key
        self.authenticated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "auth_type": self.auth_type,
            "user_id": self.user_id,
            "api_key": self.api_key,
            "authenticated_at": self.authenticated_at.isoformat()
        }

def validate_api_key(api_key: Optional[str], expected_key: Optional[str]) -> bool:
    """
    Validate API key with clear, testable logic.
    Identical to LLM Platform implementation for compatibility.
    """
    if not expected_key:
        return False
    return api_key == expected_key

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
    Identical to LLM Platform implementation for compatibility.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
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
    api_key_header: Optional[str] = Security(api_key_header)
) -> AuthenticationResult:
    """
    Provides authentication for either JWT or API Key.
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
            expected_key = os.getenv('API_KEY')
            logger.debug(f"API Key validation attempt")
            
            is_valid_api_key = validate_api_key(api_key_header, expected_key)

            if is_valid_api_key:
                logger.debug("Authenticated via API Key")
                return AuthenticationResult(auth_type="api_key", api_key=api_key_header)
            else:
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
    auth_result = await get_current_auth(request, credentials, api_key_header)
    
    if auth_result.auth_type == "jwt":
        return {"auth_type": "jwt", "user_id": auth_result.user_id}
    else:
        return {"auth_type": "api_key", "key": auth_result.api_key}
