"""
Role-Based Access Control (RBAC) System for Gaia Platform

This module provides a unified RBAC implementation that:
1. Starts with KB permissions but scales platform-wide
2. Supports teams and workspaces
3. Provides efficient permission checking with caching
4. Integrates with existing auth infrastructure
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from uuid import UUID
import asyncio
from functools import lru_cache
from enum import Enum

from sqlalchemy import select, and_, or_, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from pydantic import BaseModel

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
# MODELS
# ========================================================================

class Permission(BaseModel):
    """Permission model"""
    id: Optional[UUID] = None
    resource_type: ResourceType
    resource_path: str
    action: Action
    description: Optional[str] = None

class Role(BaseModel):
    """Role model"""
    id: Optional[UUID] = None
    name: str
    display_name: str
    description: Optional[str] = None
    role_type: RoleType
    is_active: bool = True
    permissions: List[Permission] = []

class UserRole(BaseModel):
    """User-Role assignment"""
    user_id: UUID
    role_id: UUID
    context_type: Optional[ContextType] = ContextType.GLOBAL
    context_id: Optional[str] = None
    expires_at: Optional[datetime] = None

class Team(BaseModel):
    """Team model"""
    id: Optional[UUID] = None
    name: str
    display_name: str
    description: Optional[str] = None
    parent_team_id: Optional[UUID] = None
    is_active: bool = True

class Workspace(BaseModel):
    """Workspace model"""
    id: Optional[UUID] = None
    name: str
    display_name: str
    description: Optional[str] = None
    workspace_type: str = "project"
    status: str = "active"
    expires_at: Optional[datetime] = None

# ========================================================================
# RBAC MANAGER
# ========================================================================

class RBACManager:
    """
    Central RBAC management class that handles all permission checking
    and role management across the platform.
    """
    
    def __init__(self):
        self.cache_ttl = getattr(settings, 'RBAC_CACHE_TTL', 300)  # 5 minutes
        
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
        Check if a user has a specific permission.
        
        Args:
            user_id: User ID to check
            resource_type: Type of resource (kb, api, etc.)
            resource_path: Path to resource (e.g., /kb/users/123/*)
            action: Action to perform (read, write, etc.)
            context: Optional context (team_id, workspace_id, etc.)
            
        Returns:
            bool: True if user has permission
        """
        # Check cache first
        cache_key = f"rbac:perm:{user_id}:{resource_type}:{resource_path}:{action}"
        if context:
            cache_key += f":{context}"
        
        cached = await redis_client.get(cache_key)
        if cached is not None:
            return cached == "1"
        
        # Check database
        has_permission = await self._check_permission_db(
            user_id, resource_type, resource_path, action, context
        )
        
        # Cache result
        await redis_client.setex(cache_key, self.cache_ttl, "1" if has_permission else "0")
        
        return has_permission
    
    async def _check_permission_db(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_path: str,
        action: Action,
        context: Optional[Dict[str, str]] = None
    ) -> bool:
        """Check permission in database"""
        async with get_db_session() as session:
            # Use the database function for complex permission logic
            result = await session.execute(
                text("""
                    SELECT check_user_permission(
                        :user_id::uuid,
                        :resource_type,
                        :resource_path,
                        :action
                    )
                """),
                {
                    "user_id": user_id,
                    "resource_type": resource_type,
                    "resource_path": resource_path,
                    "action": action
                }
            )
            return result.scalar()
    
    async def get_user_permissions(
        self,
        user_id: str,
        resource_type: Optional[ResourceType] = None
    ) -> List[Dict[str, str]]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User ID
            resource_type: Optional filter by resource type
            
        Returns:
            List of permission dictionaries
        """
        cache_key = f"rbac:user_perms:{user_id}"
        if resource_type:
            cache_key += f":{resource_type}"
        
        # Check cache
        cached = await redis_client.get(cache_key)
        if cached:
            import json
            return json.loads(cached)
        
        # Query database
        async with get_db_session() as session:
            query = text("""
                SELECT * FROM get_user_permissions(:user_id::uuid)
                WHERE (:resource_type IS NULL OR resource_type = :resource_type)
            """)
            
            result = await session.execute(
                query,
                {"user_id": user_id, "resource_type": resource_type}
            )
            
            permissions = [
                {
                    "resource_type": row.resource_type,
                    "resource_path": row.resource_path,
                    "action": row.action,
                    "source": row.source
                }
                for row in result
            ]
        
        # Cache result
        import json
        await redis_client.setex(cache_key, self.cache_ttl, json.dumps(permissions))
        
        return permissions
    
    # ====================================================================
    # ROLE MANAGEMENT
    # ====================================================================
    
    async def assign_role(
        self,
        user_id: str,
        role_name: str,
        assigned_by: str,
        context_type: ContextType = ContextType.GLOBAL,
        context_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Assign a role to a user.
        
        Args:
            user_id: User to assign role to
            role_name: Name of role to assign
            assigned_by: User ID who is assigning the role
            context_type: Context for role (global, team, workspace)
            context_id: ID of context (team_id, workspace_id)
            expires_at: Optional expiration time
            
        Returns:
            bool: Success status
        """
        async with get_db_session() as session:
            # Get role ID
            role_result = await session.execute(
                text("SELECT id FROM roles WHERE name = :role_name"),
                {"role_name": role_name}
            )
            role_id = role_result.scalar()
            
            if not role_id:
                logger.error(f"Role not found: {role_name}")
                return False
            
            # Insert user role
            await session.execute(
                text("""
                    INSERT INTO user_roles 
                    (user_id, role_id, context_type, context_id, assigned_by, expires_at)
                    VALUES (:user_id, :role_id, :context_type, :context_id, :assigned_by, :expires_at)
                    ON CONFLICT (user_id, role_id, COALESCE(context_id, 'global')) 
                    DO UPDATE SET 
                        assigned_by = :assigned_by,
                        assigned_at = CURRENT_TIMESTAMP,
                        expires_at = :expires_at
                """),
                {
                    "user_id": user_id,
                    "role_id": role_id,
                    "context_type": context_type,
                    "context_id": context_id,
                    "assigned_by": assigned_by,
                    "expires_at": expires_at
                }
            )
            
            await session.commit()
            
            # Invalidate cache
            await self._invalidate_user_cache(user_id)
            
            # Audit log
            await self._log_permission_event(
                "role_assigned",
                assigned_by,
                user_id,
                {"role": role_name, "context": context_type, "context_id": context_id}
            )
            
            return True
    
    async def revoke_role(
        self,
        user_id: str,
        role_name: str,
        revoked_by: str,
        context_id: Optional[str] = None
    ) -> bool:
        """Revoke a role from a user"""
        async with get_db_session() as session:
            # Get role ID
            role_result = await session.execute(
                text("SELECT id FROM roles WHERE name = :role_name"),
                {"role_name": role_name}
            )
            role_id = role_result.scalar()
            
            if not role_id:
                return False
            
            # Delete user role
            await session.execute(
                text("""
                    DELETE FROM user_roles 
                    WHERE user_id = :user_id 
                      AND role_id = :role_id
                      AND COALESCE(context_id, 'global') = COALESCE(:context_id, 'global')
                """),
                {
                    "user_id": user_id,
                    "role_id": role_id,
                    "context_id": context_id
                }
            )
            
            await session.commit()
            
            # Invalidate cache
            await self._invalidate_user_cache(user_id)
            
            # Audit log
            await self._log_permission_event(
                "role_revoked",
                revoked_by,
                user_id,
                {"role": role_name, "context_id": context_id}
            )
            
            return True
    
    # ====================================================================
    # TEAM AND WORKSPACE MANAGEMENT
    # ====================================================================
    
    async def add_team_member(
        self,
        team_id: str,
        user_id: str,
        team_role: TeamRole,
        invited_by: str
    ) -> bool:
        """Add a user to a team"""
        async with get_db_session() as session:
            await session.execute(
                text("""
                    INSERT INTO team_members 
                    (team_id, user_id, team_role, invited_by)
                    VALUES (:team_id, :user_id, :team_role, :invited_by)
                    ON CONFLICT (team_id, user_id) 
                    DO UPDATE SET team_role = :team_role
                """),
                {
                    "team_id": team_id,
                    "user_id": user_id,
                    "team_role": team_role,
                    "invited_by": invited_by
                }
            )
            
            await session.commit()
            
            # Assign team-specific role
            await self.assign_role(
                user_id,
                f"team_{team_role}",  # e.g., "team_member"
                invited_by,
                ContextType.TEAM,
                team_id
            )
            
            return True
    
    async def add_workspace_member(
        self,
        workspace_id: str,
        user_id: str,
        invited_by: str
    ) -> bool:
        """Add a user to a workspace"""
        async with get_db_session() as session:
            await session.execute(
                text("""
                    INSERT INTO workspace_members 
                    (workspace_id, user_id, invited_by)
                    VALUES (:workspace_id, :user_id, :invited_by)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "invited_by": invited_by
                }
            )
            
            await session.commit()
            
            # Workspaces typically have flat permissions
            await self.assign_role(
                user_id,
                "workspace_member",
                invited_by,
                ContextType.WORKSPACE,
                workspace_id
            )
            
            return True
    
    # ====================================================================
    # KB-SPECIFIC PERMISSIONS
    # ====================================================================
    
    async def check_kb_access(
        self,
        user_id: str,
        kb_path: str,
        action: Action = Action.READ
    ) -> bool:
        """
        Check KB-specific access permissions.
        
        This method understands KB path patterns like:
        - /kb/users/{user_id}/* - User's personal KB
        - /kb/teams/{team_id}/* - Team KB
        - /kb/workspaces/{workspace_id}/* - Workspace KB
        - /kb/shared/* - Shared KB content
        """
        # Personal KB - users always have full access to their own KB
        if kb_path.startswith(f"/kb/users/{user_id}/"):
            return True
        
        # Check standard permissions
        return await self.check_permission(
            user_id,
            ResourceType.KB,
            kb_path,
            action
        )
    
    async def get_accessible_kb_paths(self, user_id: str) -> List[str]:
        """
        Get all KB paths accessible to a user.
        
        Returns:
            List of KB paths the user can access
        """
        paths = []
        
        # Always include personal KB
        paths.append(f"/kb/users/{user_id}")
        
        # Always include shared KB (read-only)
        paths.append("/kb/shared")
        
        # Get team memberships
        async with get_db_session() as session:
            teams_result = await session.execute(
                text("""
                    SELECT team_id FROM team_members WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            )
            for row in teams_result:
                paths.append(f"/kb/teams/{row.team_id}")
        
            # Get workspace memberships
            workspaces_result = await session.execute(
                text("""
                    SELECT workspace_id FROM workspace_members WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            )
            for row in workspaces_result:
                paths.append(f"/kb/workspaces/{row.workspace_id}")
        
        # Get explicitly shared paths
        shared_paths = await self._get_shared_resource_paths(user_id, ResourceType.KB)
        paths.extend(shared_paths)
        
        return paths
    
    # ====================================================================
    # RESOURCE SHARING
    # ====================================================================
    
    async def share_resource(
        self,
        resource_type: ResourceType,
        resource_id: str,
        shared_by: str,
        principal_type: str,  # 'user', 'team', 'workspace', 'role'
        principal_id: str,
        permissions: List[Action],
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Share a resource with a user, team, workspace, or role"""
        async with get_db_session() as session:
            await session.execute(
                text("""
                    INSERT INTO resource_permissions
                    (resource_type, resource_id, principal_type, principal_id, 
                     permissions, granted_by, expires_at)
                    VALUES (:resource_type, :resource_id, :principal_type, :principal_id,
                            :permissions, :granted_by, :expires_at)
                    ON CONFLICT (resource_type, resource_id, principal_type, principal_id)
                    DO UPDATE SET 
                        permissions = :permissions,
                        granted_by = :granted_by,
                        granted_at = CURRENT_TIMESTAMP,
                        expires_at = :expires_at
                """),
                {
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "principal_type": principal_type,
                    "principal_id": principal_id,
                    "permissions": permissions,
                    "granted_by": shared_by,
                    "expires_at": expires_at
                }
            )
            
            await session.commit()
            
            # Invalidate caches for affected users
            if principal_type == "user":
                await self._invalidate_user_cache(principal_id)
            elif principal_type == "team":
                await self._invalidate_team_cache(principal_id)
            elif principal_type == "workspace":
                await self._invalidate_workspace_cache(principal_id)
            
            # Audit log
            await self._log_permission_event(
                "resource_shared",
                shared_by,
                principal_id,
                {
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "permissions": permissions
                }
            )
            
            return True
    
    # ====================================================================
    # UTILITY METHODS
    # ====================================================================
    
    async def _get_shared_resource_paths(
        self,
        user_id: str,
        resource_type: ResourceType
    ) -> List[str]:
        """Get resources shared with a user"""
        async with get_db_session() as session:
            # Direct shares to user
            direct_result = await session.execute(
                text("""
                    SELECT DISTINCT resource_id 
                    FROM resource_permissions
                    WHERE resource_type = :resource_type
                      AND principal_type = 'user'
                      AND principal_id = :user_id
                      AND (expires_at IS NULL OR expires_at > NOW())
                """),
                {"resource_type": resource_type, "user_id": user_id}
            )
            
            paths = [row.resource_id for row in direct_result]
            
            # Shares via teams
            team_result = await session.execute(
                text("""
                    SELECT DISTINCT rp.resource_id
                    FROM resource_permissions rp
                    JOIN team_members tm ON rp.principal_id = tm.team_id::text
                    WHERE rp.resource_type = :resource_type
                      AND rp.principal_type = 'team'
                      AND tm.user_id = :user_id
                      AND (rp.expires_at IS NULL OR rp.expires_at > NOW())
                """),
                {"resource_type": resource_type, "user_id": user_id}
            )
            
            paths.extend([row.resource_id for row in team_result])
            
            # Shares via workspaces
            workspace_result = await session.execute(
                text("""
                    SELECT DISTINCT rp.resource_id
                    FROM resource_permissions rp
                    JOIN workspace_members wm ON rp.principal_id = wm.workspace_id::text
                    WHERE rp.resource_type = :resource_type
                      AND rp.principal_type = 'workspace'
                      AND wm.user_id = :user_id
                      AND (rp.expires_at IS NULL OR rp.expires_at > NOW())
                """),
                {"resource_type": resource_type, "user_id": user_id}
            )
            
            paths.extend([row.resource_id for row in workspace_result])
            
            return list(set(paths))  # Remove duplicates
    
    async def _invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        pattern = f"rbac:*:{user_id}:*"
        # Note: This is a simplified version. In production, you'd want
        # to track cache keys more precisely or use Redis SCAN
        await redis_client.delete(f"rbac:user_perms:{user_id}")
    
    async def _invalidate_team_cache(self, team_id: str):
        """Invalidate cache for all team members"""
        async with get_db_session() as session:
            result = await session.execute(
                text("SELECT user_id FROM team_members WHERE team_id = :team_id"),
                {"team_id": team_id}
            )
            for row in result:
                await self._invalidate_user_cache(row.user_id)
    
    async def _invalidate_workspace_cache(self, workspace_id: str):
        """Invalidate cache for all workspace members"""
        async with get_db_session() as session:
            result = await session.execute(
                text("SELECT user_id FROM workspace_members WHERE workspace_id = :workspace_id"),
                {"workspace_id": workspace_id}
            )
            for row in result:
                await self._invalidate_user_cache(row.user_id)
    
    async def _log_permission_event(
        self,
        event_type: str,
        actor_id: str,
        target_id: str,
        details: Dict[str, Any]
    ):
        """Log permission-related events for audit"""
        try:
            async with get_db_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO permission_audit_log
                        (event_type, actor_id, target_user_id, permission_details)
                        VALUES (:event_type, :actor_id, :target_id, :details)
                    """),
                    {
                        "event_type": event_type,
                        "actor_id": actor_id,
                        "target_id": target_id,
                        "details": details
                    }
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to log permission event: {e}")

# ========================================================================
# RBAC DEPENDENCY FOR FASTAPI
# ========================================================================

# Global RBAC manager instance
rbac_manager = RBACManager()

async def require_permission(
    resource_type: ResourceType,
    action: Action,
    resource_path_param: Optional[str] = None
):
    """
    FastAPI dependency to require specific permissions.
    
    Usage:
        @app.get("/kb/{path:path}")
        async def read_kb(
            path: str,
            auth: dict = Depends(get_current_auth),
            _: None = Depends(require_permission(ResourceType.KB, Action.READ))
        ):
            # User has permission to read KB
    """
    from fastapi import Depends, HTTPException, Request
    from .security import get_current_auth
    
    async def permission_checker(
        request: Request,
        auth: dict = Depends(get_current_auth)
    ):
        user_id = auth.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        
        # Build resource path
        resource_path = resource_path_param
        if not resource_path and resource_type == ResourceType.KB:
            # Extract from request path
            resource_path = request.url.path
        
        # Check permission
        has_permission = await rbac_manager.check_permission(
            user_id,
            resource_type,
            resource_path,
            action
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {action} on {resource_type}"
            )
        
        return True
    
    return permission_checker

# Convenience decorators
require_kb_read = require_permission(ResourceType.KB, Action.READ)
require_kb_write = require_permission(ResourceType.KB, Action.WRITE)
require_kb_admin = require_permission(ResourceType.KB, Action.ADMIN)
require_api_access = require_permission(ResourceType.API, Action.ACCESS)
require_admin = require_permission(ResourceType.ADMIN, Action.ADMIN)