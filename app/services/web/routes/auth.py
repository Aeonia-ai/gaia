"""Authentication routes for web service"""
from fasthtml.components import Div
from fasthtml.core import Script
from starlette.responses import RedirectResponse
from app.services.web.components.gaia_ui import gaia_success_message, gaia_error_message
from app.services.web.utils.gateway_client import gateway_client
from app.shared.logging import setup_service_logger

logger = setup_service_logger("auth_routes")


def setup_routes(app):
    """Setup authentication routes"""
    
    @app.post("/auth/login")
    async def login(request):
        """Handle login form submission"""
        form_data = await request.form()
        email = form_data.get("email")
        password = form_data.get("password")
        
        try:
            # Call gateway login endpoint
            result = await gateway_client.login(email, password)
            
            # Store JWT and user info in session
            request.session["jwt_token"] = result["access_token"]
            request.session["user"] = result["user"]
            
            # Return success with redirect
            return Div(
                gaia_success_message("Login successful! Redirecting..."),
                Script("setTimeout(() => window.location.href = '/chat', 1000)")
            )
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return gaia_error_message("Invalid email or password")
    
    @app.post("/auth/register")
    async def register(request):
        """Handle registration form submission"""
        form_data = await request.form()
        email = form_data.get("email")
        password = form_data.get("password")
        
        try:
            # Call gateway register endpoint
            result = await gateway_client.register(email, password)
            
            # Auto-login after registration
            request.session["jwt_token"] = result["access_token"]
            request.session["user"] = result["user"]
            
            # Return success with redirect
            return Div(
                gaia_success_message("Registration successful! Redirecting..."),
                Script("setTimeout(() => window.location.href = '/chat', 1000)")
            )
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            error_msg = "Registration failed. "
            if "already exists" in str(e).lower():
                error_msg += "Email already registered."
            else:
                error_msg += "Please try again."
            return gaia_error_message(error_msg)
    
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