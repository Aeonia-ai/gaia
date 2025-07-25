#!/usr/bin/env python3
"""
Simplify gateway route management using service registry
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.service_registry import SERVICE_REGISTRY, ServiceConfig

def generate_service_urls_dict():
    """Generate the SERVICE_URLS dictionary for gateway"""
    lines = ["# Service URL configuration - auto-generated from service registry"]
    lines.append("SERVICE_URLS = {")
    
    for service_name, config in SERVICE_REGISTRY.items():
        lines.append(f'    "{service_name}": settings.{service_name.upper()}_SERVICE_URL,')
    
    lines.append("}")
    return "\n".join(lines)

def generate_generic_forwarder():
    """Generate a generic route forwarder that works for any service"""
    return '''
# Generic service forwarder - reduces boilerplate
async def forward_to_service(
    service_name: str,
    path: str,
    request: Request,
    method: str = None,
    auth_required: bool = True
) -> Dict[str, Any]:
    """Generic forwarder that handles auth and routing"""
    
    # Handle authentication if required
    auth_data = None
    if auth_required:
        auth_data = await get_current_auth_legacy(request)
    
    # Prepare request data
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    # Determine method if not specified
    if method is None:
        method = request.method
    
    # Handle body for POST/PUT requests
    body = None
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
            if auth_data:
                body["_auth"] = auth_data
        except:
            pass  # No JSON body
    
    return await forward_request_to_service(
        service_name=service_name,
        path=path,
        method=method,
        headers=headers,
        params=dict(request.query_params) if method == "GET" else None,
        json_data=body
    )

# Service-specific route generators
def create_service_routes(app: FastAPI, service_name: str, config: ServiceConfig):
    """Dynamically create routes for a service"""
    
    # Health endpoint (no auth)
    @app.get(f"/api/v1/{service_name}/health")
    async def service_health(request: Request):
        return await forward_to_service(
            service_name=service_name,
            path="/health",
            request=request,
            auth_required=False
        )
    
    # Generic catch-all for the service
    @app.api_route(f"/api/v1/{service_name}/{{path:path}}", methods=["GET", "POST", "PUT", "DELETE"])
    async def service_catchall(path: str, request: Request):
        return await forward_to_service(
            service_name=service_name,
            path=f"/{path}",
            request=request,
            auth_required=config.requires_auth
        )
'''

def generate_simplified_gateway():
    """Generate a simplified gateway setup"""
    return f'''
# Auto-configure routes from service registry
from app.shared.service_registry import SERVICE_REGISTRY

# Generate SERVICE_URLS from registry
{generate_service_urls_dict()}

{generate_generic_forwarder()}

# Auto-register all services
for service_name, config in SERVICE_REGISTRY.items():
    create_service_routes(app, service_name, config)
'''

if __name__ == "__main__":
    print("=== Simplified Gateway Configuration ===\n")
    print(generate_simplified_gateway())
    print("\n=== How to use ===")
    print("1. Add this code to gateway/main.py")
    print("2. New services are automatically routed when added to service_registry.py")
    print("3. No more manual route updates needed!")
    print("\n=== To add a new service ===")
    print("1. Run: ./scripts/create-new-service.sh <service-name>")
    print("2. Add to SERVICE_REGISTRY in app/shared/service_registry.py")
    print("3. Deploy - routes are automatic!")