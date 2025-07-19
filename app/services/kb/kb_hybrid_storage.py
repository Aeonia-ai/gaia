"""
KB Hybrid Storage Backend

Combines PostgreSQL database storage with Git backup for the best of both worlds:
- PostgreSQL: Real-time collaboration, conflict prevention, fast queries
- Git: Version control, disaster recovery, familiar workflow

This storage backend provides:
1. Immediate writes to PostgreSQL (users see changes instantly)
2. Asynchronous Git commits for backup and version control
3. Conflict-free multi-user editing
4. Rich querying and search capabilities
5. Full audit trail and history
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from app.services.kb.kb_database_storage import kb_db_storage, KBDocument
from app.services.kb.kb_editor import KBEditor
from app.shared.logging import get_logger
from app.shared.config import settings

logger = get_logger(__name__)

class KBHybridStorage:
    """
    Hybrid storage combining PostgreSQL (primary) with Git (backup).
    
    Write Flow:
    1. Write to PostgreSQL immediately → Users see changes
    2. Queue Git commit for background processing
    3. Periodic Git commits and pushes
    
    Read Flow:
    1. Always read from PostgreSQL (fastest, most current)
    2. Git is only used for backup/restore scenarios
    
    Benefits:
    - Real-time collaboration (PostgreSQL)
    - No merge conflicts (database transactions)
    - Version control backup (Git)
    - Disaster recovery (Git history)
    - Fast queries (PostgreSQL indexes)
    """
    
    def __init__(self, kb_path: str = "/kb"):
        self.db_storage = kb_db_storage
        self.git_editor = KBEditor(kb_path)
        self.kb_path = Path(kb_path)
        
        # Background task management
        self.git_commit_queue = asyncio.Queue()
        self.backup_task = None
        self.backup_interval = getattr(settings, 'KB_BACKUP_INTERVAL', 300)  # 5 minutes
        
        # Configuration
        self.git_backup_enabled = getattr(settings, 'KB_GIT_BACKUP_ENABLED', True)
        self.batch_commits = getattr(settings, 'KB_BATCH_COMMITS', True)
        
        logger.info(f"KB Hybrid Storage initialized - Git backup: {self.git_backup_enabled}")
    
    async def initialize(self):
        """Initialize both storage backends"""
        try:
            # Initialize database storage
            await self.db_storage.initialize()
            
            # Start background Git backup task if enabled
            if self.git_backup_enabled:
                self.backup_task = asyncio.create_task(self._git_backup_worker())
            
            logger.info("KB Hybrid Storage initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize KB Hybrid Storage: {e}")
            raise
    
    async def shutdown(self):
        """Clean shutdown of background tasks"""
        if self.backup_task and not self.backup_task.done():
            self.backup_task.cancel()
            try:
                await self.backup_task
            except asyncio.CancelledError:
                pass
        
        # Process any remaining commits
        if not self.git_commit_queue.empty():
            await self._process_git_queue()
    
    async def save_document(
        self,
        path: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        change_message: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Save document with hybrid storage.
        
        1. Immediate save to PostgreSQL
        2. Queue Git commit for background processing
        """
        try:
            # Extract additional metadata from content if needed
            keywords = self._extract_keywords(content)
            wiki_links = self._extract_wiki_links(content)
            
            # Create document object
            document = KBDocument(
                path=path,
                content=content,
                metadata=metadata or {},
                keywords=keywords,
                wiki_links=wiki_links,
                modified_by=user_id
            )
            
            # 1. Save to PostgreSQL immediately
            db_result = await self.db_storage.save_document(
                document=document,
                user_id=user_id,
                change_message=change_message,
                expected_version=expected_version
            )
            
            if not db_result["success"]:
                return db_result
            
            # 2. Queue for Git backup (non-blocking)
            if self.git_backup_enabled:
                await self._queue_git_commit({
                    "action": "write",
                    "path": path,
                    "content": content,
                    "user_id": user_id,
                    "change_message": change_message or f"{db_result['action'].title()} document",
                    "timestamp": datetime.now().isoformat(),
                    "version": db_result["version"]
                })
            
            return {
                **db_result,
                "storage_mode": "hybrid",
                "git_queued": self.git_backup_enabled
            }
            
        except Exception as e:
            logger.error(f"Error in hybrid save for {path}: {e}")
            return {
                "success": False,
                "error": "hybrid_save_failed",
                "message": str(e)
            }
    
    async def get_document(self, path: str) -> Optional[KBDocument]:
        """Get document from PostgreSQL (primary source)"""
        return await self.db_storage.get_document(path)
    
    async def delete_document(
        self,
        path: str,
        user_id: Optional[str] = None,
        change_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete document with hybrid storage"""
        try:
            # 1. Delete from PostgreSQL
            db_result = await self.db_storage.delete_document(
                path=path,
                user_id=user_id,
                change_message=change_message
            )
            
            if not db_result["success"]:
                return db_result
            
            # 2. Queue for Git backup
            if self.git_backup_enabled:
                await self._queue_git_commit({
                    "action": "delete",
                    "path": path,
                    "user_id": user_id,
                    "change_message": change_message or "Delete document",
                    "timestamp": datetime.now().isoformat()
                })
            
            return {
                **db_result,
                "storage_mode": "hybrid",
                "git_queued": self.git_backup_enabled
            }
            
        except Exception as e:
            logger.error(f"Error in hybrid delete for {path}: {e}")
            return {
                "success": False,
                "error": "hybrid_delete_failed",
                "message": str(e)
            }
    
    async def move_document(
        self,
        old_path: str,
        new_path: str,
        user_id: Optional[str] = None,
        change_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Move document with hybrid storage"""
        try:
            # 1. Move in PostgreSQL
            db_result = await self.db_storage.move_document(
                old_path=old_path,
                new_path=new_path,
                user_id=user_id,
                change_message=change_message
            )
            
            if not db_result["success"]:
                return db_result
            
            # 2. Queue for Git backup
            if self.git_backup_enabled:
                await self._queue_git_commit({
                    "action": "move",
                    "old_path": old_path,
                    "new_path": new_path,
                    "user_id": user_id,
                    "change_message": change_message or f"Move {old_path} to {new_path}",
                    "timestamp": datetime.now().isoformat()
                })
            
            return {
                **db_result,
                "storage_mode": "hybrid",
                "git_queued": self.git_backup_enabled
            }
            
        except Exception as e:
            logger.error(f"Error in hybrid move {old_path} -> {new_path}: {e}")
            return {
                "success": False,
                "error": "hybrid_move_failed",
                "message": str(e)
            }
    
    async def search_documents(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        contexts: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Search using PostgreSQL full-text search"""
        result = await self.db_storage.search_documents(
            query=query,
            limit=limit,
            offset=offset,
            contexts=contexts,
            keywords=keywords
        )
        
        if result["success"]:
            result["storage_mode"] = "hybrid"
        
        return result
    
    async def list_documents(
        self,
        path_prefix: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List documents from PostgreSQL"""
        result = await self.db_storage.list_documents(
            path_prefix=path_prefix,
            limit=limit,
            offset=offset
        )
        
        if result["success"]:
            result["storage_mode"] = "hybrid"
        
        return result
    
    async def document_exists(self, path: str) -> bool:
        """Check document existence in PostgreSQL"""
        return await self.db_storage.document_exists(path)
    
    async def get_document_history(self, path: str, limit: int = 10):
        """Get document history from PostgreSQL"""
        return await self.db_storage.get_document_history(path, limit)
    
    async def sync_to_git(self, force: bool = False) -> Dict[str, Any]:
        """
        Manually trigger Git sync.
        
        This exports all documents from PostgreSQL to the Git repository.
        Useful for:
        - Initial setup
        - Manual backups
        - Disaster recovery preparation
        """
        try:
            logger.info("Starting manual Git sync...")
            
            # Get all documents from database
            docs_result = await self.db_storage.list_documents(limit=10000)
            if not docs_result["success"]:
                return docs_result
            
            sync_stats = {
                "exported": 0,
                "errors": 0,
                "skipped": 0
            }
            
            for doc_info in docs_result["documents"]:
                try:
                    # Get full document content
                    doc = await self.db_storage.get_document(doc_info["path"])
                    if not doc:
                        sync_stats["skipped"] += 1
                        continue
                    
                    # Write to filesystem (Git will track changes)
                    file_path = self.kb_path / doc.path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write content with frontmatter if metadata exists
                    content = doc.content
                    if doc.metadata:
                        # Add frontmatter
                        frontmatter_lines = ["---"]
                        for key, value in doc.metadata.items():
                            frontmatter_lines.append(f"{key}: {json.dumps(value) if isinstance(value, (dict, list)) else value}")
                        frontmatter_lines.extend(["---", ""])
                        content = "\n".join(frontmatter_lines) + content
                    
                    file_path.write_text(content, encoding='utf-8')
                    sync_stats["exported"] += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing {doc_info['path']}: {e}")
                    sync_stats["errors"] += 1
            
            # Create Git commit for the sync
            if sync_stats["exported"] > 0 or force:
                commit_result = await self.git_editor.commit_changes(
                    message=f"Sync from database: {sync_stats['exported']} documents",
                    author={"name": "KB Hybrid Storage", "email": "kb@gaia.dev"}
                )
                
                return {
                    "success": True,
                    "action": "sync_to_git",
                    "stats": sync_stats,
                    "commit": commit_result
                }
            else:
                return {
                    "success": True,
                    "action": "sync_to_git",
                    "stats": sync_stats,
                    "message": "No changes to commit"
                }
                
        except Exception as e:
            logger.error(f"Error in Git sync: {e}")
            return {
                "success": False,
                "error": "sync_failed",
                "message": str(e)
            }
    
    async def restore_from_git(self) -> Dict[str, Any]:
        """
        Restore database from Git repository.
        
        This imports all documents from the Git repository to PostgreSQL.
        Useful for:
        - Disaster recovery
        - Initial database population
        - Migration from Git-only to hybrid storage
        """
        try:
            logger.info("Starting restore from Git...")
            
            restore_stats = {
                "imported": 0,
                "errors": 0,
                "skipped": 0
            }
            
            # Find all markdown files in KB
            for file_path in self.kb_path.rglob("*.md"):
                if file_path.name.startswith('.') or '.git' in str(file_path):
                    continue
                
                try:
                    relative_path = str(file_path.relative_to(self.kb_path))
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Parse frontmatter if present
                    metadata = {}
                    if content.startswith('---\n'):
                        parts = content.split('---\n', 2)
                        if len(parts) >= 3:
                            # Parse YAML frontmatter
                            frontmatter_text = parts[1]
                            content = parts[2]
                            
                            for line in frontmatter_text.split('\n'):
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    metadata[key.strip()] = value.strip()
                    
                    # Create document object
                    document = KBDocument(
                        path=relative_path,
                        content=content,
                        metadata=metadata,
                        keywords=self._extract_keywords(content),
                        wiki_links=self._extract_wiki_links(content),
                        created_by="git_restore"
                    )
                    
                    # Save to database
                    result = await self.db_storage.save_document(
                        document=document,
                        user_id="git_restore",
                        change_message="Restored from Git"
                    )
                    
                    if result["success"]:
                        restore_stats["imported"] += 1
                    else:
                        restore_stats["errors"] += 1
                        logger.error(f"Failed to restore {relative_path}: {result.get('message', 'Unknown error')}")
                
                except Exception as e:
                    logger.error(f"Error restoring {file_path}: {e}")
                    restore_stats["errors"] += 1
            
            return {
                "success": True,
                "action": "restore_from_git",
                "stats": restore_stats
            }
            
        except Exception as e:
            logger.error(f"Error in Git restore: {e}")
            return {
                "success": False,
                "error": "restore_failed",
                "message": str(e)
            }
    
    async def _queue_git_commit(self, commit_data: Dict[str, Any]):
        """Queue a Git commit for background processing"""
        try:
            await self.git_commit_queue.put(commit_data)
            logger.debug(f"Queued Git commit for {commit_data.get('path', 'unknown')}")
        except Exception as e:
            logger.error(f"Error queuing Git commit: {e}")
    
    async def _git_backup_worker(self):
        """Background worker that processes Git commits"""
        logger.info("Git backup worker started")
        
        try:
            while True:
                # Wait for backup interval or process immediately if batch is disabled
                if self.batch_commits:
                    await asyncio.sleep(self.backup_interval)
                    await self._process_git_queue()
                else:
                    # Process commits one by one
                    commit_data = await self.git_commit_queue.get()
                    await self._process_single_git_commit(commit_data)
                    
        except asyncio.CancelledError:
            logger.info("Git backup worker cancelled")
        except Exception as e:
            logger.error(f"Git backup worker error: {e}")
    
    async def _process_git_queue(self):
        """Process all queued Git commits in a batch"""
        if self.git_commit_queue.empty():
            return
        
        commits_to_process = []
        
        # Collect all queued commits
        while not self.git_commit_queue.empty():
            try:
                commit_data = self.git_commit_queue.get_nowait()
                commits_to_process.append(commit_data)
            except asyncio.QueueEmpty:
                break
        
        if not commits_to_process:
            return
        
        logger.info(f"Processing {len(commits_to_process)} queued Git commits")
        
        try:
            # Group commits by type for efficient processing
            writes = [c for c in commits_to_process if c["action"] == "write"]
            deletes = [c for c in commits_to_process if c["action"] == "delete"]
            moves = [c for c in commits_to_process if c["action"] == "move"]
            
            # Process writes
            for commit in writes:
                await self._sync_document_to_git(commit["path"])
            
            # Process deletes
            for commit in deletes:
                git_path = self.kb_path / commit["path"]
                if git_path.exists():
                    git_path.unlink()
            
            # Process moves
            for commit in moves:
                old_git_path = self.kb_path / commit["old_path"]
                new_git_path = self.kb_path / commit["new_path"]
                if old_git_path.exists():
                    new_git_path.parent.mkdir(parents=True, exist_ok=True)
                    old_git_path.rename(new_git_path)
            
            # Create batch commit
            if commits_to_process:
                commit_message = f"Batch update: {len(writes)} writes, {len(deletes)} deletes, {len(moves)} moves"
                await self.git_editor.commit_changes(
                    message=commit_message,
                    author={"name": "KB Hybrid Storage", "email": "kb@gaia.dev"}
                )
                logger.info(f"Created batch Git commit: {commit_message}")
                
        except Exception as e:
            logger.error(f"Error processing Git queue: {e}")
    
    async def _process_single_git_commit(self, commit_data: Dict[str, Any]):
        """Process a single Git commit immediately"""
        try:
            action = commit_data["action"]
            
            if action == "write":
                await self._sync_document_to_git(commit_data["path"])
            elif action == "delete":
                git_path = self.kb_path / commit_data["path"]
                if git_path.exists():
                    git_path.unlink()
            elif action == "move":
                old_git_path = self.kb_path / commit_data["old_path"]
                new_git_path = self.kb_path / commit_data["new_path"]
                if old_git_path.exists():
                    new_git_path.parent.mkdir(parents=True, exist_ok=True)
                    old_git_path.rename(new_git_path)
            
            # Create individual commit
            await self.git_editor.commit_changes(
                message=commit_data["change_message"],
                author={"name": commit_data.get("user_id", "KB User"), "email": "kb@gaia.dev"}
            )
            
        except Exception as e:
            logger.error(f"Error processing single Git commit: {e}")
    
    async def _sync_document_to_git(self, path: str):
        """Sync a single document from database to Git"""
        try:
            # Get document from database
            doc = await self.db_storage.get_document(path)
            if not doc:
                logger.warning(f"Document not found in database: {path}")
                return
            
            # Write to Git filesystem
            git_path = self.kb_path / path
            git_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add frontmatter if metadata exists
            content = doc.content
            if doc.metadata:
                frontmatter_lines = ["---"]
                for key, value in doc.metadata.items():
                    frontmatter_lines.append(f"{key}: {json.dumps(value) if isinstance(value, (dict, list)) else value}")
                frontmatter_lines.extend(["---", ""])
                content = "\n".join(frontmatter_lines) + content
            
            git_path.write_text(content, encoding='utf-8')
            
        except Exception as e:
            logger.error(f"Error syncing document to Git {path}: {e}")
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract hashtag keywords from content"""
        import re
        pattern = r'#([a-zA-Z0-9_-]+)'
        return list(set(re.findall(pattern, content)))
    
    def _extract_wiki_links(self, content: str) -> List[str]:
        """Extract wiki-style links [[link]] from content"""
        import re
        pattern = r'\[\[([^\]]+)\]\]'
        return list(set(re.findall(pattern, content)))

# Global instance
kb_hybrid_storage = KBHybridStorage(kb_path=getattr(settings, 'KB_PATH', '/kb'))