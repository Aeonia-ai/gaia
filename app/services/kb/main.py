"""
KB Service - Knowledge Base Integration Service

Provides MCP tools for Knowledge Base access:
- Direct file system search and reading
- Context loading and management
- Cross-domain synthesis
- Multi-agent task delegation
"""

from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
import logging

from app.shared import (
    settings,
    configure_logging_for_service,
    log_service_startup,
    log_service_shutdown,
    get_current_auth_legacy as get_current_auth,
    ensure_nats_connection,
    NATSSubjects,
    ServiceHealthEvent
)
from app.shared.service_discovery import create_service_health_endpoint
from datetime import datetime
from app.shared.config import settings as config_settings
from app.shared.redis_client import redis_client
from app.models.chat import ChatRequest
from .kb_service import (
    kb_search_endpoint,
    kb_context_loader_endpoint,
    kb_multi_task_endpoint,
    kb_navigate_index_endpoint,
    kb_synthesize_contexts_endpoint,
    kb_get_threads_endpoint,
    kb_read_file_endpoint,
    kb_list_directory_endpoint,
    claude_code_execute_endpoint
)
from .kb_editor import kb_editor
from .agent_endpoints import router as agent_router
from .waypoints_api import router as waypoints_router
from .kb_agent import kb_agent
from app.models.kb import WriteRequest, DeleteRequest, MoveRequest
from .kb_semantic_search import semantic_indexer
from .kb_semantic_endpoints import (
    kb_search_semantic_endpoint,
    kb_reindex_semantic_endpoint,
    kb_semantic_stats_endpoint
)

# Configure logging
logger = configure_logging_for_service("kb")

# Import RBAC-enabled storage if multi-user is enabled
if getattr(settings, 'KB_MULTI_USER_ENABLED', False):
    from .kb_storage_with_rbac import kb_storage_rbac as kb_storage
    from .kb_storage_with_rbac import router as kb_rbac_router
    logger.info("Multi-user KB mode enabled with RBAC")
else:
    from .kb_storage_manager import kb_storage
    kb_rbac_router = None
    logger.info("Single-user KB mode enabled")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    log_service_startup("kb", "1.0", settings.SERVICE_PORT)
    
    # Initialize NATS connection for service coordination
    try:
        nats_client = await ensure_nats_connection()
        logger.info("Connected to NATS for service coordination")
        
        # Publish service startup event
        startup_event = ServiceHealthEvent(
            service_name="kb",
            status="starting",
            timestamp=datetime.now()
        )
        await nats_client.publish(NATSSubjects.SERVICE_HEALTH, startup_event.model_dump_json())
    except Exception as e:
        logger.warning(f"Could not connect to NATS: {e}")
    
    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Connected to Redis for caching")
    except Exception as e:
        logger.warning(f"Redis not available, caching disabled: {e}")
    
    # Initialize KB repository (clone from Git if needed)
    try:
        from .kb_startup import initialize_kb_repository
        await initialize_kb_repository()
    except Exception as e:
        logger.error(f"Failed to initialize KB repository: {e}")
    
    # Initialize Git sync manager
    try:
        storage_mode = getattr(config_settings, 'KB_STORAGE_MODE', 'git')
        if storage_mode == 'hybrid':
            logger.info("Git sync manager initialization deferred - hybrid mode setup needed")
        else:
            logger.info(f"Git sync not applicable for storage mode: {storage_mode}")
        
    except Exception as e:
        logger.warning(f"Git sync manager not available: {e}")

    # Initialize KB Intelligent Agent
    try:
        await kb_agent.initialize(kb_storage)
        logger.info("KB Intelligent Agent initialized and ready")
    except Exception as e:
        logger.error(f"Failed to initialize KB Agent: {e}")
    
    # Initialize Semantic Search Indexer (deferred, non-blocking)
    try:
        await semantic_indexer.initialize_indexes()
        logger.info("Semantic search indexer started (background indexing)")
    except Exception as e:
        logger.warning(f"Semantic search initialization failed: {e}")

    yield
    
    # Shutdown
    log_service_shutdown("kb")
    
    # Shutdown Semantic Indexer
    try:
        await semantic_indexer.shutdown()
        logger.info("Semantic search indexer shutdown")
    except Exception as e:
        logger.warning(f"Error shutting down semantic indexer: {e}")
    
    # Shutdown Git sync manager
    try:
        from .kb_git_sync import kb_git_sync
        if kb_git_sync:
            await kb_git_sync.shutdown()
            logger.info("KB Git sync manager shutdown")
    except Exception as e:
        logger.warning(f"Error shutting down Git sync manager: {e}")
    
    # Publish shutdown event
    try:
        nats_client = await ensure_nats_connection()
        shutdown_event = ServiceHealthEvent(
            service_name="kb",
            status="stopping",
            timestamp=datetime.now()
        )
        await nats_client.publish(NATSSubjects.SERVICE_HEALTH, shutdown_event.model_dump_json())
        await nats_client.disconnect()
    except Exception as e:
        logger.warning(f"Could not publish shutdown event: {e}")

# Create FastAPI app
app = FastAPI(
    title="KB Service",
    description="Knowledge Base integration service for Gaia Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Create enhanced health endpoint with route discovery
create_service_health_endpoint(app, "kb", "1.0.0")

@app.post("/trigger-clone")
async def trigger_clone():
    """Manually trigger git clone (public endpoint for testing)"""
    import subprocess
    from pathlib import Path
    
    kb_path = Path(getattr(config_settings, 'KB_PATH', '/kb'))
    git_url = getattr(config_settings, 'KB_GIT_REPO_URL', None)
    git_token = getattr(config_settings, 'KB_GIT_AUTH_TOKEN', None)
    
    if not git_url:
        return {"error": "KB_GIT_REPO_URL not configured", "has_url": False}
    
    # Check if already cloned
    if (kb_path / '.git').exists():
        file_count = sum(1 for _ in kb_path.rglob("*") if _.is_file())
        return {
            "status": "already_cloned",
            "message": f"Repository already exists with {file_count} files",
            "file_count": file_count
        }
    
    # Simple clone
    try:
        # Prepare authenticated URL
        if git_token and 'github.com' in git_url:
            clone_url = git_url.replace('https://github.com/', f'https://{git_token}@github.com/')
        else:
            clone_url = git_url
        
        # Check if directory is empty
        if any(kb_path.iterdir()):
            return {"error": "Directory not empty, cannot clone"}
        
        # Clone directly into the directory
        cmd = ['git', 'clone', clone_url, '.']
        result = subprocess.run(
            cmd,
            cwd=str(kb_path),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            error_msg = result.stderr
            if git_token:
                error_msg = error_msg.replace(git_token, "***")
            return {
                "error": "Clone failed",
                "details": error_msg,
                "command": ' '.join(cmd[:-1] + ['***'])  # Hide URL
            }
        
        # Count files
        file_count = sum(1 for _ in kb_path.rglob("*") if _.is_file())
        
        return {
            "status": "success",
            "message": f"Clone completed with {file_count} files",
            "file_count": file_count,
            "kb_path": str(kb_path)
        }
        
    except subprocess.TimeoutExpired:
        return {"error": "Clone timed out after 5 minutes"}
    except Exception as e:
        logger.error(f"Clone failed: {e}")
        return {"error": str(e), "type": type(e).__name__}

# KB Endpoints
@app.post("/search")
async def kb_search(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Search KB using ripgrep for fast full-text search.
    
    The message field contains the search query.
    """
    return await kb_search_endpoint(request, auth)

@app.post("/context")
async def kb_load_context(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Load a KOS context by name.
    
    The message field contains the context name (e.g., 'gaia', 'mmoirl').
    """
    return await kb_context_loader_endpoint(request, auth)

@app.post("/multitask")
async def kb_multitask(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Execute multiple KB tasks in parallel.
    
    The message field contains task descriptions.
    """
    return await kb_multi_task_endpoint(request, auth)

@app.post("/navigate")
async def kb_navigate_index(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Navigate KB using the manual index system.
    
    The message field contains the starting path (default: '/').
    """
    return await kb_navigate_index_endpoint(request, auth)

@app.post("/synthesize")
async def kb_synthesize(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Synthesize insights across multiple contexts.
    
    The message field contains comma-separated context names.
    """
    return await kb_synthesize_contexts_endpoint(request, auth)

@app.post("/threads")
async def kb_get_threads(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Get active KOS threads.
    
    The message field can contain filter criteria.
    """
    return await kb_get_threads_endpoint(request, auth)

@app.post("/read")
async def kb_read_file(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Read a specific KB file.
    
    The message field contains the file path.
    """
    return await kb_read_file_endpoint(request, auth)

@app.post("/list")
async def kb_list_directory(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    List files in a KB directory.

    The message field contains the directory path.
    """
    return await kb_list_directory_endpoint(request, auth)

@app.post("/search/semantic")
async def kb_search_semantic(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Semantic search using natural language queries.
    
    Uses AI embeddings to find conceptually similar content,
    not just keyword matches.
    
    The message field contains the natural language query.
    Example: "how do users log in?" finds authentication docs.
    """
    return await kb_search_semantic_endpoint(request, auth)

@app.post("/search/semantic/reindex")
async def kb_reindex_semantic(
    namespace: str = None,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Manually trigger semantic reindexing for a namespace.
    
    Use this after adding many new files or if search results
    seem outdated. Reindexing happens automatically but this
    forces immediate reindexing.
    
    Args:
        namespace: Optional namespace to reindex (admin only)
                  Regular users can only reindex their own namespace
    """
    return await kb_reindex_semantic_endpoint(auth, namespace)

@app.get("/search/semantic/stats")
async def kb_semantic_stats(
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Get semantic search statistics and indexing status.
    
    Shows whether your namespace is indexed, queue status,
    and other diagnostic information.
    """
    return await kb_semantic_stats_endpoint(auth)


@app.get("/search/semantic/progress/{namespace}")
async def kb_indexing_progress(
    namespace: str,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Get detailed indexing progress for a namespace.
    
    Returns real-time progress information including:
    - Current status (not_indexed, indexing, ready)
    - Number of files being indexed
    - Time elapsed
    - Estimated time per file
    - Index size once completed
    
    Example: GET /search/semantic/progress/root
    """
    from .kb_semantic_search import semantic_indexer
    return await semantic_indexer.get_indexing_status(namespace)


@app.post("/claude-code")
async def claude_code_execute(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Execute Claude Code commands via subprocess and return results.

    The message field contains the Claude Code command to execute.
    Example commands:
    - "search for authentication patterns"
    - "read app/models/user.py"
    - "help"
    - "analyze codebase structure"
    """
    return await claude_code_execute_endpoint(request, auth)

# Cache management endpoints
@app.get("/cache/stats")
async def get_cache_stats(auth: dict = Depends(get_current_auth)) -> dict:
    """Get KB cache statistics"""
    from .kb_mcp_server import kb_server
    stats = await kb_server.cache.get_stats()
    return {
        "status": "success",
        "cache": stats
    }

@app.post("/cache/invalidate")
async def invalidate_cache(
    pattern: str = "*",
    auth: dict = Depends(get_current_auth)
) -> dict:
    """Invalidate cache entries matching pattern"""
    from .kb_mcp_server import kb_server
    await kb_server.cache.invalidate_pattern(pattern)
    return {
        "status": "success",
        "message": f"Cache invalidated for pattern: {pattern}"
    }

# KB Write/Edit Endpoints
@app.post("/write")
async def kb_write_file(
    request: WriteRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Write or update a file in the KB.
    
    Requires write permissions. Creates a Git commit with the changes.
    """
    try:
        # Extract author info from auth if available
        author = None
        if auth.get("email"):
            author = {
                "name": auth.get("name", auth.get("email").split("@")[0]),
                "email": auth["email"]
            }
        
        result = await kb_editor.write_file(
            path=request.path,
            content=request.content,
            message=request.message,
            author=author,
            validate=request.validate_content
        )
        
        if result["success"]:
            logger.info(f"KB file written: {request.path} by {auth.get('email', 'unknown')}")
        else:
            logger.error(f"KB write failed: {request.path} - {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"KB write endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete")
async def kb_delete_file(
    request: DeleteRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Delete a file from the KB.
    
    Requires write permissions. Creates a Git commit for the deletion.
    """
    try:
        # Extract author info from auth if available
        author = None
        if auth.get("email"):
            author = {
                "name": auth.get("name", auth.get("email").split("@")[0]),
                "email": auth["email"]
            }
        
        result = await kb_editor.delete_file(
            path=request.path,
            message=request.message,
            author=author
        )
        
        if result["success"]:
            logger.info(f"KB file deleted: {request.path} by {auth.get('email', 'unknown')}")
        else:
            logger.error(f"KB delete failed: {request.path} - {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"KB delete endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/move")
async def kb_move_file(
    request: MoveRequest,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Move or rename a file in the KB.
    
    Requires write permissions. Creates a Git commit for the move operation.
    """
    try:
        # Extract author info from auth if available
        author = None
        if auth.get("email"):
            author = {
                "name": auth.get("name", auth.get("email").split("@")[0]),
                "email": auth["email"]
            }
        
        result = await kb_editor.move_file(
            old_path=request.old_path,
            new_path=request.new_path,
            message=request.message,
            author=author
        )
        
        if result["success"]:
            logger.info(f"KB file moved: {request.old_path} -> {request.new_path} by {auth.get('email', 'unknown')}")
        else:
            logger.error(f"KB move failed: {request.old_path} - {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"KB move endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/git/status")
async def kb_git_status(auth: dict = Depends(get_current_auth)) -> dict:
    """
    Get the current Git status of the KB repository.
    
    Shows modified, added, deleted, and untracked files.
    """
    try:
        result = await kb_editor.get_git_status()
        
        if not result["success"]:
            logger.error(f"KB git status failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"KB git status endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Git Sync Endpoints
@app.post("/sync/from-git")
async def sync_from_git(
    force: bool = False,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Sync KB content from Git repository to database.
    
    Pulls latest changes from Git and updates the database.
    Use force=true to sync even if no new commits detected.
    """
    try:
        from .kb_git_sync import kb_git_sync
        
        if not kb_git_sync:
            raise HTTPException(status_code=503, detail="Git sync not available")
        
        result = await kb_git_sync.sync_from_git(force=force)
        
        if result["success"]:
            logger.info(f"Git sync from Git completed by {auth.get('email', 'unknown')}: {result.get('stats', {})}")
        else:
            logger.error(f"Git sync from Git failed: {result.get('message', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Sync from Git endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync/to-git")
async def sync_to_git(
    commit_message: str = None,
    auth: dict = Depends(get_current_auth)
) -> dict:
    """
    Sync KB content from database to Git repository.
    
    Exports database content to files and creates a Git commit.
    """
    try:
        from .kb_git_sync import kb_git_sync
        
        if not kb_git_sync:
            raise HTTPException(status_code=503, detail="Git sync not available")
        
        result = await kb_git_sync.sync_to_git(commit_message=commit_message)
        
        if result["success"]:
            logger.info(f"Git sync to Git completed by {auth.get('email', 'unknown')}: {result.get('stats', {})}")
        else:
            logger.error(f"Git sync to Git failed: {result.get('message', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Sync to Git endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sync/status")
async def get_sync_status(auth: dict = Depends(get_current_auth)) -> dict:
    """
    Get current synchronization status between Git and database.
    
    Returns information about:
    - Current Git commit vs last sync
    - Remote changes available
    - Local changes pending
    - Database statistics
    """
    try:
        from .kb_git_sync import kb_git_sync
        
        if not kb_git_sync:
            return {
                "success": False,
                "error": "git_sync_not_available",
                "message": "Git sync functionality not enabled"
            }
        
        result = await kb_git_sync.get_sync_status()
        return result
        
    except Exception as e:
        logger.error(f"Get sync status endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Add v0.2 API compatibility router if needed
from .v0_2_api import router as v0_2_router
app.include_router(v0_2_router, prefix="/api/v0.2")
logger.info("✅ v0.2 API router included for KB service")

# Add RBAC router if multi-user is enabled
if kb_rbac_router:
    app.include_router(kb_rbac_router, prefix="/api/v1")
    logger.info("✅ RBAC endpoints added for multi-user KB")

# Add KB Agent router
app.include_router(agent_router)
app.include_router(waypoints_router)
logger.info("✅ KB Agent endpoints added")

from datetime import datetime

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.services.kb.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )