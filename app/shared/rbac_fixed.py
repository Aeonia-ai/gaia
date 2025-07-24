"""
Fixed Role-Based Access Control (RBAC) System for Gaia Platform

This version fixes the SQLAlchemy/asyncpg mismatch and other issues.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from uuid import UUID
import asyncio
from functools import lru_cache
from enum import Enum
import json

from .database import get_db_session
from .logging import get_logger
from .redis_client import redis_client
from .config import settings

logger = get_logger("rbac")

# ========================================================================
# ENUMS AND CONSTANTS
# ========================================================================

class ResourceType(str, Enum):
    """Resource types that can have permissions"""
    KB = "kb"
    API = "api"
    CHAT = "chat"
    ASSET = "asset"
    ADMIN = "admin"
    
class Action(str, Enum):
    """Standard actions across all resources"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    ADMIN = "admin"
    ACCESS = "access"
    CREATE = "create"

class RoleType(str, Enum):
    """Types of roles in the system"""
    SYSTEM = "system"
    CUSTOM = "custom"
    TEAM = "team"
    WORKSPACE = "workspace"

class ContextType(str, Enum):
    """Context for role assignments"""
    GLOBAL = "global"
    TEAM = "team"
    WORKSPACE = "workspace"
    RESOURCE = "resource"

class TeamRole(str, Enum):
    """Roles within a team"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

# Default system roles
DEFAULT_ROLES = {
    "super_admin": "Full system access",
    "admin": "Administrative access",
    "developer": "Developer access to APIs and services",
    "analyst": "Read access to data and analytics",
    "user": "Standard user access",
    "viewer": "Read-only access",
    "guest": "Limited guest access",
    # KB-specific roles
    "kb_admin": "Full KB management access",
    "kb_editor": "Can create and edit KB content",
    "kb_contributor": "Can contribute to assigned KB areas",
    "kb_viewer": "Read-only KB access"
}

# ========================================================================
# RBAC MANAGER
# ========================================================================

class RBACManager:
    """
    Fixed RBAC Manager using asyncpg properly.
    """
    
    def __init__(self):
        self.cache_ttl = settings.RBAC_CACHE_TTL if hasattr(settings, 'RBAC_CACHE_TTL') else 300
        self.audit_enabled = settings.RBAC_AUDIT_ENABLED if hasattr(settings, 'RBAC_AUDIT_ENABLED') else True
        
    # ====================================================================
    # PERMISSION CHECKING
    # ====================================================================
    
    async def check_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_path: str,
        action: Action,
        context: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Check if a user has permission to perform an action on a resource.
        """
        # Check cache first
        cache_key = f"rbac:perm:{user_id}:{resource_type}:{resource_path}:{action}"
        
        if redis_client.is_connected():
            try:
                cached = await redis_client.get(cache_key)
                if cached is not None:
                    return cached == "1"
            except Exception as e:
                logger.warning(f"Redis cache check failed: {e}")
        
        # Get user's permissions
        has_permission = await self._check_permission_db(
            user_id, resource_type, resource_path, action, context
        )
        
        # Cache result
        if redis_client.is_connected():
            try:
                await redis_client.setex(cache_key, self.cache_ttl, "1" if has_permission else "0")
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")
        
        return has_permission
    
    async def _check_permission_db(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_path: str,
        action: Action,
        context: Optional[Dict[str, str]] = None
    ) -> bool:
        """Check permission in database."""
        async with get_db_session() as conn:
            # First check if user has super_admin role
            super_admin_check = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = $1 AND r.name = 'super_admin'
                )
                """,
                UUID(user_id)
            )
            
            if super_admin_check:
                return True
            
            # Check role-based permissions
            role_permission = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM user_roles ur
                    JOIN role_permissions rp ON ur.role_id = rp.role_id
                    JOIN permissions p ON rp.permission_id = p.id
                    WHERE ur.user_id = $1
                      AND p.resource_type = $2
                      AND p.action = $3
                      AND (p.resource_path IS NULL OR $4 LIKE p.resource_path || '%')
                )
                """,
                UUID(user_id), resource_type, action, resource_path
            )
            
            if role_permission:
                return True
            
            # Check direct resource permissions
            resource_permission = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM resource_permissions
                    WHERE resource_type = $1
                      AND resource_id = $2
                      AND principal_type = 'user'
                      AND principal_id = $3
                      AND $4 = ANY(permissions)
                )
                """,
                resource_type, resource_path, str(user_id), action
            )
            
            return resource_permission
    
    async def check_kb_access(
        self,
        user_id: str,
        kb_path: str,
        action: Action = Action.READ
    ) -> bool:
        """
        Specialized check for KB access with path-based rules.
        """
        # User always has full access to their own namespace
        user_namespace = f"/kb/users/{user_id}/"
        if kb_path.startswith(user_namespace):
            return True
        
        # Check general KB permission
        return await self.check_permission(
            user_id=user_id,
            resource_type=ResourceType.KB,
            resource_path=kb_path,
            action=action
        )
    
    # ====================================================================
    # ROLE MANAGEMENT
    # ====================================================================
    
    async def assign_role(
        self,
        user_id: str,
        role_name: str,
        assigned_by: str,
        context_type: str = "global",
        context_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Assign a role to a user (fixed version).
        """
        async with get_db_session() as conn:
            # Get role ID
            role_result = await conn.fetchrow(
                "SELECT id FROM roles WHERE name = $1",
                role_name
            )
            
            if not role_result:
                logger.error(f"Role not found: {role_name}")
                return False
            
            role_id = role_result['id']
            
            # Use 'global' as default context_id for global roles
            if context_type == "global" and context_id is None:
                context_id = "global"
            
            # Insert user role
            try:
                await conn.execute(
                    """
                    INSERT INTO user_roles 
                    (user_id, role_id, context_type, context_id, assigned_by, expires_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id, role_id, context_type, context_id) 
                    DO UPDATE SET 
                        assigned_by = $5,
                        assigned_at = CURRENT_TIMESTAMP,
                        expires_at = $6
                    """,
                    UUID(user_id), role_id, context_type, context_id, 
                    UUID(assigned_by), expires_at
                )
                
                # Invalidate cache
                await self._invalidate_user_cache(user_id)
                
                # Audit log
                if self.audit_enabled:
                    await self._log_permission_event(
                        "role_assigned",
                        assigned_by,
                        user_id,
                        {"role": role_name, "context": context_type, "context_id": context_id}
                    )
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to assign role: {e}")
                return False
    
    async def revoke_role(
        self,
        user_id: str,
        role_name: str,
        revoked_by: str,
        context_id: Optional[str] = None
    ) -> bool:
        """Revoke a role from a user."""
        async with get_db_session() as conn:
            # Get role ID
            role_result = await conn.fetchrow(
                "SELECT id FROM roles WHERE name = $1",
                role_name
            )
            
            if not role_result:
                return False
            
            role_id = role_result['id']
            
            # Delete user role
            if context_id:
                await conn.execute(
                    """
                    DELETE FROM user_roles 
                    WHERE user_id = $1 AND role_id = $2 AND context_id = $3
                    """,
                    UUID(user_id), role_id, context_id
                )
            else:
                await conn.execute(
                    """
                    DELETE FROM user_roles 
                    WHERE user_id = $1 AND role_id = $2 AND context_id = 'global'
                    """,
                    UUID(user_id), role_id
                )
            
            # Invalidate cache
            await self._invalidate_user_cache(user_id)
            
            # Audit log
            if self.audit_enabled:
                await self._log_permission_event(
                    "role_revoked",
                    revoked_by,
                    user_id,
                    {"role": role_name, "context_id": context_id}
                )
            
            return True
    
    async def get_user_roles(
        self,
        user_id: str,
        context_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all roles assigned to a user."""
        async with get_db_session() as conn:
            if context_type:
                result = await conn.fetch(
                    """
                    SELECT r.name, r.display_name, ur.context_type, ur.context_id
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = $1 AND ur.context_type = $2
                    """,
                    UUID(user_id), context_type
                )
            else:
                result = await conn.fetch(
                    """
                    SELECT r.name, r.display_name, ur.context_type, ur.context_id
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = $1
                    """,
                    UUID(user_id)
                )
            
            return [
                {
                    "name": row['name'],
                    "display_name": row['display_name'],
                    "context_type": row['context_type'],
                    "context_id": row['context_id']
                }
                for row in result
            ]
    
    # ====================================================================
    # TEAM MANAGEMENT
    # ====================================================================
    
    async def add_team_member(
        self,
        team_id: str,
        user_id: str,
        role: str,
        added_by: str
    ) -> bool:
        """Add a user to a team."""
        async with get_db_session() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO team_members (team_id, user_id, role, joined_at, invited_by)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP, $4)
                    ON CONFLICT (team_id, user_id) DO UPDATE SET role = $3
                    """,
                    UUID(team_id), UUID(user_id), role, UUID(added_by)
                )
                
                # Assign team role
                await self.assign_role(
                    user_id=user_id,
                    role_name=f"team_{role}",
                    assigned_by=added_by,
                    context_type="team",
                    context_id=team_id
                )
                
                return True
            except Exception as e:
                logger.error(f"Failed to add team member: {e}")
                return False
    
    async def is_team_member(self, user_id: str, team_id: str) -> bool:
        """Check if user is a team member."""
        async with get_db_session() as conn:
            return await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM team_members
                    WHERE user_id = $1 AND team_id = $2
                )
                """,
                UUID(user_id), UUID(team_id)
            )
    
    # ====================================================================
    # WORKSPACE MANAGEMENT
    # ====================================================================
    
    async def add_workspace_member(
        self,
        workspace_id: str,
        user_id: str,
        added_by: str
    ) -> bool:
        """Add a user to a workspace."""
        async with get_db_session() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO workspace_members (workspace_id, user_id, invited_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (workspace_id, user_id) DO NOTHING
                    """,
                    UUID(workspace_id), UUID(user_id), UUID(added_by)
                )
                
                # Assign workspace role
                await self.assign_role(
                    user_id=user_id,
                    role_name="workspace_member",
                    assigned_by=added_by,
                    context_type="workspace",
                    context_id=workspace_id
                )
                
                return True
            except Exception as e:
                logger.error(f"Failed to add workspace member: {e}")
                return False
    
    async def is_workspace_member(self, user_id: str, workspace_id: str) -> bool:
        """Check if user is a workspace member."""
        async with get_db_session() as conn:
            return await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM workspace_members
                    WHERE user_id = $1 AND workspace_id = $2
                )
                """,
                UUID(user_id), UUID(workspace_id)
            )
    
    # ====================================================================
    # UTILITY METHODS
    # ====================================================================
    
    async def _invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user."""
        if redis_client.is_connected():
            try:
                pattern = f"rbac:*:{user_id}:*"
                # Note: This is a simplified version. In production, 
                # you'd want to track keys or use Redis SCAN
                logger.debug(f"Invalidating cache for user {user_id}")
            except Exception as e:
                logger.warning(f"Cache invalidation failed: {e}")
    
    async def _log_permission_event(
        self,
        event_type: str,
        actor_id: str,
        target_id: str,
        details: Dict[str, Any]
    ):
        """Log permission-related events."""
        if not self.audit_enabled:
            return
            
        async with get_db_session() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO permission_audit_log 
                    (event_type, actor_id, target_user_id, details, created_at)
                    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                    """,
                    event_type, UUID(actor_id), UUID(target_id), json.dumps(details)
                )
            except Exception as e:
                logger.error(f"Failed to log audit event: {e}")

# ========================================================================
# SINGLETON INSTANCE
# ========================================================================

rbac_manager = RBACManager()

# ========================================================================
# DECORATORS
# ========================================================================

def require_permission(
    resource_type: ResourceType,
    action: Action,
    resource_path_param: str = "path"
):
    """
    Decorator to require specific permissions for a route.
    Fixed to properly handle async functions.
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract user_id from auth
            auth = kwargs.get("auth", {})
            user_id = auth.get("user_id")
            
            if not user_id:
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Extract resource path
            resource_path = kwargs.get(resource_path_param, "/")
            
            # Check permission
            has_permission = await rbac_manager.check_permission(
                user_id=user_id,
                resource_type=resource_type,
                resource_path=resource_path,
                action=action
            )
            
            if not has_permission:
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail="Permission denied")
            
            # Call original function
            return await func(*args, **kwargs)
        
        # Handle both async and sync functions
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, we need to run the permission check in an event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(async_wrapper(*args, **kwargs))
                    return func(*args, **kwargs)
                finally:
                    loop.close()
            return sync_wrapper
    
    return decorator