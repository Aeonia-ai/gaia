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
import os
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
    validate_supabase_jwt,
    get_supabase_client,
    ensure_nats_connection,
    NATSSubjects,
    ServiceHealthEvent,
    database_health_check,
    supabase_health_check
)
from app.shared.service_discovery import create_service_health_endpoint

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

class EmailConfirmationRequest(BaseModel):
    """Request model for email confirmation."""
    token: str
    email: str

class ResendVerificationRequest(BaseModel):
    """Request model for resending email verification."""
    email: str

# ========================================================================================
# HEALTH AND STATUS ENDPOINTS
# ========================================================================================

async def check_secrets_health():
    """Check if secrets are properly configured and up to date."""
    import os
    try:
        # Check required Supabase secrets
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        missing_secrets = []
        if not supabase_url:
            missing_secrets.append("SUPABASE_URL")
        if not supabase_anon_key:
            missing_secrets.append("SUPABASE_ANON_KEY")
        if not supabase_jwt_secret:
            missing_secrets.append("SUPABASE_JWT_SECRET")
        
        if missing_secrets:
            return {
                "status": "unhealthy",
                "error": f"Missing secrets: {', '.join(missing_secrets)}",
                "missing_count": len(missing_secrets)
            }
        
        # Basic validation of secret format
        warnings = []
        if supabase_url and not supabase_url.startswith("https://"):
            warnings.append("SUPABASE_URL should start with https://")
        
        if supabase_anon_key and not supabase_anon_key.startswith("eyJ"):
            warnings.append("SUPABASE_ANON_KEY appears to have invalid JWT format")
        
        # Check if we can create a Supabase client (validates JWT secret)
        try:
            supabase = get_supabase_client()
            # Simple test to validate JWT secret works
            test_health = await supabase_health_check()
            if test_health["status"] != "healthy":
                warnings.append("Supabase credentials may be outdated or invalid")
        except Exception as e:
            warnings.append(f"Supabase client creation failed: {str(e)[:100]}")
        
        status = "healthy" if not warnings else "warning"
        result = {
            "status": status,
            "secrets_configured": 3,
            "last_checked": datetime.now().isoformat()
        }
        
        if warnings:
            result["warnings"] = warnings
            
        return result
        
    except Exception as e:
        logger.error(f"Secrets health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": f"Health check failed: {str(e)}",
            "last_checked": datetime.now().isoformat()
        }

# Create enhanced health endpoint with route discovery
create_service_health_endpoint(app, "auth", "0.2")

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

@app.get("/auth/health", tags=["Authentication", "Status"])
async def authentication_health():
    """
    Comprehensive authentication system health check.
    Validates all authentication components and dependencies.
    """
    health_result = {
        "service": "auth",
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "checks": {}
    }
    
    # Check secrets configuration
    secrets_health = await check_secrets_health()
    health_result["checks"]["secrets"] = secrets_health
    
    # Check authentication backends
    auth_backend = os.getenv("AUTH_BACKEND", "postgresql")
    health_result["checks"]["auth_backend"] = {
        "configured": auth_backend,
        "status": "healthy"
    }
    
    # Test Supabase connectivity if configured
    if auth_backend == "supabase" or os.getenv("SUPABASE_AUTH_ENABLED", "false").lower() == "true":
        try:
            supabase_health = await supabase_health_check()
            health_result["checks"]["supabase"] = supabase_health
            
            # Test API key validation capability
            try:
                from app.shared.supabase_auth import validate_api_key_supabase
                # Test with a known invalid key to verify the function works
                test_result = await validate_api_key_supabase("invalid_test_key")
                health_result["checks"]["api_key_validation"] = {
                    "status": "healthy",
                    "backend": "supabase",
                    "test_performed": True
                }
            except Exception as e:
                health_result["checks"]["api_key_validation"] = {
                    "status": "error",
                    "backend": "supabase", 
                    "error": f"API key validation test failed: {str(e)[:100]}"
                }
        except Exception as e:
            health_result["checks"]["supabase"] = {
                "status": "error",
                "error": f"Supabase connection failed: {str(e)[:100]}"
            }
    
    # Test PostgreSQL connectivity if configured
    if auth_backend == "postgresql":
        try:
            db_health = await database_health_check()
            health_result["checks"]["database"] = db_health
            
            # Test API key validation capability
            try:
                from app.shared.database import get_database_session
                from app.shared.security import validate_user_api_key
                
                db_gen = get_database_session()
                db = next(db_gen)
                
                # Test with invalid key to verify function works
                test_result = await validate_user_api_key("invalid_test_key", db)
                health_result["checks"]["api_key_validation"] = {
                    "status": "healthy",
                    "backend": "postgresql",
                    "test_performed": True
                }
            except Exception as e:
                health_result["checks"]["api_key_validation"] = {
                    "status": "error", 
                    "backend": "postgresql",
                    "error": f"API key validation test failed: {str(e)[:100]}"
                }
        except Exception as e:
            health_result["checks"]["database"] = {
                "status": "error",
                "error": f"Database connection failed: {str(e)[:100]}"
            }
    
    # Check AI provider connectivity (for potential service JWT validation)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        health_result["checks"]["ai_provider"] = {
            "status": "configured",
            "provider": "anthropic",
            "key_format": "valid" if anthropic_key.startswith("sk-ant-") else "invalid"
        }
    else:
        health_result["checks"]["ai_provider"] = {
            "status": "not_configured",
            "provider": "none"
        }
    
    # Determine overall status
    error_checks = [check for check in health_result["checks"].values() 
                   if isinstance(check, dict) and check.get("status") == "error"]
    warning_checks = [check for check in health_result["checks"].values() 
                     if isinstance(check, dict) and check.get("status") in ["warning", "unhealthy"]]
    
    if error_checks:
        health_result["overall_status"] = "error"
        health_result["error_count"] = len(error_checks)
    elif warning_checks:
        health_result["overall_status"] = "warning"
        health_result["warning_count"] = len(warning_checks)
    
    return health_result

# ========================================================================================
# AUTHENTICATION ENDPOINTS
# ========================================================================================

@app.post("/auth/validate", response_model=AuthValidationResponse, tags=["Authentication"])
async def validate_authentication(request: AuthValidationRequest):
    """
    Validate authentication credentials (JWT or API key).
    Used by gateway and other services for auth validation.
    Supports user JWTs, service JWTs, and API keys.
    """
    logger.info(f"Auth validation request: JWT={bool(request.token)}, API_Key={bool(request.api_key)}")
    
    # Try JWT validation first
    if request.token:
        try:
            # First try as Supabase user JWT
            from fastapi.security import HTTPAuthorizationCredentials
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=request.token
            )
            
            try:
                jwt_payload = await validate_supabase_jwt(credentials)
                user_id = jwt_payload.get('sub')
                
                log_auth_event("auth", "jwt", user_id, success=True)
                
                return AuthValidationResponse(
                    valid=True,
                    auth_type="jwt",
                    user_id=user_id
                )
            except:
                # Try as service JWT
                from app.shared.jwt_service import validate_service_jwt
                
                try:
                    service_payload = await validate_service_jwt(request.token)
                    service_name = service_payload.get('service')
                    
                    log_auth_event("auth", "service_jwt", f"service:{service_name}", success=True)
                    
                    return AuthValidationResponse(
                        valid=True,
                        auth_type="service_jwt",
                        user_id=f"service:{service_name}"
                    )
                except Exception as service_e:
                    logger.warning(f"Service JWT validation failed: {service_e}")
                    log_auth_event("auth", "jwt", success=False)
                    
        except HTTPException as e:
            logger.warning(f"JWT validation failed: {e.detail}")
            log_auth_event("auth", "jwt", success=False)
    
    # Try API key validation - check AUTH_BACKEND to determine method
    if request.api_key:
        try:
            auth_backend = os.getenv("AUTH_BACKEND", "postgresql")
            
            if auth_backend == "supabase" or os.getenv("SUPABASE_AUTH_ENABLED", "false").lower() == "true":
                # Use Supabase exclusively when configured
                logger.debug("Validating API key in Supabase (exclusive mode)")
                try:
                    from app.shared.supabase_auth import validate_api_key_supabase
                    supabase_result = await validate_api_key_supabase(request.api_key)
                    
                    if supabase_result:
                        log_auth_event("auth", "api_key", supabase_result.user_id, success=True)
                        logger.debug(f"Authenticated via Supabase API key for user: {supabase_result.user_id}, email: {supabase_result.email}")
                        
                        return AuthValidationResponse(
                            valid=True,
                            auth_type="api_key",
                            user_id=supabase_result.user_id
                        )
                    else:
                        logger.warning("Invalid API Key provided - not found in Supabase")
                        log_auth_event("auth", "api_key", success=False)
                        
                except Exception as e:
                    logger.error(f"Supabase API key validation error: {e}")
                    log_auth_event("auth", "api_key", success=False)
            else:
                # Use PostgreSQL database validation
                logger.debug("Validating API key in PostgreSQL database")
                from app.shared.database import get_database_session
                from app.shared.security import validate_user_api_key
                
                # Get database session
                db_gen = get_database_session()
                db = next(db_gen)
                
                # Validate user-associated API key
                user_api_result = await validate_user_api_key(request.api_key, db)
                
                if user_api_result:
                    log_auth_event("auth", "api_key", user_api_result.user_id, success=True)
                    
                    return AuthValidationResponse(
                        valid=True,
                        auth_type="api_key",
                        user_id=user_api_result.user_id
                    )
                else:
                    logger.warning("Invalid API Key provided - not found in PostgreSQL")
                    log_auth_event("auth", "api_key", success=False)
                
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            log_auth_event("auth", "api_key", success=False)
    
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
        
        # Parse Supabase error messages for better user feedback
        error_msg = str(e).lower()
        
        if "email" in error_msg and ("invalid" in error_msg or "valid" in error_msg):
            detail = "Please enter a valid email address"
        elif "password" in error_msg and ("weak" in error_msg or "short" in error_msg):
            detail = "Password must be at least 6 characters long"
        elif "already registered" in error_msg or "already exists" in error_msg:
            detail = "This email is already registered"
        elif "not authorized" in error_msg or "not allowed" in error_msg:
            detail = "Registration is not allowed for this email domain"
        elif "rate limit" in error_msg:
            detail = "Too many registration attempts. Please try again later"
        else:
            # Include original error for debugging but make it user-friendly
            detail = f"Registration failed: {str(e)}"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
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

@app.post("/auth/confirm", tags=["Authentication"])
async def confirm_email(request: EmailConfirmationRequest):
    """Confirm user email with verification token."""
    try:
        supabase = get_supabase_client()
        
        logger.info(f"Email confirmation attempt for: {request.email}")
        
        # Verify the email using the confirmation token
        # Note: This depends on how your Supabase is configured
        # For now, we'll use the verify_otp method with token_type="signup"
        verification_result = supabase.auth.verify_otp({
            "email": request.email,
            "token": request.token,
            "type": "signup"
        })
        
        log_auth_event("auth", "email_confirmation", request.email, success=True)
        logger.info(f"Email confirmed successfully: {request.email}")
        
        return {
            "message": "Email confirmed successfully",
            "user": verification_result.user
        }
        
    except Exception as e:
        log_auth_event("auth", "email_confirmation", request.email, success=False)
        logger.error(f"Email confirmation failed for {request.email}: {e}")
        
        # Parse Supabase error messages
        error_msg = str(e).lower()
        
        if "expired" in error_msg or "invalid" in error_msg:
            detail = "Confirmation link is expired or invalid"
        elif "already confirmed" in error_msg:
            detail = "Email is already confirmed"
        else:
            detail = f"Email confirmation failed: {str(e)}"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

@app.post("/auth/resend-verification", tags=["Authentication"])
async def resend_verification(request: ResendVerificationRequest):
    """Resend email verification."""
    try:
        supabase = get_supabase_client()
        
        logger.info(f"Resend verification attempt for: {request.email}")
        
        # Resend confirmation email
        resend_result = supabase.auth.resend({
            "type": "signup",
            "email": request.email
        })
        
        log_auth_event("auth", "resend_verification", request.email, success=True)
        logger.info(f"Verification email resent successfully: {request.email}")
        
        return {
            "message": f"Verification email sent to {request.email}",
            "result": resend_result
        }
        
    except Exception as e:
        log_auth_event("auth", "resend_verification", request.email, success=False)
        logger.error(f"Resend verification failed for {request.email}: {e}")
        
        # Parse Supabase error messages
        error_msg = str(e).lower()
        
        if "rate limit" in error_msg:
            detail = "Too many requests. Please wait before requesting another email"
        elif "not found" in error_msg:
            detail = "Email address not found"
        else:
            detail = f"Failed to resend verification email: {str(e)}"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
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

@app.post("/internal/service-token", tags=["Internal"])
async def generate_service_token(request: Dict[str, Any]):
    """
    Generate a JWT token for service-to-service communication.
    This endpoint should only be accessible internally.
    """
    try:
        from app.shared.jwt_service import generate_service_jwt
        
        service_name = request.get("service_name")
        if not service_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service name is required"
            )
        
        # Optional: Validate that the service is allowed to request tokens
        allowed_services = ["gateway", "auth-service", "asset-service", "chat-service", "web-service"]
        if service_name not in allowed_services:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Service '{service_name}' is not authorized"
            )
        
        # Generate service JWT
        token = await generate_service_jwt(
            service_name=service_name,
            additional_claims=request.get("claims", {})
        )
        
        log_auth_event("auth", "service_token_issued", f"service:{service_name}", success=True)
        logger.info(f"Issued service token for: {service_name}")
        
        return {
            "token": token,
            "expires_in": 3600,  # 1 hour
            "token_type": "Bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Service token generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate service token"
        )

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
