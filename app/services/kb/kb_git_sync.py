"""
KB Git Sync Manager

Handles synchronization between Git repository and KB database storage.
Supports both manual sync operations and scheduled monitoring.
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from app.shared.config import settings
from app.shared.logging import get_logger
from app.shared.redis_client import redis_client

logger = get_logger(__name__)

class KBGitSync:
    """
    Git synchronization manager for KB service.
    
    Features:
    - Manual sync from Git to database
    - Manual sync from database to Git  
    - Scheduled monitoring for external changes
    - Git status checking and reporting
    - Conflict detection and resolution
    """
    
    def __init__(self, kb_path: str, storage_manager):
        self.kb_path = Path(kb_path)
        self.storage = storage_manager
        
        # Configuration
        self.git_remote = getattr(settings, 'KB_GIT_REMOTE', 'origin')
        self.git_branch = getattr(settings, 'KB_GIT_BRANCH', 'main')
        self.auto_sync_enabled = getattr(settings, 'KB_GIT_AUTO_SYNC', True)
        self.sync_interval = getattr(settings, 'KB_SYNC_INTERVAL', 3600)  # 1 hour
        
        # Repository configuration
        self.git_repo_url = getattr(settings, 'KB_GIT_REPO_URL', None)
        self.git_auth_token = getattr(settings, 'KB_GIT_AUTH_TOKEN', None)
        self.auto_clone = getattr(settings, 'KB_GIT_AUTO_CLONE', True)
        
        # State tracking
        self.monitor_task = None
        self.last_sync_commit = None
        self.sync_in_progress = False
        
        logger.info(f"KB Git Sync initialized - Auto sync: {self.auto_sync_enabled}, Interval: {self.sync_interval}s")
    
    async def initialize(self):
        """Initialize Git sync manager"""
        try:
            # Initialize Git repository if needed
            if not await self._is_git_repo():
                if self.git_repo_url and self.auto_clone:
                    logger.info(f"Initializing Git repository from {self.git_repo_url}")
                    await self._initialize_git_repo()
                else:
                    logger.warning(f"KB path {self.kb_path} is not a Git repository and no repo URL configured")
                    return
            
            # Configure Git if needed
            await self._configure_git()
            
            # Get initial state
            self.last_sync_commit = await self._get_last_sync_commit()
            
            # Start monitoring task if enabled
            if self.auto_sync_enabled:
                self.monitor_task = asyncio.create_task(self._monitor_git_changes())
            
            logger.info("KB Git Sync initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize KB Git Sync: {e}")
            raise
    
    async def shutdown(self):
        """Clean shutdown of Git sync manager"""
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("KB Git Sync shutdown complete")
    
    async def sync_from_git(self, force: bool = False) -> Dict[str, Any]:
        """
        Sync KB content from Git repository to database.
        
        This pulls the latest changes from the Git repository and updates
        the database with any new or modified documents.
        """
        if self.sync_in_progress and not force:
            return {
                "success": False,
                "error": "sync_in_progress",
                "message": "Sync operation already in progress"
            }
        
        self.sync_in_progress = True
        start_time = datetime.now()
        
        try:
            logger.info("Starting sync from Git to database...")
            
            # 1. Fetch latest from remote
            fetch_result = await self._git_fetch()
            if not fetch_result["success"]:
                return fetch_result
            
            # 2. Check if there are new commits
            current_commit = await self._get_current_commit()
            last_sync = await self._get_last_sync_commit()
            
            if current_commit == last_sync and not force:
                return {
                    "success": True,
                    "action": "sync_from_git",
                    "message": "No new commits to sync",
                    "current_commit": current_commit,
                    "last_sync": last_sync
                }
            
            # 3. Get changed files since last sync
            changed_files = await self._get_changed_files(last_sync, current_commit)
            
            # 4. Merge or reset to latest
            merge_result = await self._merge_latest()
            if not merge_result["success"]:
                return merge_result
            
            # 5. Sync files to database using storage manager
            if hasattr(self.storage, 'restore_from_git'):
                # Use hybrid storage restore
                restore_result = await self.storage.restore_from_git()
            else:
                # Manual file-by-file sync
                restore_result = await self._manual_restore_from_git(changed_files)
            
            if not restore_result["success"]:
                return restore_result
            
            # 6. Update sync tracking
            await self._update_last_sync_commit(current_commit)
            
            # 7. Trigger semantic reindexing for changed files
            if changed_files:
                try:
                    from .kb_semantic_search import semantic_indexer
                    if semantic_indexer.enabled:
                        await semantic_indexer.reindex_changed_files(changed_files)
                        logger.info(f"Queued semantic reindexing for {len(changed_files)} changed files")
                except Exception as e:
                    logger.warning(f"Could not trigger semantic reindexing: {e}")
            
            duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                "success": True,
                "action": "sync_from_git",
                "stats": restore_result.get("stats", {}),
                "changed_files": changed_files,
                "from_commit": last_sync,
                "to_commit": current_commit,
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Sync from Git completed in {duration:.2f}s - {restore_result.get('stats', {}).get('imported', 0)} files")
            return result
            
        except Exception as e:
            logger.error(f"Error syncing from Git: {e}", exc_info=True)
            return {
                "success": False,
                "error": "sync_from_git_failed",
                "message": str(e),
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }
        finally:
            self.sync_in_progress = False
    
    async def sync_to_git(self, commit_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Sync KB content from database to Git repository.
        
        This exports database content to files and creates a Git commit.
        """
        if self.sync_in_progress:
            return {
                "success": False,
                "error": "sync_in_progress", 
                "message": "Sync operation already in progress"
            }
        
        self.sync_in_progress = True
        start_time = datetime.now()
        
        try:
            logger.info("Starting sync from database to Git...")
            
            # 1. Export database to Git using storage manager
            if hasattr(self.storage, 'sync_to_git'):
                # Use hybrid storage export
                export_result = await self.storage.sync_to_git(force=True)
            else:
                # Manual database-to-file export
                export_result = await self._manual_export_to_git()
            
            if not export_result["success"]:
                return export_result
            
            # 2. Check if there are changes to commit
            status_result = await self._git_status()
            if not status_result["has_changes"]:
                return {
                    "success": True,
                    "action": "sync_to_git",
                    "message": "No changes to commit",
                    "stats": export_result.get("stats", {})
                }
            
            # 3. Add and commit changes
            commit_msg = commit_message or f"KB sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            commit_result = await self._git_commit_all(commit_msg)
            
            if not commit_result["success"]:
                return commit_result
            
            # 4. Push to remote (optional)
            push_result = await self._git_push()
            
            # 5. Update sync tracking
            current_commit = await self._get_current_commit()
            await self._update_last_sync_commit(current_commit)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                "success": True,
                "action": "sync_to_git",
                "stats": export_result.get("stats", {}),
                "commit": commit_result.get("commit_hash"),
                "pushed": push_result.get("success", False),
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Sync to Git completed in {duration:.2f}s - {export_result.get('stats', {}).get('exported', 0)} files")
            return result
            
        except Exception as e:
            logger.error(f"Error syncing to Git: {e}", exc_info=True)
            return {
                "success": False,
                "error": "sync_to_git_failed",
                "message": str(e),
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }
        finally:
            self.sync_in_progress = False
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current synchronization status between Git and database.
        """
        try:
            # Git status
            current_commit = await self._get_current_commit()
            last_sync = await self._get_last_sync_commit()
            
            # Check for new commits on remote
            await self._git_fetch()
            remote_commit = await self._get_remote_commit()
            
            # Check for local changes
            git_status = await self._git_status()
            
            # Database stats
            db_stats = {}
            try:
                if hasattr(self.storage, 'get_storage_stats'):
                    db_stats = await self.storage.get_storage_stats()
            except Exception as e:
                logger.warning(f"Could not get database stats: {e}")
            
            return {
                "success": True,
                "git": {
                    "current_commit": current_commit,
                    "remote_commit": remote_commit,
                    "last_sync_commit": last_sync,
                    "has_local_changes": git_status["has_changes"],
                    "changed_files": git_status["changed_files"],
                    "git_ahead": current_commit != remote_commit,
                    "needs_sync_from_git": remote_commit != last_sync,
                    "needs_sync_to_git": git_status["has_changes"]
                },
                "database": db_stats,
                "sync": {
                    "auto_sync_enabled": self.auto_sync_enabled,
                    "sync_in_progress": self.sync_in_progress,
                    "last_check": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                "success": False,
                "error": "sync_status_failed",
                "message": str(e)
            }
    
    async def _monitor_git_changes(self):
        """Background task to monitor Git repository for changes"""
        logger.info("Git monitoring task started")
        
        try:
            while True:
                await asyncio.sleep(self.sync_interval)
                
                try:
                    # Check if there are new commits on remote
                    await self._git_fetch()
                    remote_commit = await self._get_remote_commit()
                    last_sync = await self._get_last_sync_commit()
                    
                    if remote_commit != last_sync:
                        logger.info(f"New commits detected: {last_sync[:8]} -> {remote_commit[:8]}")
                        
                        # Auto-sync from Git
                        result = await self.sync_from_git()
                        
                        if result["success"]:
                            logger.info(f"Auto-sync completed: {result.get('stats', {}).get('imported', 0)} files updated")
                        else:
                            logger.error(f"Auto-sync failed: {result.get('message', 'Unknown error')}")
                    
                except Exception as e:
                    logger.error(f"Error in Git monitoring cycle: {e}")
                    # Continue monitoring despite errors
                    
        except asyncio.CancelledError:
            logger.info("Git monitoring task cancelled")
        except Exception as e:
            logger.error(f"Git monitoring task failed: {e}")
    
    # Git Operations
    
    async def _is_git_repo(self) -> bool:
        """Check if KB path is a Git repository"""
        return (self.kb_path / '.git').exists()
    
    async def _initialize_git_repo(self):
        """Initialize Git repository by cloning from remote URL"""
        try:
            # Ensure parent directory exists
            self.kb_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If directory exists but is not a Git repo, remove it
            if self.kb_path.exists() and not await self._is_git_repo():
                import shutil
                shutil.rmtree(self.kb_path)
            
            # Clone the repository with authentication
            clone_url = self._prepare_authenticated_url(self.git_repo_url)
            
            logger.info(f"Cloning repository from {self.git_repo_url} to {self.kb_path}")
            
            await self._run_git_command_external(['clone', clone_url, str(self.kb_path)])
            
            # Change to the cloned directory for subsequent operations
            logger.info(f"Git repository initialized successfully at {self.kb_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Git repository: {e}")
            raise
    
    def _prepare_authenticated_url(self, repo_url: str) -> str:
        """Prepare repository URL with authentication for remote deployment"""
        if not self.git_auth_token:
            return repo_url
        
        # Handle different Git hosting platforms
        if 'github.com' in repo_url:
            # GitHub: https://token@github.com/user/repo.git
            return repo_url.replace('https://github.com/', f'https://{self.git_auth_token}@github.com/')
        elif 'gitlab.com' in repo_url:
            # GitLab: https://oauth2:token@gitlab.com/user/repo.git
            return repo_url.replace('https://gitlab.com/', f'https://oauth2:{self.git_auth_token}@gitlab.com/')
        elif 'bitbucket.org' in repo_url:
            # Bitbucket: https://x-token-auth:token@bitbucket.org/user/repo.git
            return repo_url.replace('https://bitbucket.org/', f'https://x-token-auth:{self.git_auth_token}@bitbucket.org/')
        else:
            # Generic: assume GitHub-style token auth
            if 'https://' in repo_url:
                return repo_url.replace('https://', f'https://{self.git_auth_token}@')
            else:
                logger.warning(f"Unsupported repository URL format for token auth: {repo_url}")
                return repo_url
    
    async def _configure_git(self):
        """Configure Git settings if needed"""
        try:
            # Set basic Git config for commits
            await self._run_git_command(['config', 'user.name', 'KB Service'])
            await self._run_git_command(['config', 'user.email', 'kb@gaia.dev'])
            
            # Configure remote URL with authentication if token is available
            if self.git_auth_token:
                auth_url = self._prepare_authenticated_url(self.git_repo_url)
                await self._run_git_command(['remote', 'set-url', 'origin', auth_url])
                logger.info("Git remote configured with authentication")
        except Exception as e:
            logger.warning(f"Could not configure Git: {e}")
    
    async def _git_fetch(self) -> Dict[str, Any]:
        """Fetch latest from remote repository"""
        try:
            result = await self._run_git_command(['fetch', self.git_remote, self.git_branch])
            return {"success": True, "output": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _git_status(self) -> Dict[str, Any]:
        """Get Git working directory status"""
        try:
            result = await self._run_git_command(['status', '--porcelain'])
            changed_files = [line.strip() for line in result.split('\n') if line.strip()]
            
            return {
                "success": True,
                "has_changes": len(changed_files) > 0,
                "changed_files": changed_files
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _merge_latest(self) -> Dict[str, Any]:
        """Merge latest changes from remote"""
        try:
            result = await self._run_git_command(['merge', f'{self.git_remote}/{self.git_branch}'])
            return {"success": True, "output": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _git_commit_all(self, message: str) -> Dict[str, Any]:
        """Add all changes and create commit"""
        try:
            # Add all changes
            await self._run_git_command(['add', '.'])
            
            # Commit
            result = await self._run_git_command(['commit', '-m', message])
            
            # Get commit hash
            commit_hash = await self._get_current_commit()
            
            return {
                "success": True,
                "commit_hash": commit_hash,
                "output": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _git_push(self) -> Dict[str, Any]:
        """Push commits to remote repository"""
        try:
            result = await self._run_git_command(['push', self.git_remote, self.git_branch])
            return {"success": True, "output": result}
        except Exception as e:
            # Push failures are common and not critical
            logger.warning(f"Git push failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_current_commit(self) -> str:
        """Get current HEAD commit hash"""
        try:
            result = await self._run_git_command(['rev-parse', 'HEAD'])
            return result.strip()
        except Exception:
            return "unknown"
    
    async def _get_remote_commit(self) -> str:
        """Get remote HEAD commit hash"""
        try:
            result = await self._run_git_command(['rev-parse', f'{self.git_remote}/{self.git_branch}'])
            return result.strip()
        except Exception:
            return "unknown"
    
    async def _get_changed_files(self, from_commit: str, to_commit: str) -> List[str]:
        """Get list of files changed between commits"""
        try:
            if from_commit == "unknown" or to_commit == "unknown":
                return []
            
            result = await self._run_git_command(['diff', '--name-only', from_commit, to_commit])
            return [f.strip() for f in result.split('\n') if f.strip()]
        except Exception:
            return []
    
    async def _run_git_command(self, args: List[str]) -> str:
        """Run a Git command and return output"""
        try:
            process = await asyncio.create_subprocess_exec(
                'git', *args,
                cwd=self.kb_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Git command failed: {stderr.decode()}")
            
            return stdout.decode()
            
        except Exception as e:
            logger.error(f"Git command '{' '.join(args)}' failed: {e}")
            raise
    
    async def _run_git_command_external(self, args: List[str], cwd: str = None) -> str:
        """Run a Git command with custom working directory (for clone, etc.)"""
        try:
            process = await asyncio.create_subprocess_exec(
                'git', *args,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Git command failed: {stderr.decode()}")
            
            return stdout.decode()
            
        except Exception as e:
            logger.error(f"External Git command '{' '.join(args)}' failed: {e}")
            raise
    
    # Sync State Tracking
    
    async def _get_last_sync_commit(self) -> str:
        """Get the commit hash of the last successful sync"""
        try:
            # Try Redis first
            if hasattr(redis_client, 'get'):
                cached = await redis_client.get("kb:last_sync_commit")
                if cached:
                    return cached.decode() if isinstance(cached, bytes) else cached
            
            # Fallback to current commit
            return await self._get_current_commit()
            
        except Exception:
            return "unknown"
    
    async def _update_last_sync_commit(self, commit_hash: str):
        """Update the last successful sync commit hash"""
        try:
            # Store in Redis if available
            if hasattr(redis_client, 'set'):
                await redis_client.set("kb:last_sync_commit", commit_hash, ex=86400*7)  # 1 week
            
            self.last_sync_commit = commit_hash
            
        except Exception as e:
            logger.warning(f"Could not update last sync commit: {e}")
    
    # Manual sync helpers (for non-hybrid storage)
    
    async def _manual_restore_from_git(self, changed_files: List[str]) -> Dict[str, Any]:
        """Manual file-by-file restore from Git to database"""
        stats = {"imported": 0, "errors": 0, "skipped": 0}
        
        # Get all .md files if no specific files provided
        if not changed_files:
            changed_files = [str(p.relative_to(self.kb_path)) 
                           for p in self.kb_path.rglob("*.md") 
                           if not str(p).startswith('.git')]
        
        for file_path in changed_files:
            if not file_path.endswith('.md'):
                continue
                
            try:
                full_path = self.kb_path / file_path
                if not full_path.exists():
                    stats["skipped"] += 1
                    continue
                
                content = full_path.read_text(encoding='utf-8')
                
                # Save to database through storage manager
                result = await self.storage.save_document(
                    path=file_path,
                    content=content,
                    user_id="git_sync",
                    change_message="Synced from Git"
                )
                
                if result["success"]:
                    stats["imported"] += 1
                else:
                    stats["errors"] += 1
                    
            except Exception as e:
                logger.error(f"Error importing {file_path}: {e}")
                stats["errors"] += 1
        
        return {"success": True, "stats": stats}
    
    async def _manual_export_to_git(self) -> Dict[str, Any]:
        """Manual export from database to Git files"""
        stats = {"exported": 0, "errors": 0}
        
        try:
            # Get all documents from database
            docs_result = await self.storage.list_documents(limit=10000)
            if not docs_result["success"]:
                return docs_result
            
            for doc_info in docs_result["documents"]:
                try:
                    # Get full document
                    doc = await self.storage.get_document(doc_info["path"])
                    if not doc:
                        continue
                    
                    # Write to file
                    file_path = self.kb_path / doc_info["path"]
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(doc.content, encoding='utf-8')
                    
                    stats["exported"] += 1
                    
                except Exception as e:
                    logger.error(f"Error exporting {doc_info['path']}: {e}")
                    stats["errors"] += 1
            
            return {"success": True, "stats": stats}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global Git sync manager instance (initialized in main.py)
kb_git_sync = None