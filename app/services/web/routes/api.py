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