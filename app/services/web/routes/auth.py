"""Authentication routes for web service"""
from fasthtml.components import Div, A, Script
from starlette.responses import RedirectResponse, HTMLResponse
from app.services.web.components.gaia_ui import (
    gaia_success_message, 
    gaia_error_message, 
    gaia_email_verification_notice,
    gaia_email_confirmed_success,
    gaia_email_not_verified_notice,
    gaia_info_message,
    gaia_toast_script
)
from app.services.web.utils.gateway_client import gateway_client, GaiaAPIClient
from app.services.web.config import settings
from app.shared.logging import setup_service_logger

logger = setup_service_logger("auth_routes")


def setup_routes(app):
    """Setup authentication routes"""
    
    @app.post("/auth/dev-login")
    async def dev_login(request):
        """Development login bypass for local testing"""
        if settings.debug:
            # For local development, bypass Supabase
            form_data = await request.form()
            email = form_data.get("email")
            
            if email == "dev@gaia.local":
                # Create a mock session
                request.session["jwt_token"] = "dev-token-12345"
                request.session["user"] = {
                    "id": "dev-user-id",
                    "email": "dev@gaia.local",
                    "name": "Local Development User"
                }
                
                return RedirectResponse(url="/chat", status_code=303)
            
        return gaia_error_message("Development login not available")
    
    @app.post("/auth/login")
    async def login(request):
        """Handle login form submission"""
        form_data = await request.form()
        email = form_data.get("email")
        password = form_data.get("password")
        
        # For local development only - hardcoded test account
        if settings.debug and email == "dev@gaia.local" and password == "testtest":
            # Create a mock session for testing
            request.session["jwt_token"] = "dev-token-12345"
            request.session["user"] = {
                "id": "dev-user-id",
                "email": "dev@gaia.local",
                "name": "Local Development User"
            }
            
            logger.info("Using mock dev login for dev@gaia.local")
            return RedirectResponse(url="/chat", status_code=303)
        
        try:
            # Call gateway login endpoint for all other users
            async with GaiaAPIClient() as client:
                result = await client.login(email, password)
            
            logger.info(f"Login successful for {email}")
            
            # Extract user info from Supabase response
            session_data = result.get("session", {})
            user_data = result.get("user", {})
            
            # Check if email is confirmed
            email_confirmed_at = user_data.get("email_confirmed_at")
            
            if not email_confirmed_at:
                # Email not verified - show verification notice
                logger.warning(f"Login attempt with unverified email: {email}")
                return Div(
                    gaia_email_not_verified_notice(),
                    Div(
                        "Didn't receive the email? ",
                        A(
                            "Resend verification",
                            href="#",
                            cls="text-purple-400 hover:text-purple-300 underline transition-colors",
                            hx_post="/auth/resend-verification",
                            hx_vals=f'{{"email": "{email}"}}',
                            hx_target="#auth-message",
                            hx_swap="innerHTML"
                        ),
                        cls="text-sm text-slate-400 text-center mt-4"
                    )
                )
            
            # Email is verified - proceed with login
            # Store JWT and user info in session
            request.session["jwt_token"] = session_data.get("access_token")
            request.session["refresh_token"] = session_data.get("refresh_token")
            request.session["user"] = {
                "id": user_data.get("id"),
                "email": user_data.get("email", email),
                "name": user_data.get("user_metadata", {}).get("name", email.split("@")[0])
            }
            
            # Check if this is an HTMX request
            is_htmx = request.headers.get("HX-Request") == "true"
            if is_htmx:
                # For HTMX, use HX-Redirect header
                response = HTMLResponse(content=str(gaia_success_message("Login successful! Redirecting...")))
                response.headers["HX-Redirect"] = "/chat"
                return response
            else:
                # Regular form submission - do a redirect
                return RedirectResponse(url="/chat", status_code=303)
            
        except Exception as e:
            logger.error(f"Login error for {email}: {e}")
            # Check for specific error messages
            error_msg = str(e).lower()
            if "invalid" in error_msg or "credentials" in error_msg:
                return gaia_error_message("Invalid email or password")
            elif "network" in error_msg:
                return gaia_error_message("Connection error. Please try again.")
            else:
                return gaia_error_message("Login failed. Please try again.")
    
    @app.post("/auth/register")
    async def register(request):
        """Handle registration form submission"""
        form_data = await request.form()
        email = form_data.get("email")
        password = form_data.get("password")
        
        try:
            # Call gateway register endpoint
            async with GaiaAPIClient() as client:
                result = await client.register(email, password)
            
            logger.info(f"Registration successful for {email}")
            
            # Check if user needs email verification
            user_data = result.get("user", {})
            email_confirmed_at = user_data.get("email_confirmed_at")
            
            if email_confirmed_at:
                # Email already confirmed (shouldn't happen for new registrations)
                logger.info(f"Email already confirmed for {email}")
                return gaia_success_message("Registration successful! You can now log in.")
            else:
                # Email verification required - return the verification notice directly for HTMX
                logger.info(f"Email verification required for {email}")
                # Check if this is an HTMX request
                is_htmx = request.headers.get("HX-Request") == "true"
                if is_htmx:
                    # Return the verification notice directly for HTMX to swap
                    return gaia_email_verification_notice(email)
                else:
                    # Non-HTMX request - do a full page redirect
                    return RedirectResponse(url=f"/email-verification?email={email}", status_code=303)
            
        except Exception as e:
            logger.error(f"Registration error for {email}: {e}")
            
            # Extract the actual error message from the response
            error_str = str(e)
            logger.error(f"Raw error string: {error_str}")
            
            # Try to extract the detail message from the error
            if "detail" in error_str:
                # Parse JSON error response if possible
                try:
                    import json
                    import re
                    
                    # Look for nested error in Service error format
                    service_error_match = re.search(r'Service error: ({.*})', error_str)
                    if service_error_match:
                        # Parse the nested error
                        nested_error = json.loads(service_error_match.group(1))
                        error_detail = nested_error.get("detail", "")
                        logger.info(f"Extracted nested error: {error_detail}")
                        return gaia_error_message(error_detail)
                    
                    # Otherwise try to extract JSON normally
                    json_start = error_str.find('{')
                    json_end = error_str.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        error_json = json.loads(error_str[json_start:json_end])
                        error_detail = error_json.get("detail", "")
                        
                        # Handle nested Service error
                        if error_detail.startswith("Service error:"):
                            match = re.search(r'Service error: ({.*})', error_detail)
                            if match:
                                nested = json.loads(match.group(1))
                                error_detail = nested.get("detail", error_detail)
                        
                        # Clean up the error message
                        if "Registration failed: " in error_detail:
                            error_detail = error_detail.replace("Registration failed: ", "")
                        
                        logger.info(f"Extracted error detail: {error_detail}")
                        return gaia_error_message(error_detail)
                except Exception as parse_error:
                    logger.error(f"Error parsing JSON: {parse_error}")
                    pass
            
            # Fallback to pattern matching
            error_lower = error_str.lower()
            
            if "please enter a valid email" in error_lower:
                return gaia_error_message("Please enter a valid email address.")
            elif "already registered" in error_lower:
                return gaia_error_message("This email is already registered. Please login instead.")
            elif "password must be" in error_lower:
                return gaia_error_message("Password must be at least 6 characters long.")
            elif "not allowed for this email domain" in error_lower:
                return gaia_error_message("Registration is not allowed for this email domain. Please use a different email.")
            elif "rate limit" in error_lower:
                return gaia_error_message("Too many attempts. Please try again later.")
            else:
                # Generic error
                return gaia_error_message("Registration failed. Please check your email and password.")
    
    @app.get("/auth/confirm")
    async def confirm_email(request):
        """Handle email confirmation from Supabase link"""
        # Get confirmation parameters from URL
        token = request.query_params.get("token")
        type_param = request.query_params.get("type")
        email = request.query_params.get("email")
        
        if not token or type_param != "signup":
            logger.error("Invalid confirmation link parameters")
            return gaia_error_message("Invalid confirmation link. Please try registering again.")
        
        try:
            # Confirm email via gateway
            async with GaiaAPIClient() as client:
                result = await client.confirm_email(token, email or "")
            
            logger.info(f"Email confirmation successful for {email}")
            
            # Show success message with login link
            return Div(
                gaia_email_confirmed_success(),
                id="message-area"
            )
            
        except Exception as e:
            logger.error(f"Email confirmation error: {e}")
            error_msg = str(e).lower()
            if "expired" in error_msg:
                return gaia_error_message("Confirmation link has expired. Please request a new one.")
            elif "invalid" in error_msg:
                return gaia_error_message("Invalid confirmation link. Please try registering again.")
            else:
                return gaia_error_message("Confirmation failed. Please try again or contact support.")
    
    @app.post("/auth/resend-verification")
    async def resend_verification(request):
        """Resend email verification"""
        form_data = await request.form()
        email = form_data.get("email")
        
        if not email:
            return gaia_error_message("Email address is required.")
        
        try:
            # Resend verification via gateway
            async with GaiaAPIClient() as client:
                result = await client.resend_verification(email)
            
            logger.info(f"Verification email resent to {email}")
            return gaia_info_message(f"Verification email resent to {email}. Please check your inbox.")
            
        except Exception as e:
            logger.error(f"Resend verification error for {email}: {e}")
            error_msg = str(e).lower()
            if "rate limit" in error_msg:
                return gaia_error_message("Too many requests. Please wait before requesting another verification email.")
            elif "not found" in error_msg:
                return gaia_error_message("Email address not found. Please register first.")
            else:
                return gaia_error_message("Failed to resend verification email. Please try again.")
    
    @app.get("/logout")
    async def logout(request):
        """Handle logout"""
        # Clear session
        request.session.clear()
        
        # Redirect to login
        return RedirectResponse(url="/login", status_code=303)
    
    @app.middleware("http")
    async def auth_middleware(request, call_next):
        """Check authentication for protected routes"""
        # Skip auth check for certain paths
        public_paths = ["/", "/login", "/register", "/auth/", "/static/", "/health"]
        
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # Check for JWT in session
        if not request.session.get("jwt_token"):
            return RedirectResponse(url="/login", status_code=303)
        
        return await call_next(request)
