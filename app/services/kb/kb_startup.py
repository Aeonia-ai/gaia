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
    Initialize KB repository on startup.
    Clones from Git if:
    1. KB directory doesn't exist
    2. KB directory exists but is empty
    3. KB directory exists but has no .git folder
    
    This ensures local Docker behaves exactly like remote deployments.
    """
    kb_path = Path(getattr(settings, 'KB_PATH', '/kb'))
    git_repo_url = getattr(settings, 'KB_GIT_REPO_URL', None)
    git_auth_token = getattr(settings, 'KB_GIT_AUTH_TOKEN', None)
    auto_clone = getattr(settings, 'KB_GIT_AUTO_CLONE', True)
    
    if not git_repo_url:
        logger.info("No KB_GIT_REPO_URL configured, skipping repository initialization")
        return False
    
    if not auto_clone:
        logger.info("KB_GIT_AUTO_CLONE is disabled, skipping repository initialization")
        return False
    
    # Check if we need to clone
    needs_clone = False
    
    if not kb_path.exists():
        logger.info(f"KB path {kb_path} does not exist, will clone repository")
        needs_clone = True
    elif not any(kb_path.iterdir()):
        logger.info(f"KB path {kb_path} is empty, will clone repository")
        needs_clone = True
    elif not (kb_path / '.git').exists():
        logger.info(f"KB path {kb_path} exists but has no .git directory, will clone repository")
        needs_clone = True
    else:
        logger.info(f"KB repository already exists at {kb_path}, skipping clone")
        return True
    
    if needs_clone:
        try:
            # Prepare the clone URL with authentication
            clone_url = _prepare_authenticated_url(git_repo_url, git_auth_token)
            
            # Ensure parent directory exists
            kb_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If directory exists but needs clone, remove it first
            if kb_path.exists():
                logger.info(f"Removing existing non-git directory at {kb_path}")
                shutil.rmtree(kb_path)
            
            logger.info(f"Cloning repository from {git_repo_url} to {kb_path}")
            
            # Clone the repository
            process = await asyncio.create_subprocess_exec(
                'git', 'clone', clone_url, str(kb_path),
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
            
            # Configure git for any future operations
            await _configure_git(kb_path)
            
            # Count files for logging
            file_count = sum(1 for _ in kb_path.rglob("*") if _.is_file())
            logger.info(f"Successfully cloned repository with {file_count} files")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            # Create empty directory so service can still start
            kb_path.mkdir(parents=True, exist_ok=True)
            return False


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