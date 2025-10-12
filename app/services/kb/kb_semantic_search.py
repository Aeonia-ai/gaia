"""
KB Semantic Search Implementation

Provides natural language semantic search capabilities for the GAIA Knowledge Base
using the aifs library for local vector search.

Key features:
- Namespace-aware indexing (respects user/team/workspace boundaries)
- Automatic incremental indexing on file changes
- Redis caching for search results
- Deferred initialization for fast startup
"""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

try:
    from aifs import search as aifs_search
    AIFS_AVAILABLE = True
    logging.info("aifs library imported successfully")
except ImportError as e:
    AIFS_AVAILABLE = False
    logging.warning(f"aifs library not available - semantic search disabled. Error: {e}")

from app.shared.config import settings
from app.shared.redis_client import redis_client
from app.shared.logging import get_logger
from .kb_chromadb_manager import chromadb_manager

logger = get_logger(__name__)


class SemanticIndexer:
    """
    Manages semantic search indexing and querying for KB namespaces.
    
    Each namespace gets its own _.aifs index file for isolation.
    Indexes are stored in the namespace directory and Git-ignored.
    """
    
    def __init__(self):
        self.kb_path = Path(getattr(settings, 'KB_PATH', '/kb'))
        self.indexing_queue = asyncio.Queue()
        self.indexing_task = None
        self.cache_ttl = getattr(settings, 'KB_SEMANTIC_CACHE_TTL', 3600)  # Default 1 hour
        
        # Check configuration
        config_enabled = getattr(settings, 'KB_SEMANTIC_SEARCH_ENABLED', False)
        logger.info(f"KB_SEMANTIC_SEARCH_ENABLED from settings: {config_enabled}")
        logger.info(f"AIFS_AVAILABLE: {AIFS_AVAILABLE}")
        
        self.enabled = AIFS_AVAILABLE and config_enabled
        
        if not self.enabled:
            if not AIFS_AVAILABLE:
                logger.info("Semantic search disabled - aifs not available")
            elif not config_enabled:
                logger.info("Semantic search disabled - not enabled in config")
        else:
            logger.info("Semantic search ENABLED successfully!")
    
    async def initialize_indexes(self):
        """
        Initialize semantic indexes in the background (deferred initialization).
        This runs asynchronously to avoid blocking service startup.
        """
        if not self.enabled:
            return
            
        try:
            logger.info("Starting background semantic index initialization...")
            
            # Start the indexing worker
            self.indexing_task = asyncio.create_task(self._indexing_worker())
            
            # Queue initial indexing for active namespaces
            await self._queue_active_namespaces()
            
            logger.info("Semantic indexing background worker started")
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic indexes: {e}", exc_info=True)
    
    async def _queue_active_namespaces(self):
        """Queue indexing for recently active namespaces."""
        try:
            # Check for user namespaces (multi-user mode)
            users_path = self.kb_path / "users"
            if users_path.exists():
                for user_dir in users_path.iterdir():
                    if user_dir.is_dir():
                        # Check if namespace was active in last 7 days
                        if self._is_recently_active(user_dir):
                            await self.indexing_queue.put({
                                "action": "index",
                                "namespace": f"users/{user_dir.name}",
                                "path": user_dir
                            })
            
            # Check for team namespaces
            teams_path = self.kb_path / "teams"
            if teams_path.exists():
                for team_dir in teams_path.iterdir():
                    if team_dir.is_dir() and self._is_recently_active(team_dir):
                        await self.indexing_queue.put({
                            "action": "index",
                            "namespace": f"teams/{team_dir.name}",
                            "path": team_dir
                        })
            
            # Index root namespace if in single-user mode
            if not getattr(settings, 'KB_MULTI_USER_ENABLED', False):
                await self.indexing_queue.put({
                    "action": "index",
                    "namespace": "root",
                    "path": self.kb_path
                })
                
        except Exception as e:
            logger.error(f"Error queuing namespaces for indexing: {e}", exc_info=True)
    
    def _is_recently_active(self, path: Path, days: int = 7) -> bool:
        """Check if a directory has been modified recently."""
        try:
            # Check modification time of any file in the directory
            for file_path in path.rglob("*.md"):
                if file_path.stat().st_mtime > (datetime.now() - timedelta(days=days)).timestamp():
                    return True
            return False
        except Exception:
            return False
    
    async def _indexing_worker(self):
        """Background worker that processes indexing tasks."""
        while True:
            try:
                task = await self.indexing_queue.get()
                
                if task["action"] == "index":
                    await self._index_namespace(task["namespace"], task["path"])
                elif task["action"] == "reindex_files":
                    await self._reindex_changed_files(task["namespace"], task["files"])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Indexing worker error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Back off on errors
    
    async def _index_namespace(self, namespace: str, path: Path):
        """Index or reindex a complete namespace."""
        try:
            logger.info(f"Indexing namespace: {namespace}")
            
            # Simple approach - files are on disk from Git, just use them
            if not path.exists():
                logger.warning(f"Namespace path does not exist: {path}")
                path.mkdir(parents=True, exist_ok=True)
            
            # Run aifs indexing in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_aifs_index, path)
            
            logger.info(f"Successfully indexed namespace: {namespace}")
            
        except Exception as e:
            logger.error(f"Failed to index namespace {namespace}: {e}", exc_info=True)
    
    def _run_aifs_index(self, path: Path):
        """Run aifs indexing (blocking operation)."""
        if not AIFS_AVAILABLE:
            logger.warning("aifs not available, skipping indexing")
            return
            
        logger.info(f"Starting aifs indexing for path: {path}")
        
        # Track indexing progress
        import time
        start_time = time.time()
        
        # Count files to index
        md_files = list(path.rglob("*.md"))
        total_files = len(md_files)
        logger.info(f"Found {total_files} markdown files to index in {path}")
        
        # Store progress in a shared location (could be Redis in production)
        self.indexing_progress = {
            "namespace": path.name,
            "total_files": total_files,
            "start_time": start_time,
            "status": "indexing"
        }
        
        # This will create/update the _.aifs file in the directory
        # Just run a dummy search to trigger indexing
        try:
            result = aifs_search("", path=str(path))
            
            elapsed = time.time() - start_time
            logger.info(f"aifs indexing completed for {path} in {elapsed:.1f} seconds")
            logger.info(f"Indexed {total_files} files, result type: {type(result)}")
            
            # Update progress
            self.indexing_progress["status"] = "completed"
            self.indexing_progress["elapsed_time"] = elapsed
            self.indexing_progress["completed_time"] = time.time()
            
        except Exception as e:
            logger.error(f"aifs indexing failed: {e}", exc_info=True)
            self.indexing_progress["status"] = "failed"
            self.indexing_progress["error"] = str(e)
    
    async def _index_to_chromadb(self, path: Path, collection):
        """Index documents directly into ChromaDB."""
        try:
            logger.info(f"Indexing {path} directly into ChromaDB")
            
            # Find all markdown files
            md_files = list(path.rglob("*.md"))
            logger.info(f"Found {len(md_files)} markdown files to index")
            
            # Process files in batches
            batch_size = 10
            for i in range(0, len(md_files), batch_size):
                batch = md_files[i:i+batch_size]
                documents = []
                metadatas = []
                ids = []
                
                for file_path in batch:
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        rel_path = str(file_path.relative_to(path))
                        
                        # Split content into chunks (simple approach)
                        chunks = [content[j:j+1000] for j in range(0, len(content), 800)]
                        
                        for chunk_idx, chunk in enumerate(chunks):
                            documents.append(chunk)
                            metadatas.append({"file": rel_path, "chunk": chunk_idx})
                            ids.append(f"{rel_path}_{chunk_idx}")
                    except Exception as e:
                        logger.warning(f"Failed to read {file_path}: {e}")
                
                if documents:
                    # Add to ChromaDB collection
                    collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    logger.info(f"Indexed batch {i//batch_size + 1}: {len(documents)} chunks")
            
            logger.info(f"ChromaDB indexing complete. Collection has {collection.count()} documents")
        except Exception as e:
            logger.error(f"Failed to index to ChromaDB: {e}", exc_info=True)
            raise
    
    
    async def search_semantic(
        self,
        query: str,
        namespace: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Perform semantic search within a namespace.
        
        Args:
            query: Natural language search query
            namespace: Explicit namespace (e.g., "teams/engineering")
            user_id: User email for user namespace (e.g., "user@example.com")
            limit: Maximum number of results
            
        Returns:
            Search results with relevance scores
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Semantic search not available",
                "results": []
            }
        
        try:
            # Determine namespace path
            if namespace and namespace != "root":
                search_path = Path(self.kb_path) / namespace
            elif user_id and getattr(settings, 'KB_MULTI_USER_ENABLED', False):
                search_path = Path(self.kb_path) / "users" / user_id
                namespace = f"users/{user_id}"
            else:
                # Root namespace is directly in KB_PATH, not a subdirectory
                search_path = Path(self.kb_path)
                namespace = "root"
            
            logger.info(f"Semantic search - namespace: {namespace}, path: {search_path}")
            
            if not search_path.exists():
                logger.warning(f"Search path does not exist: {search_path}")
                return {
                    "success": False,
                    "error": f"Namespace not found: {namespace}",
                    "results": []
                }
            
            # Check Redis cache
            cache_key = self._get_cache_key(namespace, query)
            cached_result = await self._get_cached_result(cache_key)
            if cached_result:
                logger.info(f"Semantic search cache hit for: {query}")
                return cached_result
            
            # Check if index exists before attempting search
            aifs_file = search_path / "_.aifs"
            if not aifs_file.exists():
                logger.info(f"No index found for {namespace}, queuing background indexing")
                # Queue indexing but DON'T wait for it
                await self.indexing_queue.put({
                    "action": "index",
                    "namespace": namespace,
                    "path": search_path
                })
                return {
                    "success": True,
                    "results": [],
                    "total_results": 0,
                    "status": "indexing",
                    "message": "Building search index for this namespace. This happens once and may take a few minutes. Please try again shortly."
                }
            
            # Index exists, perform search
            loop = asyncio.get_event_loop()
            try:
                # Now aifs will just load the existing index, not create one
                search_results = await loop.run_in_executor(
                    None,
                    aifs_search,
                    query,
                    str(search_path),
                    None,  # file_paths
                    limit,  # max_results
                    False,  # verbose
                    False   # python_docstrings_only
                )
                logger.info(f"aifs search returned {len(search_results) if search_results else 0} results")
            except Exception as e:
                logger.error(f"aifs search failed: {e}", exc_info=True)
                # If aifs fails due to broken index, try to recover
                if "JSONDecodeError" in str(e):
                    aifs_file = search_path / "_.aifs"
                    if aifs_file.exists():
                        logger.warning(f"Removing corrupt index file: {aifs_file}")
                        aifs_file.unlink()
                    # Queue for re-indexing
                    await self.indexing_queue.put({
                        "action": "index",
                        "namespace": namespace,
                        "path": search_path
                    })
                    return {
                        "success": True,
                        "results": [],
                        "total_results": 0,
                        "status": "indexing",
                        "message": "Index was corrupted and is being rebuilt. Please try again in a few moments."
                    }
                raise
            
            # Format results
            formatted_results = self._format_search_results(search_results, namespace, limit)
            
            # Cache results
            await self._cache_result(cache_key, formatted_results)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    def _format_search_results(
        self,
        raw_results: List[Any],
        namespace: str,
        limit: int
    ) -> Dict[str, Any]:
        """Format aifs search results for API response."""
        results = []
        
        for i, result in enumerate(raw_results[:limit]):
            # Handle both old format (string) and new format (dict with source)
            if isinstance(result, dict):
                # Our improved aifs returns {"content": text, "source": filepath}
                content = result.get("content", "")
                source_path = result.get("source", "unknown")
                # Extract just the filename from the full path
                if source_path and "/" in source_path:
                    file_path = Path(source_path).name
                else:
                    file_path = source_path
            else:
                # Fallback for old string format
                content = str(result)
                file_path = f"unknown_{i}.md"
            
            # Calculate a simple relevance score based on position
            score = 1.0 - (i * 0.1)
            
            results.append({
                "relative_path": str(file_path),
                "content_excerpt": content[:500] if content else "",
                "relevance_score": score,
                "namespace": namespace
            })
        
        return {
            "success": True,
            "results": results,
            "total_results": len(results),
            "query": "",  # Don't expose the actual query in results
            "search_type": "semantic"
        }
    
    def _get_cache_key(self, namespace: str, query: str) -> str:
        """Generate cache key for semantic search results."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"semantic:{namespace}:{query_hash}"
    
    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached search results from Redis."""
        try:
            if not redis_client:
                return None
                
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
            
        except Exception as e:
            logger.warning(f"Redis cache get failed: {e}")
            return None
    
    async def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache search results in Redis."""
        try:
            if not redis_client:
                return
                
            await redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(result)
            )
            
        except Exception as e:
            logger.warning(f"Redis cache set failed: {e}")
    
    async def reindex_namespace(self, namespace: str) -> Dict[str, Any]:
        """
        Manually trigger reindexing of a namespace.
        
        Args:
            namespace: Namespace to reindex (e.g., "users/email@example.com")
            
        Returns:
            Status of the reindex operation
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Semantic search not available"
            }
        
        try:
            # Determine namespace path
            if namespace == "root":
                path = self.kb_path
            else:
                path = self.kb_path / namespace
            
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Namespace not found: {namespace}"
                }
            
            # Delete existing index to force full reindex
            aifs_file = path / "_.aifs"
            if aifs_file.exists():
                aifs_file.unlink()
                logger.info(f"Deleted existing index for namespace: {namespace}")
            
            # Invalidate ChromaDB collection cache
            chromadb_manager.invalidate_collection(namespace)
            logger.info(f"Invalidated ChromaDB collection for namespace: {namespace}")
            
            # Queue for reindexing
            await self.indexing_queue.put({
                "action": "index",
                "namespace": namespace,
                "path": path
            })
            
            # Invalidate Redis cache for this namespace
            await self._invalidate_namespace_cache(namespace)
            
            return {
                "success": True,
                "message": f"Reindexing queued for namespace: {namespace}",
                "namespace": namespace
            }
            
        except Exception as e:
            logger.error(f"Failed to queue reindex for {namespace}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _invalidate_namespace_cache(self, namespace: str):
        """Invalidate all cached results for a namespace."""
        try:
            if not redis_client:
                return
                
            # Use Redis SCAN to find all keys for this namespace
            pattern = f"semantic:{namespace}:*"
            cursor = 0
            
            while True:
                cursor, keys = await redis_client.scan(cursor, pattern)
                if keys:
                    await redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache entries for namespace: {namespace}")
                
                if cursor == 0:
                    break
                    
        except Exception as e:
            logger.warning(f"Failed to invalidate namespace cache: {e}")
    
    async def reindex_changed_files(self, changed_files: List[str]):
        """
        Reindex specific files after Git sync.
        
        Args:
            changed_files: List of file paths that changed
        """
        if not self.enabled:
            return
        
        try:
            # Group files by namespace
            namespace_files = {}
            
            for file_path in changed_files:
                path = Path(file_path)
                
                # Determine namespace from path
                if path.is_relative_to(self.kb_path / "users"):
                    parts = path.relative_to(self.kb_path / "users").parts
                    if parts:
                        namespace = f"users/{parts[0]}"
                    else:
                        continue
                elif path.is_relative_to(self.kb_path / "teams"):
                    parts = path.relative_to(self.kb_path / "teams").parts
                    if parts:
                        namespace = f"teams/{parts[0]}"
                    else:
                        continue
                else:
                    namespace = "root"
                
                if namespace not in namespace_files:
                    namespace_files[namespace] = []
                namespace_files[namespace].append(file_path)
            
            # Queue reindexing for affected namespaces
            for namespace, files in namespace_files.items():
                await self.indexing_queue.put({
                    "action": "reindex_files",
                    "namespace": namespace,
                    "files": files
                })
                
                # Invalidate cache for affected namespace
                await self._invalidate_namespace_cache(namespace)
            
            logger.info(f"Queued reindexing for {len(namespace_files)} namespaces after Git sync")
            
        except Exception as e:
            logger.error(f"Failed to queue file reindexing: {e}", exc_info=True)
    
    async def _reindex_changed_files(self, namespace: str, files: List[str]):
        """Reindex specific files in a namespace."""
        try:
            # For now, trigger full namespace reindex
            # aifs handles incremental updates automatically
            if namespace == "root":
                path = self.kb_path
            else:
                path = self.kb_path / namespace
            
            await self._index_namespace(namespace, path)
            
        except Exception as e:
            logger.error(f"Failed to reindex files in {namespace}: {e}", exc_info=True)
    
    async def get_indexing_status(self, namespace: str = "root") -> Dict[str, Any]:
        """Check the indexing status for a namespace."""
        if namespace == "root":
            path = self.kb_path
        else:
            path = self.kb_path / namespace
            
        aifs_file = path / "_.aifs"
        
        if aifs_file.exists():
            size = aifs_file.stat().st_size
            # Count how many files are indexed
            md_files = list(path.rglob("*.md"))
            return {
                "status": "ready",
                "indexed": True,
                "index_size": size,
                "total_files": len(md_files),
                "message": f"Index ready ({size:,} bytes, {len(md_files)} files)"
            }
        else:
            # Check if indexing is in progress
            queue_size = self.indexing_queue.qsize()
            
            # Get detailed progress if available
            progress_info = {}
            if hasattr(self, 'indexing_progress'):
                progress = self.indexing_progress
                if progress.get("namespace") == path.name:
                    import time
                    elapsed = time.time() - progress.get("start_time", 0)
                    progress_info = {
                        "total_files": progress.get("total_files", 0),
                        "elapsed_seconds": round(elapsed, 1),
                        "estimated_per_file": round(elapsed / max(1, progress.get("total_files", 1)), 2),
                        "current_status": progress.get("status", "unknown")
                    }
            
            return {
                "status": "indexing" if queue_size > 0 else "not_indexed",
                "indexed": False,
                "queue_size": queue_size,
                "progress": progress_info,
                "message": f"Indexing in progress (queue: {queue_size}, {progress_info.get('total_files', '?')} files)" if queue_size > 0 else "Not indexed yet"
            }
    
    async def shutdown(self):
        """Shutdown the semantic indexer."""
        if self.indexing_task:
            self.indexing_task.cancel()
            try:
                await self.indexing_task
            except asyncio.CancelledError:
                pass
            logger.info("Semantic indexing worker stopped")
        
        # Shutdown ChromaDB manager
        chromadb_manager.shutdown()
        logger.info("ChromaDB manager shutdown")


# Global indexer instance
semantic_indexer = SemanticIndexer()