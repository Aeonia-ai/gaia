"""
JWT Service for Service-to-Service Authentication

This module provides JWT token generation and validation for inter-service
communication in the Gaia platform. Part of the migration from API_KEY
to mTLS + JWT authentication.
"""
import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from pathlib import Path

from app.shared.logging import configure_logging_for_service
from app.shared.config import settings

# Configure logging
logger = configure_logging_for_service("jwt_service")

# JWT Configuration
JWT_ALGORITHM = "RS256"
JWT_ISSUER = "gaia-auth-service"
JWT_AUDIENCE = "gaia-services"
JWT_EXPIRY_HOURS = 1

# Key paths
JWT_PRIVATE_KEY_PATH = os.getenv("JWT_PRIVATE_KEY_PATH", "/app/certs/jwt-signing.key")
JWT_PUBLIC_KEY_PATH = os.getenv("JWT_PUBLIC_KEY_PATH", "/app/certs/jwt-signing.pub")

# Cache for keys
_private_key_cache: Optional[str] = None
_public_key_cache: Optional[str] = None


def generate_dev_keys_if_missing():
    """Generate development JWT keys if they don't exist (for local development)."""
    private_key_path = Path(JWT_PRIVATE_KEY_PATH)
    public_key_path = Path(JWT_PUBLIC_KEY_PATH)
    
    # Only generate in local development
    if settings.ENVIRONMENT not in ["local", "development"] or private_key_path.exists():
        return
    
    logger.info("Generating development JWT keys...")
    
    # Create directory if it doesn't exist
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate RSA key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Write private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    private_key_path.write_bytes(private_pem)
    logger.info(f"Generated private key: {private_key_path}")
    
    # Write public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    public_key_path.write_bytes(public_pem)
    logger.info(f"Generated public key: {public_key_path}")


def get_private_key() -> str:
    """Get JWT signing private key."""
    global _private_key_cache
    
    if _private_key_cache is None:
        # Don't try to generate keys in containers - they should be mounted
        # generate_dev_keys_if_missing()
        
        try:
            with open(JWT_PRIVATE_KEY_PATH, 'r') as f:
                _private_key_cache = f.read()
        except FileNotFoundError:
            logger.error(f"JWT private key not found at {JWT_PRIVATE_KEY_PATH}")
            raise
    
    return _private_key_cache


def get_public_key() -> str:
    """Get JWT verification public key."""
    global _public_key_cache
    
    if _public_key_cache is None:
        # Don't try to generate keys in containers - they should be mounted
        # generate_dev_keys_if_missing()
        
        try:
            with open(JWT_PUBLIC_KEY_PATH, 'r') as f:
                _public_key_cache = f.read()
        except FileNotFoundError:
            logger.error(f"JWT public key not found at {JWT_PUBLIC_KEY_PATH}")
            raise
    
    return _public_key_cache


async def generate_service_jwt(
    service_name: str, 
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a JWT token for service-to-service communication.
    
    Args:
        service_name: Name of the service requesting the token
        additional_claims: Optional additional claims to include
        
    Returns:
        JWT token string
    """
    now = datetime.utcnow()
    
    # Base payload
    payload = {
        'iss': JWT_ISSUER,
        'sub': service_name,
        'aud': JWT_AUDIENCE,
        'iat': now,
        'exp': now + timedelta(hours=JWT_EXPIRY_HOURS),
        'service': service_name,
        'service_type': 'microservice',
        'environment': settings.ENVIRONMENT
    }
    
    # Add any additional claims
    if additional_claims:
        payload.update(additional_claims)
    
    # Sign with private key
    try:
        private_key = get_private_key()
        token = jwt.encode(payload, private_key, algorithm=JWT_ALGORITHM)
        
        logger.info(f"Generated JWT for service: {service_name}")
        return token
        
    except Exception as e:
        logger.error(f"Failed to generate JWT for {service_name}: {e}")
        raise


async def validate_service_jwt(token: str) -> Dict[str, Any]:
    """
    Validate a service JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded JWT payload
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        public_key = get_public_key()
        
        # Decode and verify
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER
        )
        
        # Validate service claim
        if 'service' not in payload:
            raise jwt.InvalidTokenError("Missing service claim")
            
        logger.info(f"Validated JWT for service: {payload['service']}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise
    except Exception as e:
        logger.error(f"JWT validation error: {e}")
        raise jwt.InvalidTokenError(f"Validation failed: {e}")


async def generate_service_auth_header(service_name: str) -> Dict[str, str]:
    """
    Generate authorization header with service JWT.
    
    Args:
        service_name: Name of the requesting service
        
    Returns:
        Dictionary with Authorization header
    """
    token = await generate_service_jwt(service_name)
    return {"Authorization": f"Bearer {token}"}


# Development helpers
if __name__ == "__main__":
    import asyncio
    
    async def test_jwt_flow():
        """Test JWT generation and validation."""
        # Generate token
        service_name = "test-service"
        token = await generate_service_jwt(service_name, {"custom": "claim"})
        print(f"Generated token for {service_name}")
        print(f"Token: {token[:50]}...")
        
        # Validate token
        payload = await validate_service_jwt(token)
        print(f"Validated token. Payload: {payload}")
        
        # Test auth header
        headers = await generate_service_auth_header(service_name)
        print(f"Auth headers: {headers}")
    
    asyncio.run(test_jwt_flow())