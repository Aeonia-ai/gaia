"""API proxy routes for web service"""
from starlette.responses import JSONResponse
from app.services.web.utils.gateway_client import gateway_client
from app.shared.logging import setup_service_logger

logger = setup_service_logger("api_routes")


def setup_routes(app):
    """Setup API proxy routes"""
    
    @app.get("/api/models")
    async def get_models(request):
        """Get available models from gateway"""
        jwt_token = request.session.get("jwt_token")
        
        if not jwt_token:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        try:
            models = await gateway_client.get_models(jwt_token)
            return JSONResponse({"models": models})
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            return JSONResponse({"error": "Failed to get models"}, status_code=500)
    
    @app.get("/api/user")
    async def get_user(request):
        """Get current user info"""
        user = request.session.get("user")
        
        if not user:
            return JSONResponse({"error": "Not authenticated"}, status_code=401)
        
        return JSONResponse({"user": user})
    
    @app.get("/api/health")
    async def api_health(request):
        """Check API health via gateway"""
        try:
            health = await gateway_client.health_check()
            return JSONResponse(health)
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return JSONResponse(
                {"status": "unhealthy", "error": str(e)},
                status_code=503
            )
    
    @app.post("/api/v1/auth/register")
    async def api_register(request):
        """API proxy for user registration"""
        try:
            body = await request.json()
            email = body.get("email")
            password = body.get("password")
            
            if not email or not password:
                return JSONResponse(
                    {"detail": "Email and password are required"}, 
                    status_code=400
                )
            
            # Use the gateway client to register the user
            from app.services.web.utils.gateway_client import GaiaAPIClient
            async with GaiaAPIClient() as client:
                result = await client.register(email, password)
                
            return JSONResponse(result)
            
        except Exception as e:
            logger.error(f"API registration error: {e}")
            
            # Parse error message for better user feedback
            error_str = str(e)
            if "detail" in error_str:
                try:
                    import json
                    import re
                    
                    # Look for Service error format
                    service_error_match = re.search(r'Service error: ({.*})', error_str)
                    if service_error_match:
                        nested_error = json.loads(service_error_match.group(1))
                        return JSONResponse(
                            {"detail": nested_error.get("detail", "Registration failed")},
                            status_code=400
                        )
                    
                    # Otherwise try to extract JSON normally
                    json_start = error_str.find('{')
                    json_end = error_str.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        error_json = json.loads(error_str[json_start:json_end])
                        return JSONResponse(
                            {"detail": error_json.get("detail", "Registration failed")},
                            status_code=400
                        )
                except:
                    pass
            
            return JSONResponse(
                {"detail": "Registration failed. Please try again."},
                status_code=500
            )
    
    @app.post("/api/v1/auth/login")
    async def api_login(request):
        """API proxy for user login"""
        try:
            body = await request.json()
            email = body.get("email")
            password = body.get("password")
            
            if not email or not password:
                return JSONResponse(
                    {"detail": "Email and password are required"}, 
                    status_code=400
                )
            
            # Use the gateway client to login the user
            from app.services.web.utils.gateway_client import GaiaAPIClient
            async with GaiaAPIClient() as client:
                result = await client.login(email, password)
                
            return JSONResponse(result)
            
        except Exception as e:
            logger.error(f"API login error: {e}")
            return JSONResponse(
                {"detail": "Login failed. Please check your credentials."},
                status_code=400
            )