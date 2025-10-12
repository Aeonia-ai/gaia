"""
ChromaDB Manager for Semantic Search

Provides a singleton ChromaDB client that persists across searches,
avoiding the overhead of recreating the client and reloading embeddings.

This significantly improves performance by:
- Reusing the ChromaDB client instance
- Keeping embeddings in memory
- Avoiding repeated model initialization
"""

import logging
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading

try:
    import chromadb
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB not available - semantic search disabled")

from app.shared.logging import get_logger

logger = get_logger(__name__)


class ChromaDBManager:
    """
    Singleton manager for ChromaDB clients.
    
    Maintains persistent ChromaDB clients per namespace to avoid
    recreating them on every search. This is similar to the
    MCP-Agent hot loading pattern.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.enabled = CHROMADB_AVAILABLE
        
        if not self.enabled:
            logger.warning("ChromaDB not available")
            return
        
        # Main ephemeral client (in-memory)
        self.client = chromadb.Client()
        
        # Cache of collections per namespace
        self.collections = {}
        
        # Embedding function (reused across all collections)
        self.embed_fn = DefaultEmbeddingFunction()
        
        # Lock for thread-safe collection access
        self.collection_lock = threading.Lock()
        
        logger.info("ChromaDB manager initialized with ephemeral client")
    
    def get_or_create_collection(self, namespace: str) -> Optional[Any]:
        """
        Get or create a collection for a namespace.
        
        Collections are cached to avoid recreation overhead.
        """
        if not self.enabled:
            return None
        
        # Use namespace as collection name (sanitized)
        collection_name = self._sanitize_collection_name(namespace)
        
        with self.collection_lock:
            if collection_name not in self.collections:
                try:
                    # Try to get existing collection
                    self.collections[collection_name] = self.client.get_collection(
                        name=collection_name,
                        embedding_function=self.embed_fn
                    )
                    logger.info(f"Retrieved existing collection: {collection_name}")
                except Exception:
                    # Create new collection
                    self.collections[collection_name] = self.client.create_collection(
                        name=collection_name,
                        embedding_function=self.embed_fn,
                        metadata={"namespace": namespace}
                    )
                    logger.info(f"Created new collection: {collection_name}")
            
            return self.collections[collection_name]
    
    def _sanitize_collection_name(self, namespace: str) -> str:
        """
        Sanitize namespace to valid collection name.
        
        ChromaDB collection names must be 3-63 characters,
        start and end with alphanumeric, and contain only
        alphanumeric, underscores, or hyphens.
        """
        # Replace invalid characters with underscores
        sanitized = namespace.replace("/", "_").replace("@", "_at_").replace(".", "_")
        
        # Ensure it starts with alphanumeric
        if not sanitized[0].isalnum():
            sanitized = "c_" + sanitized
        
        # Truncate if too long, keeping it unique
        if len(sanitized) > 63:
            # Use hash suffix to maintain uniqueness
            hash_suffix = hashlib.md5(namespace.encode()).hexdigest()[:8]
            sanitized = sanitized[:54] + "_" + hash_suffix
        
        # Ensure minimum length
        if len(sanitized) < 3:
            sanitized = "col_" + sanitized
        
        return sanitized.lower()
    
    def load_index_from_file(self, index_path: Path, collection: Any) -> bool:
        """
        Load embeddings from _.aifs file into collection.
        
        Returns True if successfully loaded, False otherwise.
        """
        if not self.enabled or not index_path.exists():
            return False
        
        try:
            with open(index_path, 'r') as f:
                index = json.load(f)
            
            # Clear existing data
            collection.delete(where={})
            
            # Load embeddings from index
            id_counter = 0
            documents = []
            metadatas = []
            ids = []
            
            for file_path, file_index in index.items():
                if "__pycache__" in file_path:
                    continue
                    
                if file_index and "chunks" in file_index:
                    for chunk in file_index["chunks"]:
                        documents.append(chunk)
                        metadatas.append({"file": file_path})
                        ids.append(str(id_counter))
                        id_counter += 1
            
            # Add to collection in batches
            if documents:
                batch_size = 100
                for i in range(0, len(documents), batch_size):
                    batch_end = min(i + batch_size, len(documents))
                    collection.add(
                        documents=documents[i:batch_end],
                        metadatas=metadatas[i:batch_end],
                        ids=ids[i:batch_end]
                    )
                
                logger.info(f"Loaded {len(documents)} chunks from {index_path}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to load index from {index_path}: {e}")
        
        return False
    
    def search(
        self,
        query: str,
        collection: Any,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search in a collection.
        
        Returns list of results with metadata.
        """
        if not self.enabled or not collection:
            return []
        
        try:
            # Perform semantic search
            results = collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            # Format results
            formatted_results = []
            if results and 'documents' in results:
                documents = results['documents'][0] if results['documents'] else []
                metadatas = results['metadatas'][0] if results.get('metadatas') else []
                distances = results['distances'][0] if results.get('distances') else []
                
                for i, doc in enumerate(documents):
                    formatted_results.append({
                        'content': doc,
                        'metadata': metadatas[i] if i < len(metadatas) else {},
                        'score': 1.0 - (distances[i] if i < len(distances) else 0.5)
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def invalidate_collection(self, namespace: str):
        """
        Remove a collection from cache, forcing reload on next access.
        """
        collection_name = self._sanitize_collection_name(namespace)
        
        with self.collection_lock:
            if collection_name in self.collections:
                try:
                    # Delete the collection from ChromaDB
                    self.client.delete_collection(name=collection_name)
                    logger.info(f"Deleted collection: {collection_name}")
                except Exception as e:
                    logger.warning(f"Failed to delete collection {collection_name}: {e}")
                
                # Remove from cache
                del self.collections[collection_name]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about cached collections and memory usage.
        """
        stats = {
            "enabled": self.enabled,
            "cached_collections": len(self.collections) if self.enabled else 0,
            "collections": list(self.collections.keys()) if self.enabled else []
        }
        
        if self.enabled:
            # Get collection sizes
            collection_stats = {}
            for name, collection in self.collections.items():
                try:
                    count = collection.count()
                    collection_stats[name] = {"document_count": count}
                except Exception:
                    collection_stats[name] = {"document_count": "unknown"}
            
            stats["collection_stats"] = collection_stats
        
        return stats
    
    def shutdown(self):
        """
        Clean shutdown of ChromaDB manager.
        """
        if self.enabled:
            # Clear all collections
            with self.collection_lock:
                for collection_name in list(self.collections.keys()):
                    try:
                        self.client.delete_collection(name=collection_name)
                    except Exception:
                        pass
                
                self.collections.clear()
            
            logger.info("ChromaDB manager shutdown complete")


# Global singleton instance
chromadb_manager = ChromaDBManager()