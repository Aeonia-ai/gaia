"""
KB Semantic Search Endpoints

Provides FastAPI endpoint handlers for semantic search functionality.
"""

import logging
from typing import Dict, Any
from fastapi import HTTPException

from app.models.chat import ChatRequest
from app.shared.config import settings
from .kb_semantic_search import semantic_indexer

logger = logging.getLogger(__name__)


async def kb_search_semantic_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform semantic search using natural language queries.
    
    The message field contains the natural language query.
    In multi-user mode, searches are restricted to the user's namespace.
    """
    try:
        query = request.message
        logger.info(f"🔍 KB semantic search: {query[:100]}...")
        
        # Prepare search parameters
        kwargs = {
            "query": query,
            "limit": 20
        }
        
        # Handle namespace based on auth mode
        if getattr(settings, 'KB_MULTI_USER_ENABLED', False):
            # Multi-user mode: use email-based namespace
            user_email = auth_principal.get("email")
            if user_email:
                kwargs["user_id"] = user_email
                logger.info(f"Semantic search for user: {user_email}")
            else:
                logger.warning(f"Semantic search denied - no email in auth_principal")
                raise HTTPException(
                    status_code=403,
                    detail="KB semantic search requires email-based authentication"
                )
        else:
            # Single-user mode: search entire KB
            kwargs["namespace"] = "root"
        
        # Execute semantic search
        search_result = await semantic_indexer.search_semantic(**kwargs)
        
        if search_result["success"]:
            results = search_result["results"]
            total = search_result["total_results"]
            status = search_result.get("status", "ready")
            
            # Format response
            response_content = f"🧠 **Semantic Search Results for: '{query}'**\n\n"
            
            if status == "indexing":
                response_content += f"⏳ {search_result.get('message', 'Indexing in progress...')}\n\n"
            elif total == 0:
                response_content += "No results found. Try rephrasing your query or wait for indexing to complete.\n"
            else:
                response_content += f"Found {total} relevant results:\n\n"
                
                for i, result in enumerate(results[:10], 1):
                    path = result["relative_path"]
                    excerpt = result["content_excerpt"]
                    score = result.get("relevance_score", 0)
                    
                    response_content += f"**{i}. {path}** (relevance: {score:.2f})\n"
                    if excerpt:
                        response_content += f"Excerpt: {excerpt[:200]}...\n\n"
                    else:
                        response_content += "\n"
                
                if total > 10:
                    response_content += f"... and {total - 10} more results.\n"
        else:
            error_msg = search_result.get('error', 'Unknown error')
            response_content = f"❌ Semantic search failed: {error_msg}"
        
        return {
            "status": "success" if search_result["success"] else "error",
            "response": response_content,
            "metadata": {
                "search_type": "semantic",
                "total_results": search_result.get("total_results", 0),
                "query": query[:100],  # Truncate for metadata
                "indexing_status": search_result.get("status", "ready")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"KB semantic search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Semantic search error: {str(e)}")


async def kb_reindex_semantic_endpoint(
    auth_principal: Dict[str, Any],
    namespace: str = None
) -> Dict[str, Any]:
    """
    Manually trigger semantic reindexing for a namespace.
    
    Args:
        auth_principal: Authentication information
        namespace: Optional namespace to reindex (defaults to user's namespace)
        
    Returns:
        Status of the reindex operation
    """
    try:
        # Determine namespace to reindex
        if namespace:
            # Admin reindexing specific namespace (requires admin role)
            if not auth_principal.get("is_admin", False):
                raise HTTPException(
                    status_code=403,
                    detail="Admin privileges required to reindex other namespaces"
                )
            target_namespace = namespace
        elif getattr(settings, 'KB_MULTI_USER_ENABLED', False):
            # User reindexing their own namespace
            user_email = auth_principal.get("email")
            if not user_email:
                raise HTTPException(
                    status_code=403,
                    detail="Email-based authentication required for reindexing"
                )
            target_namespace = f"users/{user_email}"
        else:
            # Single-user mode: reindex entire KB
            target_namespace = "root"
        
        logger.info(f"🔄 Triggering semantic reindex for namespace: {target_namespace}")
        
        # Trigger reindexing
        result = await semantic_indexer.reindex_namespace(target_namespace)
        
        if result["success"]:
            logger.info(f"Successfully queued reindex for: {target_namespace}")
            return {
                "status": "success",
                "message": result["message"],
                "namespace": target_namespace
            }
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Failed to reindex {target_namespace}: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindex endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reindex error: {str(e)}")


async def kb_semantic_stats_endpoint(
    auth_principal: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get semantic search statistics and indexing status.
    
    Returns information about:
    - Indexing queue size
    - Indexed namespaces
    - Cache statistics
    """
    try:
        # Check if semantic search is enabled
        if not semantic_indexer.enabled:
            return {
                "status": "disabled",
                "message": "Semantic search is not enabled",
                "enabled": False
            }
        
        # Get queue size
        queue_size = semantic_indexer.indexing_queue.qsize()
        
        # Determine user's namespace for stats
        if getattr(settings, 'KB_MULTI_USER_ENABLED', False):
            user_email = auth_principal.get("email")
            if user_email:
                namespace = f"users/{user_email}"
            else:
                namespace = None
        else:
            namespace = "root"
        
        # Check if namespace is indexed
        indexed = False
        if namespace:
            namespace_path = semantic_indexer.kb_path
            if namespace != "root":
                namespace_path = namespace_path / namespace
            aifs_file = namespace_path / "_.aifs"
            indexed = aifs_file.exists()
        
        return {
            "status": "success",
            "enabled": True,
            "statistics": {
                "indexing_queue_size": queue_size,
                "namespace": namespace,
                "indexed": indexed,
                "cache_ttl_seconds": semantic_indexer.cache_ttl
            }
        }
        
    except Exception as e:
        logger.error(f"Semantic stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")