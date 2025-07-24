"""
KB Storage Manager

Provides a unified interface for different KB storage backends:
- Git-based storage (original implementation)
- Database storage (PostgreSQL)
- Hybrid storage (Database + Git backup)

This allows switching between storage modes via configuration
while maintaining the same API interface.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from enum import Enum

from app.shared.config import settings
from app.shared.logging import get_logger
from app.services.kb.kb_mcp_server import KBMCPServer
from app.services.kb.kb_database_storage import kb_db_storage, KBDocument
from app.services.kb.kb_hybrid_storage import kb_hybrid_storage

logger = get_logger(__name__)

class StorageMode(Enum):
    """Available storage modes"""
    GIT = "git"
    DATABASE = "database" 
    HYBRID = "hybrid"

class KBStorageManager:
    """
    Unified storage manager that delegates to the appropriate backend
    based on configuration.
    
    Configuration via environment variables:
    - KB_STORAGE_MODE: "git", "database", or "hybrid" (default: "git")
    - KB_PATH: Path to KB directory (for git/hybrid modes)
    - KB_DATABASE_URL: PostgreSQL connection (for database/hybrid modes)
    """
    
    def __init__(self):
        # Determine storage mode from configuration
        mode_str = getattr(settings, 'KB_STORAGE_MODE', 'git').lower()
        try:
            self.storage_mode = StorageMode(mode_str)
        except ValueError:
            logger.warning(f"Invalid storage mode '{mode_str}', falling back to git")
            self.storage_mode = StorageMode.GIT
        
        # Initialize the appropriate backend
        self.backend = None
        self._initialize_backend()
        
        logger.info(f"KB Storage Manager initialized with mode: {self.storage_mode.value}")
    
    def _initialize_backend(self):
        """Initialize the storage backend based on mode"""
        kb_path = getattr(settings, 'KB_PATH', '/kb')
        
        if self.storage_mode == StorageMode.GIT:
            # Use original MCP server with Git backend
            self.backend = KBMCPServer(kb_path=kb_path)
            
        elif self.storage_mode == StorageMode.DATABASE:
            # Use database storage
            self.backend = kb_db_storage
            
        elif self.storage_mode == StorageMode.HYBRID:
            # Use hybrid storage (database + git backup)
            self.backend = kb_hybrid_storage
        
        logger.info(f"Storage backend initialized: {type(self.backend).__name__}")
    
    async def initialize(self):
        """Initialize the storage backend"""
        if hasattr(self.backend, 'initialize'):
            await self.backend.initialize()
    
    async def shutdown(self):
        """Shutdown the storage backend"""
        if hasattr(self.backend, 'shutdown'):
            await self.backend.shutdown()
    
    # =============================================================================
    # Unified Storage Interface
    # =============================================================================
    
    async def search_documents(
        self,
        query: str,
        contexts: Optional[List[str]] = None,
        limit: int = 20,
        include_content: bool = False,
        use_index_filter: bool = True
    ) -> Dict[str, Any]:
        """Search documents across all storage backends"""
        
        if self.storage_mode == StorageMode.GIT:
            # Use MCP server search
            return await self.backend.search_kb(
                query=query,
                contexts=contexts,
                limit=limit,
                include_content=include_content,
                use_index_filter=use_index_filter
            )
        else:
            # Use database search (database or hybrid)
            return await self.backend.search_documents(
                query=query,
                contexts=contexts,
                limit=limit
            )
    
    async def get_document(self, path: str) -> Optional[Union[Dict[str, Any], KBDocument]]:
        """Get a document by path"""
        
        if self.storage_mode == StorageMode.GIT:
            # Use MCP server
            return await self.backend.read_kb_file(path)
        else:
            # Use database backends
            return await self.backend.get_document(path)
    
    async def save_document(
        self,
        path: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        change_message: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """Save a document"""
        
        if self.storage_mode == StorageMode.GIT:
            # Use Git-based editor (via imports)
            from app.services.kb.kb_editor import kb_editor
            
            author = None
            if user_id:
                author = {"name": user_id, "email": f"{user_id}@gaia.dev"}
            
            return await kb_editor.write_file(
                path=path,
                content=content,
                message=change_message or "Update document",
                author=author
            )
        else:
            # Use database backends
            return await self.backend.save_document(
                path=path,
                content=content,
                metadata=metadata,
                user_id=user_id,
                change_message=change_message,
                expected_version=expected_version
            )
    
    async def delete_document(
        self,
        path: str,
        user_id: Optional[str] = None,
        change_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete a document"""
        
        if self.storage_mode == StorageMode.GIT:
            # Use Git-based editor
            from app.services.kb.kb_editor import kb_editor
            
            author = None
            if user_id:
                author = {"name": user_id, "email": f"{user_id}@gaia.dev"}
            
            return await kb_editor.delete_file(
                path=path,
                message=change_message or "Delete document",
                author=author
            )
        else:
            # Use database backends
            return await self.backend.delete_document(
                path=path,
                user_id=user_id,
                change_message=change_message
            )
    
    async def move_document(
        self,
        old_path: str,
        new_path: str,
        user_id: Optional[str] = None,
        change_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Move/rename a document"""
        
        if self.storage_mode == StorageMode.GIT:
            # Use Git-based editor
            from app.services.kb.kb_editor import kb_editor
            
            author = None
            if user_id:
                author = {"name": user_id, "email": f"{user_id}@gaia.dev"}
            
            return await kb_editor.move_file(
                old_path=old_path,
                new_path=new_path,
                message=change_message or f"Move {old_path} to {new_path}",
                author=author
            )
        else:
            # Use database backends
            return await self.backend.move_document(
                old_path=old_path,
                new_path=new_path,
                user_id=user_id,
                change_message=change_message
            )
    
    async def list_documents(
        self,
        path: str = "/",
        pattern: str = "*.md",
        include_metadata: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List documents in a directory"""
        
        if self.storage_mode == StorageMode.GIT:
            # Use MCP server
            return await self.backend.list_kb_directory(
                path=path,
                pattern=pattern,
                include_metadata=include_metadata
            )
        else:
            # Use database backends
            path_prefix = path.rstrip('/') if path != '/' else ''
            return await self.backend.list_documents(
                path_prefix=path_prefix,
                limit=limit,
                offset=offset
            )
    
    async def document_exists(self, path: str) -> bool:
        """Check if a document exists"""
        
        if self.storage_mode == StorageMode.GIT:
            # Check file existence
            from pathlib import Path
            kb_path = Path(getattr(settings, 'KB_PATH', '/kb'))
            file_path = kb_path / path
            return file_path.exists() and file_path.is_file()
        else:
            # Use database backends
            return await self.backend.document_exists(path)
    
    async def get_document_history(
        self,
        path: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get document version history"""
        
        if self.storage_mode == StorageMode.GIT:
            # Git history via git log
            from app.services.kb.kb_editor import kb_editor
            return await kb_editor.get_file_history(path, limit=limit)
        else:
            # Use database backends
            history = await self.backend.get_document_history(path, limit)
            return [h.model_dump() if hasattr(h, 'model_dump') else h for h in history]
    
    # =============================================================================
    # Advanced Features (database backends only)
    # =============================================================================
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        stats = {
            "storage_mode": self.storage_mode.value,
            "backend_type": type(self.backend).__name__
        }
        
        if self.storage_mode == StorageMode.GIT:
            # Git repository stats
            from pathlib import Path
            kb_path = Path(getattr(settings, 'KB_PATH', '/kb'))
            if kb_path.exists():
                md_files = list(kb_path.rglob("*.md"))
                stats.update({
                    "total_files": len(md_files),
                    "total_size": sum(f.stat().st_size for f in md_files if f.is_file()),
                    "kb_path": str(kb_path)
                })
        else:
            # Database stats
            try:
                db_stats = await self.backend.list_documents(limit=1)
                if db_stats.get("success"):
                    stats.update({
                        "total_documents": db_stats.get("total_count", 0),
                        "database_connected": True
                    })
            except Exception as e:
                stats.update({
                    "database_connected": False,
                    "error": str(e)
                })
        
        return stats
    
    async def export_to_git(self) -> Dict[str, Any]:
        """Export database content to Git (hybrid/database modes only)"""
        if self.storage_mode == StorageMode.HYBRID:
            return await self.backend.sync_to_git()
        elif self.storage_mode == StorageMode.DATABASE:
            # TODO: Implement direct database to Git export
            return {
                "success": False,
                "error": "export_not_supported",
                "message": "Git export not supported in database-only mode"
            }
        else:
            return {
                "success": False,
                "error": "export_not_needed",
                "message": "Git export not needed in Git mode"
            }
    
    async def import_from_git(self) -> Dict[str, Any]:
        """Import Git content to database (hybrid/database modes only)"""
        if self.storage_mode == StorageMode.HYBRID:
            return await self.backend.restore_from_git()
        elif self.storage_mode == StorageMode.DATABASE:
            # TODO: Implement direct Git to database import
            return {
                "success": False,
                "error": "import_not_supported", 
                "message": "Git import not supported in database-only mode"
            }
        else:
            return {
                "success": False,
                "error": "import_not_needed",
                "message": "Git import not needed in Git mode"
            }
    
    # =============================================================================
    # MCP Tool Compatibility Layer
    # =============================================================================
    
    async def load_kos_context(
        self,
        context_name: str,
        include_dependencies: bool = True,
        depth: int = 2
    ) -> Dict[str, Any]:
        """Load KOS context (compatible with MCP tools)"""
        
        if self.storage_mode == StorageMode.GIT:
            # Use MCP server directly
            return await self.backend.load_kos_context(
                context_name=context_name,
                include_dependencies=include_dependencies,
                depth=depth
            )
        else:
            # Emulate context loading for database backends
            # TODO: Implement proper context loading for database storage
            search_result = await self.search_documents(
                query="",
                contexts=[context_name],
                limit=100
            )
            
            if search_result.get("success"):
                files = [r["path"] for r in search_result["results"]]
                return {
                    "success": True,
                    "context": {
                        "name": context_name,
                        "files": files,
                        "total_files": len(files),
                        "summary": f"Context '{context_name}' with {len(files)} documents"
                    }
                }
            else:
                return search_result
    
    async def get_active_threads(self) -> Dict[str, Any]:
        """Get active KOS threads (compatible with MCP tools)"""
        
        if self.storage_mode == StorageMode.GIT:
            # Use MCP server directly
            return await self.backend.get_active_threads()
        else:
            # Search for thread documents in database
            search_result = await self.search_documents(
                query="",
                contexts=["kos/sessions/threads"],
                limit=50
            )
            
            if search_result.get("success"):
                threads = []
                for result in search_result["results"]:
                    # Parse thread info from metadata
                    metadata = result.get("metadata", {})
                    threads.append({
                        "thread_id": result["path"].split("/")[-1].replace(".md", ""),
                        "title": metadata.get("title", result["path"]),
                        "state": metadata.get("state", "unknown"),
                        "current_action": metadata.get("current_action", ""),
                        "last_updated": result.get("updated_at", "unknown")
                    })
                
                return {
                    "success": True,
                    "threads": threads,
                    "total_threads": len(threads),
                    "active_count": len([t for t in threads if t["state"] == "active"])
                }
            else:
                return search_result

# Global storage manager instance
kb_storage = KBStorageManager()