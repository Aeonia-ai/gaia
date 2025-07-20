"""
KB Storage Manager with RBAC Integration

This extends the existing KB storage manager to include full RBAC support
for multi-user knowledge base access control.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from app.shared.rbac_fixed import (
    rbac_manager,
    ResourceType,
    Action,
    ContextType,
    require_permission
)
from app.shared.config import settings
from app.shared.logging import get_logger

# Import the existing storage manager
from .kb_storage_manager import KBStorageManager, StorageMode

logger = get_logger("kb_rbac")

class KBStorageWithRBAC(KBStorageManager):
    """
    Enhanced KB Storage Manager that enforces RBAC permissions
    on all operations.
    """
    
    async def search_documents(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        contexts: Optional[List[str]] = None,
        include_content: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search documents with RBAC filtering.
        
        Only returns documents the user has permission to read.
        """
        if not user_id:
            # No user = no results (secure by default)
            return {"results": [], "total": 0}
        
        # Get accessible paths for user
        accessible_paths = await rbac_manager.get_accessible_kb_paths(user_id)
        
        # Filter contexts by accessible paths
        if contexts:
            filtered_contexts = []
            for context in contexts:
                for path in accessible_paths:
                    if context.startswith(path):
                        filtered_contexts.append(context)
                        break
            contexts = filtered_contexts if filtered_contexts else None
        
        # Perform search with filtered contexts
        results = await super().search_documents(
            query=query,
            limit=limit,
            offset=offset,
            contexts=contexts or accessible_paths,
            include_content=include_content,
            **kwargs
        )
        
        # Double-check permissions on results (defense in depth)
        filtered_results = []
        for result in results.get("results", []):
            doc_path = result.get("path", "")
            if await rbac_manager.check_kb_access(user_id, doc_path, Action.READ):
                filtered_results.append(result)
        
        results["results"] = filtered_results
        results["total"] = len(filtered_results)
        
        return results
    
    async def get_document(
        self,
        path: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Get a document with RBAC check.
        """
        if not user_id:
            logger.warning(f"Attempted to get document without user_id: {path}")
            return None
        
        # Check read permission
        kb_path = self._normalize_kb_path(path)
        if not await rbac_manager.check_kb_access(user_id, kb_path, Action.READ):
            logger.warning(f"User {user_id} denied read access to: {kb_path}")
            return None
        
        # Get document
        return await super().get_document(path, **kwargs)
    
    async def save_document(
        self,
        path: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Save a document with RBAC check.
        """
        if not user_id:
            return {
                "success": False,
                "error": "authentication_required",
                "message": "User ID is required for write operations"
            }
        
        # Normalize path
        kb_path = self._normalize_kb_path(path)
        
        # Check write permission
        if not await rbac_manager.check_kb_access(user_id, kb_path, Action.WRITE):
            logger.warning(f"User {user_id} denied write access to: {kb_path}")
            return {
                "success": False,
                "error": "permission_denied",
                "message": f"You don't have permission to write to {kb_path}"
            }
        
        # If creating in a team/workspace, verify membership
        if "/teams/" in kb_path or "/workspaces/" in kb_path:
            if not await self._verify_context_membership(user_id, kb_path):
                return {
                    "success": False,
                    "error": "not_a_member",
                    "message": "You must be a member to write to this space"
                }
        
        # Add user info to metadata
        if metadata is None:
            metadata = {}
        metadata["last_modified_by"] = user_id
        
        # Save document
        return await super().save_document(
            path=path,
            content=content,
            metadata=metadata,
            user_id=user_id,
            **kwargs
        )
    
    async def delete_document(
        self,
        path: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Delete a document with RBAC check.
        """
        if not user_id:
            return {
                "success": False,
                "error": "authentication_required",
                "message": "User ID is required for delete operations"
            }
        
        # Check delete permission
        kb_path = self._normalize_kb_path(path)
        if not await rbac_manager.check_kb_access(user_id, kb_path, Action.DELETE):
            logger.warning(f"User {user_id} denied delete access to: {kb_path}")
            return {
                "success": False,
                "error": "permission_denied",
                "message": f"You don't have permission to delete {kb_path}"
            }
        
        # Delete document
        return await super().delete_document(path, **kwargs)
    
    async def list_documents(
        self,
        directory: str = "/",
        user_id: Optional[str] = None,
        pattern: Optional[str] = None,
        recursive: bool = False,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        List documents in a directory with RBAC filtering.
        """
        if not user_id:
            return []
        
        # Check if user can read this directory
        kb_path = self._normalize_kb_path(directory)
        if not await rbac_manager.check_kb_access(user_id, kb_path, Action.READ):
            logger.warning(f"User {user_id} denied list access to: {kb_path}")
            return []
        
        # Get all documents
        all_docs = await super().list_documents(
            directory=directory,
            pattern=pattern,
            recursive=recursive,
            **kwargs
        )
        
        # Filter by permissions
        accessible_docs = []
        for doc in all_docs:
            doc_path = doc.get("path", "")
            if await rbac_manager.check_kb_access(user_id, doc_path, Action.READ):
                accessible_docs.append(doc)
        
        return accessible_docs
    
    async def share_document(
        self,
        path: str,
        shared_by: str,
        recipients: Optional[List[str]] = None,
        teams: Optional[List[str]] = None,
        workspaces: Optional[List[str]] = None,
        permissions: List[str] = ["read"],
        message: Optional[str] = None,
        expires_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Share a KB document with users, teams, or workspaces.
        """
        kb_path = self._normalize_kb_path(path)
        
        # Check if user can share this document
        if not await rbac_manager.check_kb_access(shared_by, kb_path, Action.SHARE):
            return {
                "success": False,
                "error": "permission_denied",
                "message": "You don't have permission to share this document"
            }
        
        results = {
            "success": True,
            "shared_with": {
                "users": [],
                "teams": [],
                "workspaces": []
            }
        }
        
        # Convert string permissions to Action enums
        action_perms = []
        for perm in permissions:
            if perm == "read":
                action_perms.append(Action.READ)
            elif perm == "write":
                action_perms.append(Action.WRITE)
            elif perm == "delete":
                action_perms.append(Action.DELETE)
        
        # Share with individual users
        if recipients:
            for recipient_id in recipients:
                success = await rbac_manager.share_resource(
                    resource_type=ResourceType.KB,
                    resource_id=kb_path,
                    shared_by=shared_by,
                    principal_type="user",
                    principal_id=recipient_id,
                    permissions=action_perms,
                    expires_at=expires_at
                )
                if success:
                    results["shared_with"]["users"].append(recipient_id)
        
        # Share with teams
        if teams:
            for team_id in teams:
                success = await rbac_manager.share_resource(
                    resource_type=ResourceType.KB,
                    resource_id=kb_path,
                    shared_by=shared_by,
                    principal_type="team",
                    principal_id=team_id,
                    permissions=action_perms,
                    expires_at=expires_at
                )
                if success:
                    results["shared_with"]["teams"].append(team_id)
        
        # Share with workspaces
        if workspaces:
            for workspace_id in workspaces:
                success = await rbac_manager.share_resource(
                    resource_type=ResourceType.KB,
                    resource_id=kb_path,
                    shared_by=shared_by,
                    principal_type="workspace",
                    principal_id=workspace_id,
                    permissions=action_perms,
                    expires_at=expires_at
                )
                if success:
                    results["shared_with"]["workspaces"].append(workspace_id)
        
        # Log share activity in KB metadata
        if self.storage_mode in [StorageMode.DATABASE, StorageMode.HYBRID]:
            await self._log_share_activity(
                kb_path, shared_by, results["shared_with"], message
            )
        
        return results
    
    async def create_workspace(
        self,
        name: str,
        display_name: str,
        description: Optional[str],
        created_by: str,
        initial_members: Optional[List[str]] = None,
        workspace_type: str = "project"
    ) -> Dict[str, Any]:
        """
        Create a new workspace for KB collaboration.
        """
        from app.shared.database import get_db_session
        from sqlalchemy import text
        
        async with get_db_session() as session:
            # Create workspace
            result = await session.execute(
                text("""
                    INSERT INTO workspaces 
                    (name, display_name, description, workspace_type, created_by)
                    VALUES (:name, :display_name, :description, :workspace_type, :created_by)
                    RETURNING id
                """),
                {
                    "name": name,
                    "display_name": display_name,
                    "description": description,
                    "workspace_type": workspace_type,
                    "created_by": created_by
                }
            )
            workspace_id = str(result.scalar())
            
            # Add creator as member
            await rbac_manager.add_workspace_member(
                workspace_id, created_by, created_by
            )
            
            # Add initial members
            if initial_members:
                for member_id in initial_members:
                    await rbac_manager.add_workspace_member(
                        workspace_id, member_id, created_by
                    )
            
            # Create KB directory for workspace
            workspace_kb_path = f"/kb/workspaces/{workspace_id}"
            if self.storage_mode == StorageMode.GIT:
                # Create directory in Git
                workspace_dir = Path(self.kb_path) / f"workspaces/{workspace_id}"
                workspace_dir.mkdir(parents=True, exist_ok=True)
                
                # Create README
                readme_path = workspace_dir / "README.md"
                readme_content = f"""# {display_name}

{description or 'Workspace for collaborative knowledge management.'}

Created by: {created_by}
Created at: {datetime.now().isoformat()}
Type: {workspace_type}
"""
                readme_path.write_text(readme_content)
            
            await session.commit()
            
            return {
                "success": True,
                "workspace_id": workspace_id,
                "kb_path": workspace_kb_path,
                "members": [created_by] + (initial_members or [])
            }
    
    async def create_team(
        self,
        name: str,
        display_name: str,
        description: Optional[str],
        created_by: str,
        parent_team_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new team for KB collaboration.
        """
        from app.shared.database import get_db_session
        from sqlalchemy import text
        
        async with get_db_session() as session:
            # Create team
            result = await session.execute(
                text("""
                    INSERT INTO teams 
                    (name, display_name, description, parent_team_id, created_by)
                    VALUES (:name, :display_name, :description, :parent_team_id, :created_by)
                    RETURNING id
                """),
                {
                    "name": name,
                    "display_name": display_name,
                    "description": description,
                    "parent_team_id": parent_team_id,
                    "created_by": created_by
                }
            )
            team_id = str(result.scalar())
            
            # Add creator as team owner
            await rbac_manager.add_team_member(
                team_id, created_by, "owner", created_by
            )
            
            # Create KB directory for team
            team_kb_path = f"/kb/teams/{team_id}"
            if self.storage_mode == StorageMode.GIT:
                # Create directory structure
                team_dir = Path(self.kb_path) / f"teams/{team_id}"
                for subdir in ["standards", "onboarding", "knowledge-base"]:
                    (team_dir / subdir).mkdir(parents=True, exist_ok=True)
            
            await session.commit()
            
            return {
                "success": True,
                "team_id": team_id,
                "kb_path": team_kb_path
            }
    
    # ====================================================================
    # HELPER METHODS
    # ====================================================================
    
    def _normalize_kb_path(self, path: str) -> str:
        """Ensure path starts with /kb/"""
        if not path.startswith("/kb/"):
            if path.startswith("kb/"):
                path = "/" + path
            elif path.startswith("/"):
                path = "/kb" + path
            else:
                path = "/kb/" + path
        return path
    
    async def _verify_context_membership(self, user_id: str, kb_path: str) -> bool:
        """Verify user is member of team/workspace for path"""
        from app.shared.database import get_db_session
        from sqlalchemy import text
        
        if "/teams/" in kb_path:
            # Extract team ID from path
            parts = kb_path.split("/")
            if len(parts) > 3 and parts[2] == "teams":
                team_id = parts[3]
                
                async with get_db_session() as session:
                    result = await session.execute(
                        text("""
                            SELECT 1 FROM team_members 
                            WHERE team_id = :team_id AND user_id = :user_id
                        """),
                        {"team_id": team_id, "user_id": user_id}
                    )
                    return result.scalar() is not None
        
        elif "/workspaces/" in kb_path:
            # Extract workspace ID from path
            parts = kb_path.split("/")
            if len(parts) > 3 and parts[2] == "workspaces":
                workspace_id = parts[3]
                
                async with get_db_session() as session:
                    result = await session.execute(
                        text("""
                            SELECT 1 FROM workspace_members 
                            WHERE workspace_id = :workspace_id AND user_id = :user_id
                        """),
                        {"workspace_id": workspace_id, "user_id": user_id}
                    )
                    return result.scalar() is not None
        
        return True  # Not a team/workspace path
    
    async def _log_share_activity(
        self,
        kb_path: str,
        shared_by: str,
        shared_with: Dict[str, List[str]],
        message: Optional[str] = None
    ):
        """Log sharing activity in KB metadata"""
        # This would update document metadata with sharing history
        # Implementation depends on storage backend
        pass

# ====================================================================
# FASTAPI INTEGRATION
# ====================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from app.shared.security import get_current_auth_legacy
from app.models.kb import ShareRequest, WorkspaceCreateRequest, TeamCreateRequest

router = APIRouter(prefix="/kb", tags=["knowledge-base"])

# Initialize storage with RBAC
kb_storage_rbac = KBStorageWithRBAC()

@router.get("/search")
async def search_kb(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    contexts: Optional[List[str]] = Query(None),
    auth: dict = Depends(get_current_auth_legacy)
):
    """Search KB with RBAC filtering"""
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    results = await kb_storage_rbac.search_documents(
        query=q,
        user_id=user_id,
        limit=limit,
        offset=offset,
        contexts=contexts
    )
    
    return results

@router.get("/document/{path:path}")
async def get_document(
    path: str,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get a KB document with permission check"""
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    doc = await kb_storage_rbac.get_document(path, user_id=user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied")
    
    return doc

@router.post("/share")
async def share_document(
    request: ShareRequest,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Share a KB document"""
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    result = await kb_storage_rbac.share_document(
        path=request.path,
        shared_by=user_id,
        recipients=request.recipients,
        teams=request.teams,
        workspaces=request.workspaces,
        permissions=request.permissions,
        message=request.message,
        expires_at=request.expires_at
    )
    
    if not result["success"]:
        raise HTTPException(status_code=403, detail=result.get("message"))
    
    return result

@router.post("/workspace")
async def create_workspace(
    request: WorkspaceCreateRequest,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Create a new workspace"""
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if user has permission to create workspaces
    if not await rbac_manager.check_permission(
        user_id, ResourceType.KB, "/kb/workspaces", Action.CREATE
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    result = await kb_storage_rbac.create_workspace(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        created_by=user_id,
        initial_members=request.initial_members,
        workspace_type=request.workspace_type
    )
    
    return result

@router.post("/team")
async def create_team(
    request: TeamCreateRequest,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Create a new team"""
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if user has permission to create teams
    if not await rbac_manager.check_permission(
        user_id, ResourceType.KB, "/kb/teams", Action.CREATE
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    result = await kb_storage_rbac.create_team(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        created_by=user_id,
        parent_team_id=request.parent_team_id
    )
    
    return result