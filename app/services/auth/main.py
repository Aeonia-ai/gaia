"""
Gaia Platform Auth Service

Handles all authentication operations including:
- JWT token validation and refresh
- API key validation
- User registration and login via Supabase
- Inter-service authentication coordination

This service extracts authentication functionality from the LLM Platform
while maintaining identical API behavior for client compatibility.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import shared Gaia utilities
from app.shared import (
    settings,
    configure_logging_for_service,
    log_service_startup,
    log_service_shutdown,
    log_auth_event,
    get_current_auth,
    get_api_key,
    validate_supabase_jwt,
    get_supabase_client,
    ensure_nats_connection,
    NATSSubjects,
    ServiceHealthEvent,
    database_health_check,
    supabase_health_check
)

# Configure logging for auth service
logger = configure_logging_for_service("auth")

# FastAPI application
app = FastAPI(
    title="Gaia Auth Service",
    description="Authentication service for Gaia Platform",
    version="0.2"
)

# ========================================================================================
# REQUEST/RESPONSE MODELS
# ========================================================================================

class AuthValidationRequest(BaseModel):
    """Request model for auth validation."""
    token: Optional[str] = None
    api_key: Optional[str] = None

class AuthValidationResponse(BaseModel):
    """Response model for auth validation."""
    valid: bool
    auth_type: str
    user_id: Optional[str] = None
    error: Optional[str] = None

class UserRegistrationRequest(BaseModel):
    """Request model for user registration."""
    email: str
    password: str

class UserLoginRequest(BaseModel):
    """Request model for user login.""" 
    email: str
    password: str

class TokenRefreshRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str

# ========================================================================================
# HEALTH AND STATUS ENDPOINTS
# ========================================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for auth service."""
    # Check database and Supabase connectivity
    db_health = await database_health_check()
    supabase_health = await supabase_health_check()
    
    overall_status = "healthy"
    if db_health["status"] != "healthy" or supabase_health["status"] != "healthy":
        overall_status = "unhealthy"
    
    return {
        "service": "auth",
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "database": db_health,
        "supabase": supabase_health,
        "version": "0.2"
    }

@app.get("/status", tags=["Status"])
async def service_status():
    """Detailed service status information."""
    return {
        "service": "auth",
        "version": "0.2",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "features": {
            "jwt_validation": True,
            "api_key_validation": True,
            "supabase_auth": True,
            "user_registration": True
        }
    }

# ========================================================================================
# AUTHENTICATION ENDPOINTS
# ========================================================================================

@app.post("/auth/validate", response_model=AuthValidationResponse, tags=["Authentication"])
async def validate_authentication(request: AuthValidationRequest):
    """
    Validate authentication credentials (JWT or API key).
    Used by gateway and other services for auth validation.
    """
    logger.info(f"Auth validation request: JWT={bool(request.token)}, API_Key={bool(request.api_key)}")
    
    # Try JWT validation first
    if request.token:
        try:
            from fastapi.security import HTTPAuthorizationCredentials
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=request.token
            )
            
            jwt_payload = await validate_supabase_jwt(credentials)
            user_id = jwt_payload.get('sub')
            
            log_auth_event("auth", "jwt", user_id, success=True)
            
            return AuthValidationResponse(
                valid=True,
                auth_type="jwt",
                user_id=user_id
            )
            
        except HTTPException as e:
            logger.warning(f"JWT validation failed: {e.detail}")
            log_auth_event("auth", "jwt", success=False)
    
    # Try API key validation
    if request.api_key:
        try:
            expected_key = settings.API_KEY
            if request.api_key == expected_key:
                log_auth_event("auth", "api_key", success=True)
                
                return AuthValidationResponse(
                    valid=True,
                    auth_type="api_key"
                )
            else:
                log_auth_event("auth", "api_key", success=False)
                
        except Exception as e:
            logger.error(f"API key validation error: {e}")
    
    # No valid authentication found
    return AuthValidationResponse(
        valid=False,
        auth_type="none",
        error="No valid authentication credentials provided"
    )

@app.post("/auth/register", tags=["Authentication"])
async def register_user(request: UserRegistrationRequest):
    """Register a new user via Supabase."""
    try:
        supabase = get_supabase_client()
        
        logger.info(f"User registration attempt: {request.email}")
        
        user = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })
        
        log_auth_event("auth", "registration", request.email, success=True)
        logger.info(f"User registered successfully: {request.email}")
        
        return user
        
    except Exception as e:
        log_auth_event("auth", "registration", request.email, success=False)
        logger.error(f"User registration failed for {request.email}: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )

@app.post("/auth/login", tags=["Authentication"])
async def login_user(request: UserLoginRequest):
    """Login user via Supabase."""
    try:
        supabase = get_supabase_client()
        
        logger.info(f"User login attempt: {request.email}")
        
        user = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        log_auth_event("auth", "login", request.email, success=True)
        logger.info(f"User logged in successfully: {request.email}")
        
        return user
        
    except Exception as e:
        log_auth_event("auth", "login", request.email, success=False)
        logger.error(f"User login failed for {request.email}: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Login failed: {str(e)}"
        )

@app.post("/auth/refresh", tags=["Authentication"])
async def refresh_token(request: TokenRefreshRequest):
    """Refresh JWT token via Supabase."""
    try:
        supabase = get_supabase_client()
        
        logger.info("Token refresh attempt")
        
        # Refresh the token using Supabase
        refresh_result = supabase.auth.refresh_session(request.refresh_token)
        
        log_auth_event("auth", "token_refresh", success=True)
        logger.info("Token refreshed successfully")
        
        return refresh_result
        
    except Exception as e:
        log_auth_event("auth", "token_refresh", success=False)
        logger.error(f"Token refresh failed: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token refresh failed: {str(e)}"
        )

@app.post("/auth/logout", tags=["Authentication"])
async def logout_user():
    """Logout user via Supabase."""
    try:
        supabase = get_supabase_client()
        
        logger.info("User logout attempt")
        
        # Sign out the user
        supabase.auth.sign_out()
        
        log_auth_event("auth", "logout", success=True)
        logger.info("User logged out successfully")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        log_auth_event("auth", "logout", success=False)
        logger.error(f"Logout failed: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Logout failed: {str(e)}"
        )

# ========================================================================================
# INTER-SERVICE ENDPOINTS
# ========================================================================================

@app.post("/internal/validate", tags=["Internal"])
async def internal_auth_validation(auth_data: Dict[str, Any]):
    """
    Internal endpoint for validating auth data passed between services.
    Used by other Gaia services to validate authentication.
    """
    try:
        from app.shared.security import validate_auth_for_service
        
        auth_result = await validate_auth_for_service(auth_data)
        
        return {
            "valid": True,
            "auth_type": auth_result.auth_type,
            "user_id": auth_result.user_id,
            "api_key": auth_result.api_key
        }
        
    except HTTPException as e:
        return {
            "valid": False,
            "error": e.detail
        }
    except Exception as e:
        logger.error(f"Internal auth validation error: {e}")
        return {
            "valid": False,
            "error": "Internal validation error"
        }

# ========================================================================================
# SERVICE LIFECYCLE
# ========================================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize auth service."""
    log_service_startup("auth", "1.0.0", settings.SERVICE_PORT)
    
    # Test Supabase connection
    try:
        supabase_health = await supabase_health_check()
        if supabase_health["status"] == "healthy":
            logger.lifecycle("Supabase connection verified")
        else:
            logger.warning("Supabase connection issues detected")
    except Exception as e:
        logger.error(f"Failed to verify Supabase connection: {e}")
    
    # Initialize NATS connection for service coordination
    try:
        nats_client = await ensure_nats_connection()
        logger.nats("Connected to NATS for service coordination")
        
        # Publish auth service startup event
        startup_event = ServiceHealthEvent(
            service_name="auth",
            status="starting",
            timestamp=datetime.now()
        )
        await nats_client.publish(NATSSubjects.SERVICE_HEALTH, startup_event.dict())
        
        # Publish ready event
        ready_event = ServiceHealthEvent(
            service_name="auth",
            status="healthy", 
            timestamp=datetime.now()
        )
        await nats_client.publish(NATSSubjects.SERVICE_READY, ready_event.dict())
        
        logger.lifecycle("Auth service ready and published to NATS")
        
    except Exception as e:
        logger.warning(f"NATS initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    log_service_shutdown("auth")
    
    # Publish shutdown event to NATS
    try:
        nats_client = await ensure_nats_connection()
        shutdown_event = ServiceHealthEvent(
            service_name="auth",
            status="stopping",
            timestamp=datetime.now()
        )
        await nats_client.publish(NATSSubjects.SERVICE_HEALTH, shutdown_event.dict())
        await nats_client.disconnect()
        
    except Exception as e:
        logger.warning(f"Could not publish shutdown event to NATS: {e}")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with error logging."""
    logger.error(f"Unhandled exception in auth service: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.services.auth.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )
