"""
Simple RBAC implementation that works with asyncpg directly
"""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from uuid import UUID
import uuid
import logging

from .database import get_db_session
from .logging import get_logger
from .redis_client import redis_client
from .config import settings

logger = get_logger("rbac_simple")

class SimpleRBACManager:
    """
    Simplified RBAC manager that works directly with asyncpg
    """
    
    def __init__(self):
        self.cache_ttl = getattr(settings, 'RBAC_CACHE_TTL', 300)  # 5 minutes

    def ensure_uuid(self, user_id: Union[str, UUID]) -> str:
        """Ensure user_id is a valid UUID string"""
        if isinstance(user_id, UUID):
            return str(user_id)
        
        if isinstance(user_id, str):
            try:
                uuid.UUID(user_id)
                return user_id
            except ValueError:
                logger.warning(f"Invalid UUID format for user_id: {user_id}")
                raise ValueError(f"user_id must be a valid UUID, got: {user_id}")
        
        raise TypeError(f"user_id must be str or UUID, got {type(user_id)}")

    async def get_accessible_kb_paths(self, user_id: str) -> List[str]:
        """
        Get all KB paths accessible to a user.
        """
        try:
            validated_user_id = self.ensure_uuid(user_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid user_id in get_accessible_kb_paths: {e}")
            return []

        paths = []
        
        # Always include personal KB
        paths.append(f"/kb/users/{user_id}")
        
        # Always include shared KB (read-only)
        paths.append("/kb/shared")
        
        try:
            # Get team memberships
            async with get_db_session() as connection:
                teams_result = await connection.fetch(
                    "SELECT team_id FROM team_members WHERE user_id = $1",
                    validated_user_id
                )
                for row in teams_result:
                    paths.append(f"/kb/teams/{row['team_id']}")
            
                # Get workspace memberships
                workspaces_result = await connection.fetch(
                    "SELECT workspace_id FROM workspace_members WHERE user_id = $1",
                    validated_user_id
                )
                for row in workspaces_result:
                    paths.append(f"/kb/workspaces/{row['workspace_id']}")
        except Exception as e:
            logger.error(f"Error getting team/workspace memberships: {e}")
            # Continue with just personal and shared paths

        return paths

    async def check_kb_access(self, user_id: str, kb_path: str, action: str = "read") -> bool:
        """
        Check KB-specific access permissions.
        For now, this is permissive - users can access their own KB and shared KB.
        """
        try:
            validated_user_id = self.ensure_uuid(user_id)
        except (ValueError, TypeError):
            return False

        # Personal KB - users always have full access to their own KB
        if kb_path.startswith(f"/kb/users/{user_id}/"):
            return True
        
        # Shared KB - always readable
        if kb_path.startswith("/kb/shared"):
            return True
        
        # For now, allow access to all KB paths for authenticated users
        # TODO: Implement proper team/workspace checking
        return True

# Global simple RBAC manager instance
rbac_manager = SimpleRBACManager()

# Compatibility exports
ResourceType = type('ResourceType', (), {'KB': 'kb'})()
Action = type('Action', (), {'READ': 'read', 'WRITE': 'write', 'DELETE': 'delete'})()