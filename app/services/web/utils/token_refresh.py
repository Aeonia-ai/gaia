"""JWT Token Refresh Utility

This module provides automatic token refresh functionality for the web service.
It checks JWT token expiration and refreshes tokens before they expire.
"""
import jwt
import time
from typing import Optional, Dict, Any
from starlette.requests import Request
from app.shared.logging import setup_service_logger
from app.services.web.utils.gateway_client import GaiaAPIClient

logger = setup_service_logger("token_refresh")

# Refresh tokens when they have less than 5 minutes remaining
TOKEN_REFRESH_THRESHOLD = 300  # seconds


async def check_and_refresh_token(request: Request) -> bool:
    """
    Check if JWT token needs refresh and refresh it if necessary.

    Args:
        request: Starlette request object with session

    Returns:
        bool: True if token was refreshed or is still valid, False if refresh failed
    """
    jwt_token = request.session.get("jwt_token")
    refresh_token = request.session.get("refresh_token")

    # Skip dev tokens
    if jwt_token == "dev-token-12345":
        return True

    if not jwt_token:
        logger.warning("No JWT token in session")
        return False

    if not refresh_token:
        logger.warning("No refresh token in session")
        return False

    try:
        # Decode JWT without verification to check expiration
        # (verification happens at the service level)
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        exp = decoded.get("exp")

        if not exp:
            logger.warning("JWT token has no expiration")
            return True  # Let it through, service will validate

        # Calculate time until expiration
        current_time = int(time.time())
        time_until_expiry = exp - current_time

        # Calculate total token lifetime for verification
        iat = decoded.get("iat", current_time)
        token_lifetime = exp - iat

        logger.info(f"Token expires in {time_until_expiry} seconds ({time_until_expiry/3600:.1f} hours)")
        logger.info(f"Token lifetime: {token_lifetime} seconds ({token_lifetime/3600:.1f} hours)")

        # If token expires soon or has expired, refresh it
        if time_until_expiry < TOKEN_REFRESH_THRESHOLD:
            logger.info(f"Token expiring soon ({time_until_expiry}s remaining), refreshing...")

            try:
                async with GaiaAPIClient() as client:
                    result = await client.refresh_token(refresh_token)

                # Update session with new tokens
                session_data = result.get("session", {})
                user_data = result.get("user", {})

                request.session["jwt_token"] = session_data.get("access_token")
                request.session["refresh_token"] = session_data.get("refresh_token")

                # Update user data if provided
                if user_data:
                    request.session["user"] = {
                        "id": user_data.get("id"),
                        "email": user_data.get("email"),
                        "name": user_data.get("user_metadata", {}).get("name",
                                    user_data.get("email", "").split("@")[0])
                    }

                logger.info("Token refreshed successfully")
                return True

            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                # Clear session on refresh failure
                request.session.clear()
                return False
        else:
            # Token is still valid
            return True

    except jwt.DecodeError as e:
        logger.error(f"Failed to decode JWT: {e}")
        return False
    except Exception as e:
        logger.error(f"Error checking token expiration: {e}")
        return False


async def ensure_valid_token(request: Request) -> Optional[str]:
    """
    Ensure the session has a valid JWT token, refreshing if necessary.

    Args:
        request: Starlette request object with session

    Returns:
        str: Valid JWT token, or None if token is invalid/refresh failed
    """
    is_valid = await check_and_refresh_token(request)

    if not is_valid:
        return None

    return request.session.get("jwt_token")
