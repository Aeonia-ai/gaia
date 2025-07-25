"""
Service Registry for Gaia Platform

This module provides a centralized registry of all microservices,
their configurations, and routing patterns.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel

class ServiceConfig(BaseModel):
    """Configuration for a microservice"""
    name: str
    port: int
    description: str
    has_v1_api: bool = True
    has_v0_2_api: bool = False
    requires_auth: bool = True
    health_endpoint: str = "/health"
    # Define common endpoint patterns
    endpoints: List[str] = []

# Central service registry
SERVICE_REGISTRY: Dict[str, ServiceConfig] = {
    "auth": ServiceConfig(
        name="auth",
        port=8001,
        description="Authentication and authorization service",
        has_v1_api=True,
        has_v0_2_api=False,
        endpoints=[
            "/auth/login",
            "/auth/register", 
            "/auth/refresh",
            "/auth/logout",
            "/auth/validate",
            "/auth/confirm"
        ]
    ),
    "asset": ServiceConfig(
        name="asset",
        port=8002,
        description="Universal Asset Server",
        has_v1_api=True,
        has_v0_2_api=False,
        endpoints=[
            "/assets",
            "/assets/generate",
            "/assets/test",
            "/assets/{asset_id}"
        ]
    ),
    "chat": ServiceConfig(
        name="chat",
        port=8003,
        description="LLM chat orchestration service",
        has_v1_api=True,
        has_v0_2_api=True,
        endpoints=[
            "/chat",
            "/chat/completions",
            "/chat/status",
            "/chat/history",
            "/chat/personas",
            "/chat/mcp-agent",
            "/chat/stream"
        ]
    ),
    "kb": ServiceConfig(
        name="kb",
        port=8004,
        description="Knowledge Base service",
        has_v1_api=False,
        has_v0_2_api=True,
        endpoints=[
            "/search",
            "/read",
            "/write",
            "/delete",
            "/move",
            "/list",
            "/navigate",
            "/context",
            "/git/status",
            "/cache/stats"
        ]
    ),
}

def get_service_config(service_name: str) -> Optional[ServiceConfig]:
    """Get configuration for a specific service"""
    return SERVICE_REGISTRY.get(service_name)

def get_all_services() -> List[str]:
    """Get list of all registered services"""
    return list(SERVICE_REGISTRY.keys())

def get_service_url_env_name(service_name: str) -> str:
    """Get the environment variable name for a service URL"""
    return f"{service_name.upper()}_SERVICE_URL"

def register_service(service_config: ServiceConfig):
    """Register a new service in the registry"""
    SERVICE_REGISTRY[service_config.name] = service_config

def generate_gateway_routes(service_name: str) -> str:
    """Generate gateway route code for a service"""
    config = get_service_config(service_name)
    if not config:
        return f"# Service {service_name} not found in registry"
    
    routes = []
    
    # Generate route forwarding functions
    for endpoint in config.endpoints:
        # Parse endpoint to create function name
        endpoint_name = endpoint.replace("/", "_").replace("{", "").replace("}", "")
        if endpoint_name.startswith("_"):
            endpoint_name = endpoint_name[1:]
        
        # Determine HTTP method (simplified - you'd want more logic here)
        if any(action in endpoint for action in ["create", "generate", "login", "register"]):
            method = "POST"
        elif "delete" in endpoint:
            method = "DELETE"
        else:
            method = "GET"
        
        route_code = f'''
@app.{method.lower()}("/api/v1/{endpoint.lstrip('/')}")
async def {service_name}_{endpoint_name}(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward to {service_name} service: {endpoint}"""
    return await forward_request_to_service(
        service_name="{service_name}",
        path="{endpoint}",
        method="{method}",
        headers=dict(request.headers),
        {"json_data=await request.json()" if method == "POST" else "params=dict(request.query_params)"}
    )
'''
        routes.append(route_code)
    
    return "\n".join(routes)