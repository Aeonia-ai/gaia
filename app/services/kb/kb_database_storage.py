"""
KB Database Storage Backend

Provides PostgreSQL-based document storage for the Knowledge Base.
Designed for multi-user scenarios with real-time collaboration,
conflict prevention, and rich querying capabilities.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import asyncpg
from pydantic import BaseModel

from app.shared.database import get_database
from app.shared.logging import get_logger

logger = get_logger(__name__)

class KBDocument(BaseModel):
    """KB Document model for database storage"""
    path: str
    content: str
    metadata: Dict[str, Any] = {}
    keywords: List[str] = []
    wiki_links: List[str] = []
    version: int = 1
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class KBDocumentVersion(BaseModel):
    """Document version for history tracking"""
    id: int
    path: str
    version: int
    document: Dict[str, Any]
    change_type: str
    changed_by: Optional[str] = None
    change_message: Optional[str] = None
    created_at: datetime

class KBDatabaseStorage:
    """
    PostgreSQL-based KB storage backend.
    
    Features:
    - ACID transactions for conflict prevention
    - Optimistic locking with version control
    - Full-text search with PostgreSQL
    - Rich metadata queries with JSONB
    - Automatic history tracking
    - Multi-user permission support (future)
    """
    
    def __init__(self):
        self.db = get_database()
        
    async def initialize(self):
        """Initialize the database storage backend"""
        try:
            # Test database connection
            async with self.db.acquire() as conn:
                await conn.fetchval("SELECT 1")
            logger.info("KB database storage initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize KB database storage: {e}")
            raise
    
    async def document_exists(self, path: str) -> bool:
        """Check if a document exists"""
        try:
            async with self.db.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM kb_documents WHERE path = $1)",
                    path
                )
                return result
        except Exception as e:
            logger.error(f"Error checking document existence {path}: {e}")
            return False
    
    async def get_document(self, path: str) -> Optional[KBDocument]:
        """Get a document by path"""
        try:
            async with self.db.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT path, document, version, created_at, updated_at
                    FROM kb_documents 
                    WHERE path = $1
                    """,
                    path
                )
                
                if not row:
                    return None
                
                doc_data = row['document']
                return KBDocument(
                    path=row['path'],
                    content=doc_data.get('content', ''),
                    metadata=doc_data.get('metadata', {}),
                    keywords=doc_data.get('keywords', []),
                    wiki_links=doc_data.get('wiki_links', []),
                    version=row['version'],
                    created_by=doc_data.get('created_by'),
                    modified_by=doc_data.get('modified_by'),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                
        except Exception as e:
            logger.error(f"Error getting document {path}: {e}")
            return None
    
    async def save_document(
        self, 
        document: KBDocument, 
        user_id: Optional[str] = None,
        change_message: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Save a document with optimistic locking.
        
        Args:
            document: Document to save
            user_id: User making the change
            change_message: Description of the change
            expected_version: Expected current version (for conflict detection)
            
        Returns:
            Dict with save result and metadata
        """
        try:
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    # Check if document exists and get current version
                    current_row = await conn.fetchrow(
                        "SELECT version, locked_by, locked_until FROM kb_documents WHERE path = $1",
                        document.path
                    )
                    
                    is_new = current_row is None
                    
                    # Version conflict check
                    if expected_version is not None and not is_new:
                        if current_row['version'] != expected_version:
                            return {
                                "success": False,
                                "error": "version_conflict",
                                "message": f"Document modified by another user. Expected version {expected_version}, got {current_row['version']}",
                                "current_version": current_row['version']
                            }
                    
                    # Lock conflict check
                    if not is_new and current_row['locked_by'] and current_row['locked_until']:
                        if current_row['locked_until'] > datetime.now():
                            if current_row['locked_by'] != user_id:
                                return {
                                    "success": False,
                                    "error": "document_locked",
                                    "message": f"Document locked by {current_row['locked_by']} until {current_row['locked_until']}",
                                    "locked_by": current_row['locked_by'],
                                    "locked_until": current_row['locked_until']
                                }
                    
                    # Prepare document data
                    doc_data = {
                        "content": document.content,
                        "metadata": document.metadata,
                        "keywords": document.keywords,
                        "wiki_links": document.wiki_links,
                        "modified_by": user_id,
                        "change_message": change_message,
                        "modified_at": datetime.now().isoformat()
                    }
                    
                    if is_new:
                        doc_data["created_by"] = user_id
                        doc_data["created_at"] = datetime.now().isoformat()
                        
                        # Insert new document
                        result = await conn.fetchrow(
                            """
                            INSERT INTO kb_documents (path, document, version)
                            VALUES ($1, $2, 1)
                            RETURNING version, created_at, updated_at
                            """,
                            document.path,
                            json.dumps(doc_data)
                        )
                        
                        action = "create"
                        
                    else:
                        # Update existing document with version increment
                        result = await conn.fetchrow(
                            """
                            UPDATE kb_documents 
                            SET document = $2, version = version + 1
                            WHERE path = $1
                            RETURNING version, created_at, updated_at
                            """,
                            document.path,
                            json.dumps(doc_data)
                        )
                        
                        action = "update"
                    
                    if not result:
                        return {
                            "success": False,
                            "error": "save_failed",
                            "message": "Failed to save document"
                        }
                    
                    # Update search index
                    await self._update_search_index(conn, document.path, document.content, document.keywords)
                    
                    # Log activity
                    await self._log_activity(
                        conn, action, document.path, user_id, {
                            "version": result['version'],
                            "change_message": change_message
                        }
                    )
                    
                    return {
                        "success": True,
                        "action": action,
                        "path": document.path,
                        "version": result['version'],
                        "created_at": result['created_at'],
                        "updated_at": result['updated_at']
                    }
                    
        except Exception as e:
            logger.error(f"Error saving document {document.path}: {e}")
            return {
                "success": False,
                "error": "database_error",
                "message": str(e)
            }
    
    async def delete_document(
        self, 
        path: str, 
        user_id: Optional[str] = None,
        change_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete a document"""
        try:
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    # Check if document exists
                    existing = await conn.fetchrow(
                        "SELECT version FROM kb_documents WHERE path = $1",
                        path
                    )
                    
                    if not existing:
                        return {
                            "success": False,
                            "error": "not_found",
                            "message": f"Document not found: {path}"
                        }
                    
                    # Delete document (history will be preserved by trigger)
                    await conn.execute(
                        "DELETE FROM kb_documents WHERE path = $1",
                        path
                    )
                    
                    # Remove from search index
                    await conn.execute(
                        "DELETE FROM kb_search_index WHERE path = $1",
                        path
                    )
                    
                    # Log activity
                    await self._log_activity(
                        conn, "delete", path, user_id, {
                            "change_message": change_message,
                            "version": existing['version']
                        }
                    )
                    
                    return {
                        "success": True,
                        "action": "delete",
                        "path": path
                    }
                    
        except Exception as e:
            logger.error(f"Error deleting document {path}: {e}")
            return {
                "success": False,
                "error": "database_error",
                "message": str(e)
            }
    
    async def move_document(
        self, 
        old_path: str, 
        new_path: str,
        user_id: Optional[str] = None,
        change_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Move/rename a document"""
        try:
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    # Check if source exists
                    source_doc = await conn.fetchrow(
                        "SELECT document, version FROM kb_documents WHERE path = $1",
                        old_path
                    )
                    
                    if not source_doc:
                        return {
                            "success": False,
                            "error": "not_found",
                            "message": f"Source document not found: {old_path}"
                        }
                    
                    # Check if destination already exists
                    dest_exists = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM kb_documents WHERE path = $1)",
                        new_path
                    )
                    
                    if dest_exists:
                        return {
                            "success": False,
                            "error": "destination_exists",
                            "message": f"Destination already exists: {new_path}"
                        }
                    
                    # Update document path
                    doc_data = source_doc['document']
                    doc_data['modified_by'] = user_id
                    doc_data['change_message'] = change_message
                    doc_data['modified_at'] = datetime.now().isoformat()
                    
                    result = await conn.fetchrow(
                        """
                        UPDATE kb_documents 
                        SET path = $2, document = $3, version = version + 1
                        WHERE path = $1
                        RETURNING version, updated_at
                        """,
                        old_path,
                        new_path,
                        json.dumps(doc_data)
                    )
                    
                    # Update search index
                    await conn.execute(
                        "UPDATE kb_search_index SET path = $2 WHERE path = $1",
                        old_path, new_path
                    )
                    
                    # Log activity
                    await self._log_activity(
                        conn, "move", new_path, user_id, {
                            "old_path": old_path,
                            "new_path": new_path,
                            "change_message": change_message
                        }
                    )
                    
                    return {
                        "success": True,
                        "action": "move",
                        "old_path": old_path,
                        "new_path": new_path,
                        "version": result['version'],
                        "updated_at": result['updated_at']
                    }
                    
        except Exception as e:
            logger.error(f"Error moving document {old_path} -> {new_path}: {e}")
            return {
                "success": False,
                "error": "database_error",
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
        """Search documents using PostgreSQL full-text search"""
        try:
            async with self.db.acquire() as conn:
                # Build search conditions
                conditions = []
                params = []
                param_count = 0
                
                # Full-text search condition
                if query.strip():
                    param_count += 1
                    conditions.append(f"search_vector @@ plainto_tsquery('english', ${param_count})")
                    params.append(query)
                
                # Context filtering
                if contexts:
                    context_conditions = []
                    for context in contexts:
                        param_count += 1
                        context_conditions.append(f"si.path LIKE ${param_count}")
                        params.append(f"{context}%")
                    
                    if context_conditions:
                        conditions.append(f"({' OR '.join(context_conditions)})")
                
                # Keyword filtering
                if keywords:
                    param_count += 1
                    conditions.append(f"si.keywords && ${param_count}")
                    params.append(keywords)
                
                # Build WHERE clause
                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
                
                # Add limit and offset
                param_count += 1
                limit_clause = f"LIMIT ${param_count}"
                params.append(limit)
                
                param_count += 1
                offset_clause = f"OFFSET ${param_count}"
                params.append(offset)
                
                # Execute search query
                search_query = f"""
                    SELECT 
                        si.path,
                        si.line_number,
                        si.content_excerpt,
                        si.keywords,
                        d.document->>'content' as full_content,
                        d.document->'metadata' as metadata,
                        d.version,
                        d.updated_at,
                        ts_rank(si.search_vector, plainto_tsquery('english', $1)) as rank
                    FROM kb_search_index si
                    JOIN kb_documents d ON si.path = d.path
                    {where_clause}
                    ORDER BY rank DESC, si.path, si.line_number
                    {limit_clause} {offset_clause}
                """
                
                results = await conn.fetch(search_query, *params)
                
                # Get total count
                count_query = f"""
                    SELECT COUNT(DISTINCT si.path)
                    FROM kb_search_index si
                    JOIN kb_documents d ON si.path = d.path
                    {where_clause}
                """
                
                total_count = await conn.fetchval(count_query, *params[:-2])  # Exclude limit/offset
                
                # Format results
                search_results = []
                for row in results:
                    search_results.append({
                        "path": row['path'],
                        "line_number": row['line_number'],
                        "content_excerpt": row['content_excerpt'],
                        "keywords": row['keywords'],
                        "metadata": row['metadata'],
                        "version": row['version'],
                        "updated_at": row['updated_at'],
                        "relevance_score": float(row['rank']) if row['rank'] else 0.0
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "total_results": total_count,
                    "results": search_results,
                    "limit": limit,
                    "offset": offset
                }
                
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {
                "success": False,
                "error": "search_failed",
                "message": str(e)
            }
    
    async def list_documents(
        self,
        path_prefix: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List documents with optional path prefix filtering"""
        try:
            async with self.db.acquire() as conn:
                # Build query
                where_clause = ""
                params = []
                
                if path_prefix:
                    where_clause = "WHERE path LIKE $1"
                    params.append(f"{path_prefix}%")
                
                # Get documents
                query = f"""
                    SELECT 
                        path,
                        document->'metadata' as metadata,
                        version,
                        created_at,
                        updated_at,
                        LENGTH(document->>'content') as content_length
                    FROM kb_documents
                    {where_clause}
                    ORDER BY path
                    LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
                """
                
                params.extend([limit, offset])
                results = await conn.fetch(query, *params)
                
                # Get total count
                count_query = f"SELECT COUNT(*) FROM kb_documents {where_clause}"
                total_count = await conn.fetchval(count_query, *params[:-2])
                
                # Format results
                documents = []
                for row in results:
                    documents.append({
                        "path": row['path'],
                        "metadata": row['metadata'],
                        "version": row['version'],
                        "content_length": row['content_length'],
                        "created_at": row['created_at'],
                        "updated_at": row['updated_at']
                    })
                
                return {
                    "success": True,
                    "documents": documents,
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset
                }
                
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return {
                "success": False,
                "error": "list_failed",
                "message": str(e)
            }
    
    async def get_document_history(
        self,
        path: str,
        limit: int = 10
    ) -> List[KBDocumentVersion]:
        """Get version history for a document"""
        try:
            async with self.db.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, path, version, document, change_type, 
                           changed_by, change_message, created_at
                    FROM kb_document_history
                    WHERE path = $1
                    ORDER BY version DESC
                    LIMIT $2
                    """,
                    path, limit
                )
                
                return [
                    KBDocumentVersion(
                        id=row['id'],
                        path=row['path'],
                        version=row['version'],
                        document=row['document'],
                        change_type=row['change_type'],
                        changed_by=row['changed_by'],
                        change_message=row['change_message'],
                        created_at=row['created_at']
                    )
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting document history {path}: {e}")
            return []
    
    async def _update_search_index(
        self, 
        conn: asyncpg.Connection, 
        path: str, 
        content: str, 
        keywords: List[str]
    ):
        """Update search index for a document"""
        try:
            # Remove existing index entries
            await conn.execute(
                "DELETE FROM kb_search_index WHERE path = $1",
                path
            )
            
            # Split content into lines and index each line
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                if line.strip():  # Skip empty lines
                    await conn.execute(
                        """
                        INSERT INTO kb_search_index (path, line_number, content_excerpt, search_vector, keywords)
                        VALUES ($1, $2, $3, to_tsvector('english', $3), $4)
                        """,
                        path, line_num, line[:500], keywords  # Limit excerpt to 500 chars
                    )
                    
        except Exception as e:
            logger.error(f"Error updating search index for {path}: {e}")
    
    async def _log_activity(
        self,
        conn: asyncpg.Connection,
        action: str,
        resource_path: str,
        actor_id: Optional[str],
        details: Dict[str, Any]
    ):
        """Log activity for auditing"""
        try:
            await conn.execute(
                """
                INSERT INTO kb_activity_log (action, resource_path, actor_id, details)
                VALUES ($1, $2, $3, $4)
                """,
                action, resource_path, actor_id, json.dumps(details)
            )
        except Exception as e:
            logger.error(f"Error logging activity: {e}")

# Global instance
kb_db_storage = KBDatabaseStorage()