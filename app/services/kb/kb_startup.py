"""
KB Service Startup Initialization

Handles Git repository cloning on service startup to ensure
local-remote parity. In production, containers are ephemeral
so we need to clone the repository on every startup.
"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional

from app.shared.config import settings
from app.shared.logging import get_logger

logger = get_logger(__name__)


async def initialize_kb_repository():
    """
    Initialize KB repository on startup with deferred clone.
    
    Fast startup approach:
    1. Check if repository already exists - if so, we're done
    2. Create empty directory structure for immediate service startup
    3. Schedule background git clone (non-blocking)
    
    This ensures services start immediately while git clone happens in background.
    """
    kb_path = Path(getattr(settings, 'KB_PATH', '/kb'))
    git_repo_url = getattr(settings, 'KB_GIT_REPO_URL', None)
    auto_clone = getattr(settings, 'KB_GIT_AUTO_CLONE', True)
    
    # Always ensure the KB directory exists for immediate service startup
    kb_path.mkdir(parents=True, exist_ok=True)
    
    # Check if repository already exists and is complete
    if (kb_path / '.git').exists() and any(kb_path.iterdir()):
        file_count = sum(1 for _ in kb_path.rglob("*") if _.is_file())
        logger.info(f"KB repository already exists with {file_count} files, startup complete")
        return True
    
    # Repository doesn't exist or is incomplete
    if not git_repo_url:
        logger.info("No KB_GIT_REPO_URL configured, KB will start empty")
        return True  # Return True so service starts normally
    
    if not auto_clone:
        logger.info("KB_GIT_AUTO_CLONE disabled, KB will start empty")
        return True  # Return True so service starts normally
    
    # Schedule background clone (non-blocking)
    logger.info(f"Scheduling background clone from {git_repo_url}")
    task = asyncio.create_task(_background_clone())
    
    # Add error callback to see if task fails
    def log_task_exception(task):
        try:
            task.result()
        except Exception as e:
            logger.error(f"Background clone task failed: {e}")
    
    task.add_done_callback(log_task_exception)
    
    return True  # Service starts immediately


async def _background_clone():
    """
    Perform git clone in background after service startup.
    This prevents blocking service startup on large repositories.
    """
    kb_path = Path(getattr(settings, 'KB_PATH', '/kb'))
    git_repo_url = getattr(settings, 'KB_GIT_REPO_URL', None)
    git_auth_token = getattr(settings, 'KB_GIT_AUTH_TOKEN', None)
    
    try:
        logger.info("Starting background git clone...")
        
        # If directory has content but no .git, clean it first
        if kb_path.exists() and any(kb_path.iterdir()) and not (kb_path / '.git').exists():
            logger.info(f"Cleaning non-git directory at {kb_path}")
            shutil.rmtree(kb_path)
            kb_path.mkdir(parents=True, exist_ok=True)
        
        # Prepare the clone URL with authentication
        clone_url = _prepare_authenticated_url(git_repo_url, git_auth_token)
        
        logger.info(f"Cloning repository from {git_repo_url} to {kb_path}")
        
        # Clone to persistent volume using temp directory approach
        # This ensures the repository persists across container restarts
        temp_clone_path = kb_path.parent / f"{kb_path.name}_temp"
        
        # Clone to temp location first
        process = await asyncio.create_subprocess_exec(
            'git', 'clone', clone_url, str(temp_clone_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            # Remove auth token from error message for security
            if git_auth_token:
                error_msg = error_msg.replace(git_auth_token, "***")
            raise Exception(f"Git clone failed: {error_msg}")
        
        # Move contents to persistent volume (preserving .git)
        for item in temp_clone_path.iterdir():
            dest = kb_path / item.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            shutil.move(str(item), str(dest))
        
        # Remove temp directory
        temp_clone_path.rmdir()
        
        logger.info(f"Repository moved to persistent volume at {kb_path}")
        
        # Configure git for any future operations
        await _configure_git(kb_path)
        
        # Count files for logging
        file_count = sum(1 for _ in kb_path.rglob("*") if _.is_file())
        logger.info(f"✅ Background clone completed successfully with {file_count} files")
        
    except Exception as e:
        logger.error(f"❌ Background clone failed: {e}")
        # Ensure directory exists even if clone failed
        kb_path.mkdir(parents=True, exist_ok=True)


def _prepare_authenticated_url(repo_url: str, auth_token: Optional[str]) -> str:
    """Prepare repository URL with authentication token if provided"""
    if not auth_token:
        return repo_url
    
    # Handle different Git hosting platforms
    if 'github.com' in repo_url:
        # GitHub: https://token@github.com/user/repo.git
        return repo_url.replace('https://github.com/', f'https://{auth_token}@github.com/')
    elif 'gitlab.com' in repo_url:
        # GitLab: https://oauth2:token@gitlab.com/user/repo.git
        return repo_url.replace('https://gitlab.com/', f'https://oauth2:{auth_token}@gitlab.com/')
    elif 'bitbucket.org' in repo_url:
        # Bitbucket: https://x-token-auth:token@bitbucket.org/user/repo.git
        return repo_url.replace('https://bitbucket.org/', f'https://x-token-auth:{auth_token}@bitbucket.org/')
    else:
        # Generic: assume GitHub-style token auth
        if 'https://' in repo_url:
            return repo_url.replace('https://', f'https://{auth_token}@')
        else:
            logger.warning(f"Unsupported repository URL format for token auth: {repo_url}")
            return repo_url


async def _configure_git(kb_path: Path):
    """Configure Git settings for the repository"""
    try:
        # Set basic Git config for any future commits
        await _run_git_command(['config', 'user.name', 'KB Service'], cwd=kb_path)
        await _run_git_command(['config', 'user.email', 'kb@gaia.dev'], cwd=kb_path)
        
        # If we have auth token, update the remote URL to include it
        git_auth_token = getattr(settings, 'KB_GIT_AUTH_TOKEN', None)
        git_repo_url = getattr(settings, 'KB_GIT_REPO_URL', None)
        
        if git_auth_token and git_repo_url:
            auth_url = _prepare_authenticated_url(git_repo_url, git_auth_token)
            await _run_git_command(['remote', 'set-url', 'origin', auth_url], cwd=kb_path)
            logger.info("Git remote configured with authentication")
            
    except Exception as e:
        logger.warning(f"Could not configure Git: {e}")


async def _run_git_command(args: list, cwd: Path) -> str:
    """Run a Git command and return output"""
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