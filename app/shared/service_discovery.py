"""
Service Discovery System for Gaia Microservices

Provides automatic route discovery and registration for services.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from app.shared.logging import get_logger
from app.shared.config import settings

logger = get_logger(__name__)


class ServiceRoute(BaseModel):
    """Information about a service route"""
    path: str
    methods: List[str]
    description: Optional[str] = None
    tags: List[str] = []
    requires_auth: bool = True


class ServiceInfo(BaseModel):
    """Service registration information"""
    name: str
    version: str
    base_url: str
    health_endpoint: str = "/health"
    routes: List[ServiceRoute] = []
    last_seen: datetime = datetime.utcnow()
    healthy: bool = True


class ServiceRegistry:
    """
    Central registry for service discovery.
    Services register their routes on startup and the gateway discovers them.
    """
    
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self._health_check_interval = 30  # seconds
        self._health_check_task = None
        self._http_client = None
    
    async def start(self):
        """Start the service registry and health checks"""
        self._http_client = httpx.AsyncClient(timeout=5.0)
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Service registry started")
    
    async def stop(self):
        """Stop the service registry"""
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._http_client:
            await self._http_client.aclose()
        logger.info("Service registry stopped")
    
    def register_service(self, service_info: ServiceInfo):
        """Register a service with its available routes"""
        self.services[service_info.name] = service_info
        logger.info(f"Registered service: {service_info.name} with {len(service_info.routes)} routes")
    
    async def discover_service_routes(self, service_name: str, base_url: str) -> Optional[ServiceInfo]:
        """
        Discover routes from a service by calling its health endpoint.
        The health endpoint should return available routes.
        """
        try:
            # Try enhanced health endpoint that includes routes
            response = await self._http_client.get(f"{base_url}/health?include_routes=true")
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract routes if provided
                routes = []
                if "routes" in data:
                    for route_data in data["routes"]:
                        routes.append(ServiceRoute(**route_data))
                
                service_info = ServiceInfo(
                    name=service_name,
                    version=data.get("version", "unknown"),
                    base_url=base_url,
                    routes=routes,
                    healthy=True
                )
                
                self.register_service(service_info)
                return service_info
                
        except Exception as e:
            logger.error(f"Failed to discover routes for {service_name}: {e}")
        
        return None
    
    async def _health_check_loop(self):
        """Periodically check health of registered services"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_all_services()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _check_all_services(self):
        """Check health of all registered services"""
        for service_name, service_info in self.services.items():
            try:
                response = await self._http_client.get(
                    f"{service_info.base_url}{service_info.health_endpoint}"
                )
                
                service_info.healthy = response.status_code == 200
                service_info.last_seen = datetime.utcnow()
                
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                service_info.healthy = False
    
    def get_service_routes(self, service_name: str) -> List[ServiceRoute]:
        """Get routes for a specific service"""
        if service_name in self.services:
            return self.services[service_name].routes
        return []
    
    def get_healthy_services(self) -> Dict[str, ServiceInfo]:
        """Get all healthy services"""
        return {
            name: info 
            for name, info in self.services.items() 
            if info.healthy
        }


# Global registry instance
service_registry = ServiceRegistry()


def create_service_health_endpoint(app: FastAPI, service_name: str, version: str):
    """
    Create an enhanced health endpoint that includes route information.
    Add this to each service to enable route discovery.
    """
    
    @app.get("/health")
    async def enhanced_health_check(include_routes: bool = False):
        """Health check with optional route discovery"""
        
        health_data = {
            "service": service_name,
            "status": "healthy",
            "version": version,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if include_routes:
            # Extract routes from FastAPI app
            routes = []
            for route in app.routes:
                if hasattr(route, "methods") and hasattr(route, "path"):
                    # Skip internal routes
                    if route.path.startswith("/health") or route.path.startswith("/docs"):
                        continue
                    
                    routes.append({
                        "path": route.path,
                        "methods": list(route.methods),
                        "description": route.summary if hasattr(route, "summary") else None,
                        "tags": route.tags if hasattr(route, "tags") else [],
                        "requires_auth": True  # Default to requiring auth
                    })
            
            health_data["routes"] = routes
        
        return health_data


async def discover_services_from_config():
    """
    Discover services based on configuration.
    This runs on gateway startup to find all available services.
    """
    service_urls = {
        "chat": settings.CHAT_SERVICE_URL,
        "auth": settings.AUTH_SERVICE_URL,
        "asset": settings.ASSET_SERVICE_URL,
        "kb": settings.KB_SERVICE_URL,
    }
    
    for service_name, base_url in service_urls.items():
        if base_url:
            logger.info(f"Discovering routes for {service_name} at {base_url}")
            await service_registry.discover_service_routes(service_name, base_url)