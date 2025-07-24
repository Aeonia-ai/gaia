"""
KB Editor Module

Provides safe editing capabilities for KB content with Git integration.
"""

import os
import logging
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import frontmatter
import aiofiles

from app.shared.config import settings
from app.models.chat import ChatRequest
from .kb_cache import kb_cache

logger = logging.getLogger(__name__)

class KBEditor:
    """
    KB content editor with Git integration.
    
    Features:
    - Safe file writing with validation
    - Git commit integration
    - Automatic cache invalidation
    - Audit logging
    """
    
    def __init__(self, kb_path: str = "/kb"):
        self.kb_path = Path(kb_path)
        self.allowed_extensions = {'.md', '.txt', '.yml', '.yaml', '.json'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        
    def _validate_path(self, path: str) -> Path:
        """Validate path is safe and within KB"""
        # Remove any leading slashes
        path = path.lstrip('/')
        
        # Check for directory traversal
        if '..' in path:
            raise ValueError("Directory traversal not allowed")
        
        # Check for hidden files
        parts = path.split('/')
        if any(part.startswith('.') for part in parts):
            raise ValueError("Hidden files not allowed")
        
        # Construct full path
        full_path = self.kb_path / path
        
        # Ensure it's within KB root
        try:
            full_path.resolve().relative_to(self.kb_path.resolve())
        except ValueError:
            raise ValueError("Path must be within KB root")
        
        return full_path
    
    def _validate_content(self, content: str, path: str) -> Dict[str, Any]:
        """Validate content before writing"""
        errors = []
        warnings = []
        
        # Check size
        if len(content.encode('utf-8')) > self.max_file_size:
            errors.append(f"File too large (max {self.max_file_size} bytes)")
        
        # Check extension
        ext = Path(path).suffix.lower()
        if ext not in self.allowed_extensions:
            errors.append(f"File type {ext} not allowed")
        
        # For markdown files, validate frontmatter
        if ext == '.md':
            try:
                post = frontmatter.loads(content)
                # Check for required fields
                if 'title' not in post.metadata:
                    warnings.append("Missing 'title' in frontmatter")
                if 'tags' not in post.metadata:
                    warnings.append("Missing 'tags' in frontmatter")
            except Exception as e:
                warnings.append(f"Invalid frontmatter: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def _run_git_command(self, cmd: List[str], cwd: str = None) -> Dict[str, Any]:
        """Run a git command and return result"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd or self.kb_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode('utf-8').strip(),
                "stderr": stderr.decode('utf-8').strip(),
                "returncode": process.returncode
            }
        except Exception as e:
            logger.error(f"Git command failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def write_file(
        self,
        path: str,
        content: str,
        message: str,
        author: Optional[Dict[str, str]] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Write or update a file in the KB.
        
        Args:
            path: Relative path within KB
            content: File content
            message: Git commit message
            author: Dict with 'name' and 'email'
            validate: Whether to validate content
        
        Returns:
            Dict with success status and commit info
        """
        try:
            # Validate path
            full_path = self._validate_path(path)
            
            # Validate content if requested
            if validate:
                validation = self._validate_content(content, path)
                if not validation["valid"]:
                    return {
                        "success": False,
                        "errors": validation["errors"],
                        "warnings": validation["warnings"]
                    }
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file exists for proper commit message
            is_new = not full_path.exists()
            action = "Create" if is_new else "Update"
            
            # Write file
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            logger.info(f"{action} file: {path}")
            
            # Git add
            git_add = await self._run_git_command(['git', 'add', str(full_path)])
            if not git_add["success"]:
                return {
                    "success": False,
                    "error": f"Git add failed: {git_add.get('stderr', 'Unknown error')}"
                }
            
            # Prepare commit
            commit_args = ['git', 'commit', '-m', f"{action} {path}: {message}"]
            
            # Add author if provided
            if author:
                commit_args.extend([
                    '--author',
                    f"{author['name']} <{author['email']}>"
                ])
            
            # Git commit
            git_commit = await self._run_git_command(commit_args)
            if not git_commit["success"]:
                # Check if there were no changes
                if "nothing to commit" in git_commit.get("stdout", ""):
                    return {
                        "success": True,
                        "message": "No changes to commit",
                        "path": path
                    }
                return {
                    "success": False,
                    "error": f"Git commit failed: {git_commit.get('stderr', 'Unknown error')}"
                }
            
            # Extract commit hash
            commit_hash = None
            for line in git_commit["stdout"].split('\n'):
                if line.strip().startswith('['):
                    # Format: [branch hash] message
                    parts = line.split()
                    if len(parts) >= 2:
                        commit_hash = parts[1].rstrip(']')
                        break
            
            # Invalidate cache for this file
            await kb_cache.invalidate_pattern(f"*{path}*")
            
            return {
                "success": True,
                "action": action.lower(),
                "path": path,
                "commit_hash": commit_hash,
                "message": message,
                "warnings": validation.get("warnings", []) if validate else []
            }
            
        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_file(
        self,
        path: str,
        message: str,
        author: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Delete a file from the KB"""
        try:
            # Validate path
            full_path = self._validate_path(path)
            
            # Check file exists
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }
            
            # Git rm
            git_rm = await self._run_git_command(['git', 'rm', str(full_path)])
            if not git_rm["success"]:
                return {
                    "success": False,
                    "error": f"Git rm failed: {git_rm.get('stderr', 'Unknown error')}"
                }
            
            # Prepare commit
            commit_args = ['git', 'commit', '-m', f"Delete {path}: {message}"]
            
            # Add author if provided
            if author:
                commit_args.extend([
                    '--author',
                    f"{author['name']} <{author['email']}>"
                ])
            
            # Git commit
            git_commit = await self._run_git_command(commit_args)
            if not git_commit["success"]:
                return {
                    "success": False,
                    "error": f"Git commit failed: {git_commit.get('stderr', 'Unknown error')}"
                }
            
            # Invalidate cache
            await kb_cache.invalidate_pattern(f"*{path}*")
            
            return {
                "success": True,
                "action": "delete",
                "path": path,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def move_file(
        self,
        old_path: str,
        new_path: str,
        message: str,
        author: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Move/rename a file in the KB"""
        try:
            # Validate paths
            old_full_path = self._validate_path(old_path)
            new_full_path = self._validate_path(new_path)
            
            # Check source exists
            if not old_full_path.exists():
                return {
                    "success": False,
                    "error": f"Source file not found: {old_path}"
                }
            
            # Check destination doesn't exist
            if new_full_path.exists():
                return {
                    "success": False,
                    "error": f"Destination already exists: {new_path}"
                }
            
            # Create parent directories for destination
            new_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Git mv
            git_mv = await self._run_git_command([
                'git', 'mv', str(old_full_path), str(new_full_path)
            ])
            if not git_mv["success"]:
                return {
                    "success": False,
                    "error": f"Git mv failed: {git_mv.get('stderr', 'Unknown error')}"
                }
            
            # Prepare commit
            commit_args = ['git', 'commit', '-m', f"Move {old_path} to {new_path}: {message}"]
            
            # Add author if provided
            if author:
                commit_args.extend([
                    '--author',
                    f"{author['name']} <{author['email']}>"
                ])
            
            # Git commit
            git_commit = await self._run_git_command(commit_args)
            if not git_commit["success"]:
                return {
                    "success": False,
                    "error": f"Git commit failed: {git_commit.get('stderr', 'Unknown error')}"
                }
            
            # Invalidate cache for both paths
            await kb_cache.invalidate_pattern(f"*{old_path}*")
            await kb_cache.invalidate_pattern(f"*{new_path}*")
            
            return {
                "success": True,
                "action": "move",
                "old_path": old_path,
                "new_path": new_path,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Failed to move file {old_path} to {new_path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_git_status(self) -> Dict[str, Any]:
        """Get current git status of KB"""
        try:
            status = await self._run_git_command(['git', 'status', '--porcelain'])
            
            if not status["success"]:
                return {
                    "success": False,
                    "error": status.get("stderr", "Unknown error")
                }
            
            # Parse status output
            changes = {
                "modified": [],
                "added": [],
                "deleted": [],
                "untracked": []
            }
            
            for line in status["stdout"].split('\n'):
                if not line.strip():
                    continue
                
                status_code = line[:2]
                file_path = line[3:]
                
                if status_code == ' M' or status_code == 'M ':
                    changes["modified"].append(file_path)
                elif status_code == ' A' or status_code == 'A ':
                    changes["added"].append(file_path)
                elif status_code == ' D' or status_code == 'D ':
                    changes["deleted"].append(file_path)
                elif status_code == '??':
                    changes["untracked"].append(file_path)
            
            return {
                "success": True,
                "changes": changes,
                "has_changes": any(len(v) > 0 for v in changes.values())
            }
            
        except Exception as e:
            logger.error(f"Failed to get git status: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

# Global editor instance
kb_editor = KBEditor()