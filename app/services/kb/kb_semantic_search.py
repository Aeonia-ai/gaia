"""
KB Semantic Search Implementation

Provides natural language semantic search capabilities for the GAIA Knowledge Base
using pgvector for PostgreSQL-native vector search.

Key features:
- Namespace-aware indexing (respects user/team/workspace boundaries)
- Incremental indexing based on file modification time
- Persistent vector storage in PostgreSQL
- Redis caching for search results
- Deferred initialization for fast startup
"""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta

# Use pgvector via PostgreSQL
PGVECTOR_AVAILABLE = True
logging.info("Using pgvector for PostgreSQL-native semantic search")

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None  # type: ignore
    EMBEDDINGS_AVAILABLE = False
    logging.warning("sentence-transformers not available - semantic search disabled")

# Import pgvector for asyncpg type registration
try:
    from pgvector.asyncpg import register_vector
    PGVECTOR_ASYNCPG_AVAILABLE = True
except ImportError:
    PGVECTOR_ASYNCPG_AVAILABLE = False
    logging.warning("pgvector.asyncpg not available - vector type registration disabled")

from app.shared.config import settings
from app.shared.redis_client import redis_client
from app.shared.logging import get_logger
from app.shared.database import get_database

logger = get_logger(__name__)


class SemanticIndexer:
    """
    Manages semantic search indexing and querying for KB namespaces.

    Uses pgvector for PostgreSQL-native vector storage with incremental indexing.
    """

    def __init__(self):
        self.kb_path = Path(getattr(settings, 'KB_PATH', '/kb'))
        self.indexing_queue = asyncio.Queue()
        self.indexing_task = None
        self.cache_ttl = getattr(settings, 'KB_SEMANTIC_CACHE_TTL', 3600)  # Default 1 hour

        # Database connection pool
        self.db = get_database()

        # Embedding model (lazy loaded on first use)
        self._embedding_model = None

        # Check configuration
        config_enabled = getattr(settings, 'KB_SEMANTIC_SEARCH_ENABLED', False)
        logger.info(f"KB_SEMANTIC_SEARCH_ENABLED from settings: {config_enabled}")
        logger.info(f"PGVECTOR_AVAILABLE: {PGVECTOR_AVAILABLE}")
        logger.info(f"EMBEDDINGS_AVAILABLE: {EMBEDDINGS_AVAILABLE}")

        self.enabled = PGVECTOR_AVAILABLE and EMBEDDINGS_AVAILABLE and config_enabled

        if not self.enabled:
            if not PGVECTOR_AVAILABLE:
                logger.info("Semantic search disabled - pgvector not available")
            elif not EMBEDDINGS_AVAILABLE:
                logger.info("Semantic search disabled - sentence-transformers not available")
            elif not config_enabled:
                logger.info("Semantic search disabled - not enabled in config")
        else:
            logger.info("Semantic search ENABLED successfully!")

    def _get_embedding_model(self) -> "SentenceTransformer":
        """Lazy load the embedding model (heavy operation)."""
        if self._embedding_model is None:
            logger.info("Loading sentence embedding model (all-MiniLM-L6-v2)...")
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded successfully")
        return self._embedding_model
    
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

            # Run pgvector indexing directly (now async)
            await self._run_pgvector_index(path, namespace)

            logger.info(f"Successfully indexed namespace: {namespace}")

        except Exception as e:
            logger.error(f"Failed to index namespace {namespace}: {e}", exc_info=True)
    
    async def _run_pgvector_index(self, path: Path, namespace: str):
        """
        Run pgvector indexing (async operation).

        Implements incremental indexing by checking file mtime against stored metadata.
        Only reindexes files that have changed since last indexing.
        """
        import time

        start_time = time.time()

        # Get embedding model
        model = self._get_embedding_model()

        # Count files to index
        md_files = list(path.rglob("*.md"))
        total_files = len(md_files)
        logger.info(f"Found {total_files} markdown files in {path}")

        # Track progress
        self.indexing_progress = {
            "namespace": path.name,
            "total_files": total_files,
            "start_time": start_time,
            "status": "indexing"
        }

        try:
            # Get existing file metadata from database
            async with self.db.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT relative_path, mtime, num_chunks
                    FROM kb_semantic_index_metadata
                    WHERE namespace = $1
                    """,
                    namespace
                )
                existing_metadata = {row['relative_path']: (row['mtime'], row['num_chunks']) for row in rows}

                files_to_index = []
                files_skipped = 0

                # Check which files need indexing
                for md_file in md_files:
                    relative_path = str(md_file.relative_to(path))
                    file_mtime = md_file.stat().st_mtime

                    if relative_path in existing_metadata:
                        stored_mtime, _ = existing_metadata[relative_path]
                        mtime_diff = abs(file_mtime - stored_mtime)

                        # Skip if file hasn't changed (within 60 second tolerance for Docker volume mounts)
                        # Larger tolerance handles filesystem sync delays and precision differences
                        if mtime_diff < 60.0:
                            files_skipped += 1
                            continue

                    files_to_index.append(md_file)

                logger.info(f"Incremental indexing: {len(files_to_index)} new/changed files, {files_skipped} unchanged files")

            if not files_to_index:
                logger.info(f"No files need reindexing in {namespace}")
                self.indexing_progress["status"] = "completed"
                self.indexing_progress["elapsed_time"] = time.time() - start_time
                return

            # Process files and generate embeddings
            total_chunks_indexed = 0

            for md_file in files_to_index:
                try:
                    content = md_file.read_text(encoding='utf-8')
                    relative_path = str(md_file.relative_to(path))
                    file_mtime = md_file.stat().st_mtime

                    # Simple chunking - split by double newlines (paragraphs)
                    chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
                    chunks = [chunk for chunk in chunks if len(chunk) > 50]  # Skip very short chunks

                    if not chunks:
                        continue

                    # Generate embeddings for all chunks (offloaded to thread pool to avoid blocking event loop)
                    embeddings = await asyncio.to_thread(
                        model.encode, chunks, convert_to_numpy=True
                    )

                    # Store in database (direct await - no nested loop needed)
                    async with self.db.acquire() as conn:
                        # Register pgvector type for this connection
                        if PGVECTOR_ASYNCPG_AVAILABLE:
                            await register_vector(conn)

                        async with conn.transaction():
                            # Delete old chunks for this file
                            await conn.execute(
                                "DELETE FROM kb_semantic_index_metadata WHERE relative_path = $1 AND namespace = $2",
                                relative_path, namespace
                            )

                            # Insert metadata
                            await conn.execute(
                                """
                                INSERT INTO kb_semantic_index_metadata (relative_path, namespace, mtime, num_chunks)
                                VALUES ($1, $2, $3, $4)
                                """,
                                relative_path, namespace, file_mtime, len(chunks)
                            )

                            # Insert chunks with embeddings
                            for chunk_index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                                chunk_id = f"{namespace}:{relative_path}:{chunk_index}"

                                # Convert numpy array to list for pgvector
                                embedding_list = embedding.tolist()

                                await conn.execute(
                                    """
                                    INSERT INTO kb_semantic_chunk_ids
                                    (namespace, relative_path, chunk_id, chunk_index, chunk_text, embedding)
                                    VALUES ($1, $2, $3, $4, $5, $6::vector)
                                    ON CONFLICT (chunk_id) DO UPDATE
                                    SET chunk_text = EXCLUDED.chunk_text,
                                        embedding = EXCLUDED.embedding
                                    """,
                                    namespace, relative_path, chunk_id, chunk_index, chunk_text, embedding_list
                                )

                    total_chunks_indexed += len(chunks)

                except Exception as e:
                    logger.warning(f"Failed to process {md_file}: {e}")

            elapsed = time.time() - start_time
            logger.info(f"pgvector indexing completed in {elapsed:.1f}s: {total_chunks_indexed} chunks from {len(files_to_index)} files")

            # Update progress
            self.indexing_progress["status"] = "completed"
            self.indexing_progress["elapsed_time"] = elapsed
            self.indexing_progress["completed_time"] = time.time()

        except Exception as e:
            logger.error(f"pgvector indexing failed: {e}", exc_info=True)
            self.indexing_progress["status"] = "failed"
            self.indexing_progress["error"] = str(e)
    
    
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
            
            # Check if PostgreSQL index has data for this namespace
            async with self.db.acquire() as conn:
                # Register pgvector type for this connection
                if PGVECTOR_ASYNCPG_AVAILABLE:
                    await register_vector(conn)

                chunk_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM kb_semantic_chunk_ids c JOIN kb_semantic_index_metadata m ON c.relative_path = m.relative_path WHERE m.namespace = $1",
                    namespace
                )

                if chunk_count == 0:
                    logger.info(f"No pgvector index found for {namespace}, queuing background indexing")
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

                # Generate embedding for query
                model = self._get_embedding_model()
                query_embedding = model.encode(query, convert_to_numpy=True).tolist()

                # Perform pgvector similarity search
                rows = await conn.fetch(
                    """
                    SELECT c.relative_path, c.chunk_text, c.embedding <=> $1::vector AS distance
                    FROM kb_semantic_chunk_ids c
                    JOIN kb_semantic_index_metadata m ON c.relative_path = m.relative_path
                    WHERE m.namespace = $2
                    ORDER BY distance ASC
                    LIMIT $3
                    """,
                    query_embedding, namespace, limit
                )

                # Format results (distance to similarity score: 1 - distance)
                search_results = []
                for row in rows:
                    search_results.append({
                        "relative_path": row['relative_path'],
                        "chunk_text": row['chunk_text'],
                        "distance": row['distance'],
                        "relevance_score": 1.0 - row['distance']  # Convert distance to similarity
                    })

                logger.info(f"pgvector search returned {len(search_results)} results")

            # Format results for API response
            formatted_results = {
                "success": True,
                "results": [
                    {
                        "relative_path": result["relative_path"],
                        "content_excerpt": result["chunk_text"][:500] if result["chunk_text"] else "",
                        "relevance_score": result["relevance_score"],
                        "namespace": namespace
                    }
                    for result in search_results
                ],
                "total_results": len(search_results),
                "query": "",  # Don't expose the actual query
                "search_type": "semantic"
            }
            
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
            
            # Clear existing pgvector index to force full reindex
            async with self.db.acquire() as conn:
                await conn.execute(
                    "DELETE FROM kb_semantic_index_metadata WHERE namespace = $1",
                    namespace
                )
            logger.info(f"Cleared existing pgvector index for namespace: {namespace}")
            
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
        """Check the indexing status for a namespace using PostgreSQL."""
        if namespace == "root":
            path = self.kb_path
        else:
            path = self.kb_path / namespace

        # Check PostgreSQL index stats
        async with self.db.acquire() as conn:
            # Count indexed chunks and files
            indexed_chunks = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM kb_semantic_chunk_ids c
                JOIN kb_semantic_index_metadata m ON c.relative_path = m.relative_path
                WHERE m.namespace = $1
                """,
                namespace
            )

            indexed_files = await conn.fetchval(
                "SELECT COUNT(*) FROM kb_semantic_index_metadata WHERE namespace = $1",
                namespace
            )

        if indexed_chunks and indexed_chunks > 0:
            # Count total markdown files on disk
            md_files = list(path.rglob("*.md"))
            return {
                "status": "ready",
                "indexed": True,
                "indexed_chunks": indexed_chunks,
                "total_files": len(md_files),
                "message": f"Index ready ({indexed_chunks:,} chunks, {indexed_files} indexed files, {len(md_files)} total files)"
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


# Global indexer instance
semantic_indexer = SemanticIndexer()