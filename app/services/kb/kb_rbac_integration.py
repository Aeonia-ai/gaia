"""
KB RBAC Integration Module

This module integrates the KB MCP server with RBAC when multi-user mode is enabled.
It wraps the kb_server methods to add user context and permission checking.
"""

from typing import Dict, Any, Optional
from app.shared.config import settings
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Import the appropriate storage based on multi-user mode
if getattr(settings, 'KB_MULTI_USER_ENABLED', False):
    from .kb_storage_with_rbac import kb_storage_rbac as storage_manager
    logger.info("KB RBAC Integration: Using multi-user storage with RBAC")
else:
    from .kb_storage_manager import kb_storage as storage_manager
    logger.info("KB RBAC Integration: Using single-user storage")

class KBRBACWrapper:
    """
    Wraps KB operations with RBAC when multi-user mode is enabled.
    Falls back to direct file operations when in single-user mode.
    """
    
    def __init__(self, kb_server):
        self.kb_server = kb_server
        self.multi_user = getattr(settings, 'KB_MULTI_USER_ENABLED', False)
        self.storage = storage_manager
        
    async def search_kb(
        self,
        query: str,
        user_id: Optional[str] = None,
        contexts: Optional[list] = None,
        limit: int = 20,
        include_content: bool = False,
        use_index_filter: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search KB with optional RBAC filtering.
        """
        if self.multi_user and user_id:
            # Use storage manager for RBAC-aware search
            logger.info(f"RBAC search for user {user_id}: {query}")
            
            result = await self.storage.search_documents(
                query=query,
                user_id=user_id,
                contexts=contexts,
                limit=limit,
                include_content=include_content,
                **kwargs
            )
            
            # Convert storage format to KB server format
            return {
                "success": True,
                "results": [
                    {
                        "file_path": r.get("path", ""),
                        "relative_path": r.get("path", "").replace("/kb/", ""),
                        "content_excerpt": r.get("excerpt", ""),
                        "context": r.get("context", "unknown"),
                        "keywords": r.get("keywords", []),
                        "relevance_score": r.get("score", 0.0)
                    }
                    for r in result.get("results", [])
                ],
                "total_results": result.get("total", 0)
            }
        else:
            # Fall back to direct KB server search
            return await self.kb_server.search_kb(
                query=query,
                contexts=contexts,
                limit=limit,
                include_content=include_content,
                use_index_filter=use_index_filter
            )
    
    async def read_kb_file(
        self,
        path: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Read a KB file with optional RBAC check.
        """
        if self.multi_user and user_id:
            logger.info(f"RBAC read for user {user_id}: {path}")
            
            # Ensure path starts with /kb/
            if not path.startswith("/kb/"):
                path = f"/kb/{path}"
            
            doc = await self.storage.get_document(path, user_id=user_id)
            
            if doc:
                return {
                    "success": True,
                    "content": doc.get("content", ""),
                    "metadata": doc.get("metadata", {}),
                    "path": path
                }
            else:
                return {
                    "success": False,
                    "error": "file_not_found_or_access_denied",
                    "message": f"File not found or access denied: {path}"
                }
        else:
            # Fall back to direct file read
            return await self.kb_server.read_kb_file(path)
    
    async def list_kb_directory(
        self,
        path: str = "/",
        pattern: str = "*.md",
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        List KB directory with optional RBAC filtering.
        """
        if self.multi_user and user_id:
            logger.info(f"RBAC list for user {user_id}: {path}")
            
            # Ensure path has /kb/ prefix
            if not path.startswith("/kb/"):
                path = f"/kb/{path}"
            
            docs = await self.storage.list_documents(
                directory=path,
                user_id=user_id,
                pattern=pattern,
                recursive=False
            )
            
            return {
                "success": True,
                "files": [
                    {
                        "name": doc.get("name", ""),
                        "path": doc.get("path", ""),
                        "is_directory": doc.get("is_directory", False),
                        "size": doc.get("size", 0),
                        "modified": doc.get("modified", "")
                    }
                    for doc in docs
                ]
            }
        else:
            # Fall back to direct listing
            return await self.kb_server.list_kb_directory(path, pattern)
    
    # Delegate other methods directly to kb_server
    def __getattr__(self, name):
        """Delegate undefined methods to kb_server"""
        return getattr(self.kb_server, name)

# Create wrapped instance
def create_rbac_kb_server():
    """Create KB server with optional RBAC wrapper"""
    from .kb_mcp_server import kb_server as original_kb_server
    
    if getattr(settings, 'KB_MULTI_USER_ENABLED', False):
        logger.info("Creating RBAC-wrapped KB server")
        return KBRBACWrapper(original_kb_server)
    else:
        logger.info("Using standard KB server")
        return original_kb_server

# Export the wrapped server
kb_server_with_rbac = create_rbac_kb_server()