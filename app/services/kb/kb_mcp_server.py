"""
KB MCP Server for Gaia Platform

Implements MCP tools for Knowledge Base integration:
- Direct file system access to mounted KB
- Fast search using ripgrep 
- Context loading and thread management
- Multi-agent delegation capabilities

This integrates with existing Chat Service MCP infrastructure.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import aiofiles
import frontmatter
from pydantic import BaseModel, Field

from app.shared.logging import get_logger
from app.shared.config import settings
from app.services.kb.kb_cache import kb_cache

logger = get_logger(__name__)

class KBSearchResult(BaseModel):
    """Search result from KB"""
    file_path: str
    relative_path: str
    line_number: Optional[int] = None
    content_excerpt: str
    relevance_score: float = 0.0
    context: Optional[str] = None
    keywords: List[str] = []
    entities: Dict[str, List[str]] = {}

class KBFileInfo(BaseModel):
    """KB file metadata"""
    path: str
    relative_path: str
    size: int
    modified: datetime
    content_hash: str
    frontmatter: Dict[str, Any] = {}
    keywords: List[str] = []
    entities: Dict[str, List[str]] = {}

class KBContext(BaseModel):
    """KOS context information"""
    name: str
    path: str
    files: List[str]
    keywords: List[str] = []
    entities: Dict[str, List[str]] = {}
    dependencies: List[str] = []
    summary: str = ""

class KBThread(BaseModel):
    """KOS work thread"""
    thread_id: str
    title: str
    state: str  # 'active', 'paused', 'completed', 'archived'
    current_action: str = ""
    next_steps: List[str] = []
    context: str = ""
    last_updated: datetime
    progress_notes: List[str] = []

class KBMCPServer:
    """
    Knowledge Base MCP Server
    
    Provides MCP tools for KB integration within Chat Service.
    Uses direct file system access for maximum performance.
    """
    
    def __init__(self, kb_path: str = "/kb"):
        self.kb_path = Path(kb_path)
        self.cache = kb_cache  # Use Redis cache
        self.cache_ttl = 300  # 5 minutes
        
        # Validate KB path exists
        if not self.kb_path.exists():
            logger.warning(f"KB path does not exist: {self.kb_path}")
            
        logger.info(f"KB MCP Server initialized with path: {self.kb_path}")
    
    def _validate_path(self, path: str) -> Path:
        """Validate path is within KB and exists"""
        if path.startswith('/'):
            # Absolute path within KB
            full_path = self.kb_path / path[1:]
        else:
            # Relative path
            full_path = self.kb_path / path
            
        # Resolve to prevent directory traversal
        try:
            resolved = full_path.resolve()
            if not str(resolved).startswith(str(self.kb_path.resolve())):
                raise ValueError(f"Path outside KB: {path}")
            return resolved
        except Exception as e:
            raise ValueError(f"Invalid path {path}: {e}")
    
    def _parse_frontmatter(self, content: str) -> tuple[str, Dict[str, Any]]:
        """Parse frontmatter from markdown content"""
        try:
            post = frontmatter.loads(content)
            return post.content, post.metadata
        except Exception:
            return content, {}
    
    def _extract_wiki_links(self, content: str) -> List[str]:
        """Extract wiki-style links [[link]] from content"""
        pattern = r'\[\[([^\]]+)\]\]'
        return re.findall(pattern, content)
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract hashtag keywords from content"""
        pattern = r'#([a-zA-Z0-9_-]+)'
        return list(set(re.findall(pattern, content)))
    
    def _is_index_file(self, path: Path) -> bool:
        """Check if file is a manual index file (+name.md)"""
        return path.name.startswith('+') and path.name.endswith('.md')
    
    async def _run_ripgrep(self, query: str, paths: List[str] = None, options: List[str] = None) -> List[Dict]:
        """Run ripgrep search and parse JSON results"""
        cmd = ["rg", "--json", "--ignore-case", "--type", "md"]
        
        if options:
            cmd.extend(options)
        
        cmd.append(query)
        
        if paths:
            cmd.extend(paths)
        else:
            cmd.append(str(self.kb_path))
            
        try:
            logger.debug(f"Running ripgrep: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0 and process.returncode != 1:  # 1 means no matches
                logger.error(f"Ripgrep error: {stderr.decode()}")
                return []
            
            # Parse JSON output
            results = []
            for line in stdout.decode().strip().split('\n'):
                if not line:
                    continue
                try:
                    result = json.loads(line)
                    if result.get('type') == 'match':
                        results.append(result)
                except json.JSONDecodeError:
                    continue
                    
            return results
            
        except Exception as e:
            logger.error(f"Ripgrep execution failed: {e}")
            return []
    
    # =============================================================================
    # MCP Tool Implementations
    # =============================================================================
    
    async def search_kb(
        self,
        query: str,
        contexts: Optional[List[str]] = None,
        limit: int = 20,
        include_content: bool = False,
        use_index_filter: bool = True
    ) -> Dict[str, Any]:
        """
        Search KB using ripgrep for fast full-text search.
        
        Args:
            query: Search query string
            contexts: List of context paths to search within
            limit: Maximum number of results
            include_content: Include full file content in results
            use_index_filter: Use manual indexes for filtering
            
        Returns:
            Dict with search results and metadata
        """
        try:
            # Check cache first
            cached_result = await self.cache.get_search_results(query, contexts)
            if cached_result:
                logger.info(f"Cache hit for KB search: '{query}'")
                return cached_result
            
            logger.info(f"Searching KB for: '{query}' in contexts: {contexts}")
            
            search_paths = []
            if contexts:
                for context in contexts:
                    context_path = self._validate_path(context)
                    if context_path.exists():
                        search_paths.append(str(context_path))
            
            # Run ripgrep search
            rg_results = await self._run_ripgrep(
                query=query,
                paths=search_paths if search_paths else None,
                options=["--max-count", str(limit)]
            )
            
            # Process results
            search_results = []
            for rg_result in rg_results[:limit]:
                data = rg_result.get('data', {})
                file_path = data.get('path', {}).get('text', '')
                
                if not file_path:
                    continue
                    
                # Get relative path from KB root
                try:
                    rel_path = str(Path(file_path).relative_to(self.kb_path))
                except ValueError:
                    rel_path = file_path
                
                # Extract content
                lines = data.get('lines', {})
                line_text = lines.get('text', '') if lines else ''
                line_number = data.get('line_number')
                
                # Determine context from path
                context = rel_path.split('/')[0] if '/' in rel_path else None
                
                result = KBSearchResult(
                    file_path=file_path,
                    relative_path=rel_path,
                    line_number=line_number,
                    content_excerpt=line_text,
                    context=context,
                    relevance_score=1.0  # TODO: Implement scoring
                )
                
                # Optionally include full content
                if include_content:
                    try:
                        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                            content = await f.read()
                            result.keywords = self._extract_keywords(content)
                    except Exception as e:
                        logger.warning(f"Could not read file {file_path}: {e}")
                
                search_results.append(result.model_dump())
            
            result = {
                "success": True,
                "query": query,
                "contexts": contexts,
                "total_results": len(search_results),
                "results": search_results,
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache the result
            await self.cache.set_search_results(query, result, contexts)
            
            return result
            
        except Exception as e:
            logger.error(f"KB search failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }
    
    async def read_kb_file(self, path: str, parse_frontmatter: bool = True) -> Dict[str, Any]:
        """
        Read a specific KB file by path.
        
        Args:
            path: File path relative to KB root
            parse_frontmatter: Whether to parse markdown frontmatter
            
        Returns:
            Dict with file content and metadata
        """
        try:
            file_path = self._validate_path(path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}",
                    "path": path
                }
            
            if not file_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {path}",
                    "path": path
                }
            
            # Read file content
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                raw_content = await f.read()
            
            # Parse frontmatter if requested
            content = raw_content
            metadata = {}
            if parse_frontmatter and file_path.suffix == '.md':
                content, metadata = self._parse_frontmatter(raw_content)
            
            # Extract additional metadata
            keywords = self._extract_keywords(content)
            wiki_links = self._extract_wiki_links(content)
            
            # File stats
            stat = file_path.stat()
            
            return {
                "success": True,
                "path": path,
                "content": content,
                "raw_content": raw_content,
                "frontmatter": metadata,
                "keywords": keywords,
                "wiki_links": wiki_links,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_index": self._is_index_file(file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to read KB file {path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "path": path
            }
    
    async def load_kos_context(
        self,
        context_name: str,
        include_dependencies: bool = True,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        Load a KOS context by reading its index file and related documents.
        
        Args:
            context_name: Name of context to load (e.g., 'gaia', 'mmoirl')
            include_dependencies: Whether to follow dependencies
            depth: Maximum depth for following links
            
        Returns:
            Dict with context structure and content
        """
        try:
            # Check cache first
            cached_context = await self.cache.get_context(context_name)
            if cached_context:
                logger.info(f"Cache hit for context: {context_name}")
                return cached_context
            
            logger.info(f"Loading KOS context: {context_name}")
            
            # Look for context index file
            index_patterns = [
                f"{context_name}/+{context_name}.md",
                f"{context_name}/+index.md",
                f"+{context_name}.md"
            ]
            
            index_file = None
            for pattern in index_patterns:
                candidate = self.kb_path / pattern
                if candidate.exists():
                    index_file = candidate
                    break
            
            if not index_file:
                return {
                    "success": False,
                    "error": f"Context index not found for: {context_name}",
                    "context_name": context_name
                }
            
            # Read index file
            index_content = await self.read_kb_file(str(index_file.relative_to(self.kb_path)))
            if not index_content["success"]:
                return index_content
            
            # Extract context metadata
            frontmatter = index_content.get("frontmatter", {})
            content = index_content.get("content", "")
            keywords = index_content.get("keywords", [])
            wiki_links = index_content.get("wiki_links", [])
            
            # Find all files in context directory
            context_dir = index_file.parent
            context_files = []
            
            if context_dir.exists() and context_dir.is_dir():
                for file_path in context_dir.rglob("*.md"):
                    if file_path.is_file():
                        rel_path = str(file_path.relative_to(self.kb_path))
                        context_files.append(rel_path)
            
            # Build context structure
            context = KBContext(
                name=context_name,
                path=str(index_file.relative_to(self.kb_path)),
                files=context_files,
                keywords=keywords,
                dependencies=wiki_links if include_dependencies else [],
                summary=content[:500] + "..." if len(content) > 500 else content
            )
            
            result = {
                "success": True,
                "context": context.model_dump(),
                "index_content": index_content,
                "total_files": len(context_files)
            }
            
            # Cache the context
            await self.cache.set_context(context_name, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to load KOS context {context_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "context_name": context_name
            }
    
    async def list_kb_directory(
        self,
        path: str = "/",
        pattern: str = "*.md",
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        List files in a KB directory with optional pattern matching.
        
        Args:
            path: Directory path to list
            pattern: Glob pattern for filtering files
            include_metadata: Whether to include file metadata
            
        Returns:
            Dict with directory listing and metadata
        """
        try:
            dir_path = self._validate_path(path)
            
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {path}",
                    "path": path
                }
            
            if not dir_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {path}",
                    "path": path
                }
            
            # List files matching pattern
            files = []
            directories = []
            
            for item in dir_path.glob(pattern):
                rel_path = str(item.relative_to(self.kb_path))
                
                if item.is_file():
                    file_info = {
                        "name": item.name,
                        "path": rel_path,
                        "is_index": self._is_index_file(item)
                    }
                    
                    if include_metadata:
                        stat = item.stat()
                        file_info.update({
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                    
                    files.append(file_info)
                    
                elif item.is_dir():
                    directories.append({
                        "name": item.name,
                        "path": rel_path
                    })
            
            return {
                "success": True,
                "path": path,
                "files": files,
                "directories": directories,
                "total_files": len(files),
                "total_directories": len(directories)
            }
            
        except Exception as e:
            logger.error(f"Failed to list KB directory {path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "path": path
            }
    
    async def get_active_threads(self) -> Dict[str, Any]:
        """
        Read all active threads from /kos/sessions/threads/
        
        Returns:
            Dict with active threads list
        """
        try:
            threads_path = self.kb_path / "kos" / "sessions" / "threads"
            
            if not threads_path.exists():
                return {
                    "success": True,
                    "threads": [],
                    "message": "No threads directory found"
                }
            
            threads = []
            
            for thread_file in threads_path.glob("*.md"):
                if thread_file.is_file():
                    # Read thread file
                    file_content = await self.read_kb_file(
                        str(thread_file.relative_to(self.kb_path))
                    )
                    
                    if file_content["success"]:
                        frontmatter = file_content.get("frontmatter", {})
                        content = file_content.get("content", "")
                        
                        thread = KBThread(
                            thread_id=thread_file.stem,
                            title=frontmatter.get("title", thread_file.stem),
                            state=frontmatter.get("state", "unknown"),
                            current_action=frontmatter.get("current_action", ""),
                            next_steps=frontmatter.get("next_steps", []),
                            context=frontmatter.get("context", ""),
                            last_updated=datetime.fromtimestamp(thread_file.stat().st_mtime),
                            progress_notes=content.split('\n') if content else []
                        )
                        
                        threads.append(thread.model_dump())
            
            # Sort by last updated
            threads.sort(key=lambda x: x["last_updated"], reverse=True)
            
            return {
                "success": True,
                "threads": threads,
                "total_threads": len(threads),
                "active_count": len([t for t in threads if t["state"] == "active"])
            }
            
        except Exception as e:
            logger.error(f"Failed to get active threads: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "threads": []
            }
    
    async def navigate_kb_index(
        self,
        start_path: str = "/",
        max_depth: int = 3,
        filter_keywords: Optional[List[str]] = None,
        filter_entities: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Navigate KB using the manual index system.
        
        Args:
            start_path: Starting path for navigation
            max_depth: Maximum depth to traverse
            filter_keywords: Keywords to filter by
            filter_entities: Entities to filter by
            
        Returns:
            Dict with hierarchical navigation structure
        """
        try:
            logger.info(f"Navigating KB index from: {start_path}")
            
            start_dir = self._validate_path(start_path)
            
            if not start_dir.exists():
                return {
                    "success": False,
                    "error": f"Path not found: {start_path}",
                    "path": start_path
                }
            
            async def traverse_directory(dir_path: Path, current_depth: int = 0):
                """Recursively traverse directories looking for indexes"""
                if current_depth >= max_depth:
                    return None
                
                # Look for index file in this directory
                index_files = list(dir_path.glob("+*.md"))
                
                node = {
                    "path": str(dir_path.relative_to(self.kb_path)),
                    "name": dir_path.name,
                    "has_index": len(index_files) > 0,
                    "children": []
                }
                
                # If index exists, extract metadata
                if index_files:
                    index_file = index_files[0]  # Use first index found
                    index_content = await self.read_kb_file(
                        str(index_file.relative_to(self.kb_path))
                    )
                    
                    if index_content["success"]:
                        node.update({
                            "keywords": index_content.get("keywords", []),
                            "frontmatter": index_content.get("frontmatter", {}),
                            "summary": index_content.get("content", "")[:200]
                        })
                
                # Apply filters
                if filter_keywords:
                    node_keywords = node.get("keywords", [])
                    if not any(kw in node_keywords for kw in filter_keywords):
                        return None
                
                # Traverse subdirectories
                for subdir in dir_path.iterdir():
                    if subdir.is_dir() and not subdir.name.startswith('.'):
                        child = await traverse_directory(subdir, current_depth + 1)
                        if child:
                            node["children"].append(child)
                
                return node
            
            navigation_tree = await traverse_directory(start_dir)
            
            return {
                "success": True,
                "navigation": navigation_tree,
                "start_path": start_path,
                "max_depth": max_depth,
                "filters": {
                    "keywords": filter_keywords,
                    "entities": filter_entities
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to navigate KB index: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "start_path": start_path
            }
    
    async def synthesize_contexts(
        self,
        source_contexts: List[str],
        focus: Optional[str] = None,
        max_connections: int = 10
    ) -> Dict[str, Any]:
        """
        Generate cross-domain insights by analyzing multiple contexts.
        
        Args:
            source_contexts: List of context names to analyze
            focus: Optional focus area for synthesis
            max_connections: Maximum number of connections to identify
            
        Returns:
            Dict with synthesis results and insights
        """
        try:
            logger.info(f"Synthesizing contexts: {source_contexts}")
            
            # Load all specified contexts
            contexts_data = []
            for context_name in source_contexts:
                context = await self.load_kos_context(context_name)
                if context["success"]:
                    contexts_data.append(context["context"])
            
            if not contexts_data:
                return {
                    "success": False,
                    "error": "No valid contexts found",
                    "source_contexts": source_contexts
                }
            
            # Analyze connections between contexts
            all_keywords = []
            all_entities = {}
            context_summaries = []
            
            for context in contexts_data:
                all_keywords.extend(context.get("keywords", []))
                
                # Collect entities
                context_entities = context.get("entities", {})
                for entity_type, entities in context_entities.items():
                    if entity_type not in all_entities:
                        all_entities[entity_type] = []
                    all_entities[entity_type].extend(entities)
                
                context_summaries.append({
                    "name": context["name"],
                    "summary": context.get("summary", ""),
                    "file_count": len(context.get("files", []))
                })
            
            # Find common keywords and themes
            keyword_counts = {}
            for kw in all_keywords:
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
            
            common_keywords = [
                kw for kw, count in keyword_counts.items() 
                if count > 1
            ]
            
            # Generate synthesis insights
            insights = {
                "common_themes": common_keywords[:max_connections],
                "shared_entities": {
                    entity_type: list(set(entities))
                    for entity_type, entities in all_entities.items()
                },
                "context_overlap": len(common_keywords),
                "potential_connections": []
            }
            
            # Identify potential connections based on shared keywords
            for i, ctx1 in enumerate(contexts_data):
                for j, ctx2 in enumerate(contexts_data[i+1:], i+1):
                    ctx1_keywords = set(ctx1.get("keywords", []))
                    ctx2_keywords = set(ctx2.get("keywords", []))
                    shared = ctx1_keywords & ctx2_keywords
                    
                    if shared:
                        insights["potential_connections"].append({
                            "context1": ctx1["name"],
                            "context2": ctx2["name"],
                            "shared_keywords": list(shared),
                            "connection_strength": len(shared)
                        })
            
            return {
                "success": True,
                "source_contexts": source_contexts,
                "focus": focus,
                "insights": insights,
                "context_summaries": context_summaries,
                "total_contexts": len(contexts_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to synthesize contexts: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "source_contexts": source_contexts
            }

# =============================================================================
# Multi-Agent Delegation Tool
# =============================================================================

class KBTaskOrchestrator:
    """Orchestrator for parallel KB task execution"""
    
    def __init__(self, kb_server: KBMCPServer):
        self.kb_server = kb_server
        self.max_workers = 5
    
    async def delegate_kb_tasks(
        self,
        tasks: List[Dict[str, Any]],
        parallel: bool = True,
        max_workers: int = 5,
        compression_strategy: str = "summary"
    ) -> Dict[str, Any]:
        """
        Delegate multiple KB tasks to parallel workers.
        
        Args:
            tasks: List of task dictionaries
            parallel: Whether to execute in parallel
            max_workers: Maximum parallel workers
            compression_strategy: How to compress results
            
        Returns:
            Dict with task results
        """
        try:
            logger.info(f"Delegating {len(tasks)} KB tasks (parallel={parallel})")
            
            if parallel:
                # Execute tasks in parallel
                semaphore = asyncio.Semaphore(max_workers)
                
                async def execute_task_with_semaphore(task):
                    async with semaphore:
                        return await self._execute_single_task(task)
                
                task_results = await asyncio.gather(*[
                    execute_task_with_semaphore(task) for task in tasks
                ])
            else:
                # Sequential execution
                task_results = []
                for task in tasks:
                    result = await self._execute_single_task(task)
                    task_results.append(result)
            
            # Compress results based on strategy
            compressed_results = await self._compress_results(
                task_results, compression_strategy
            )
            
            return {
                "success": True,
                "total_tasks": len(tasks),
                "execution_mode": "parallel" if parallel else "sequential",
                "compression_strategy": compression_strategy,
                "results": compressed_results
            }
            
        except Exception as e:
            logger.error(f"Task delegation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tasks": tasks
            }
    
    async def _execute_single_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single KB task"""
        task_type = task.get("type")
        
        try:
            if task_type == "search":
                return await self.kb_server.search_kb(
                    query=task.get("query", ""),
                    contexts=task.get("contexts"),
                    limit=task.get("limit", 20)
                )
                
            elif task_type == "read_file":
                return await self.kb_server.read_kb_file(
                    path=task.get("path", "")
                )
                
            elif task_type == "load_context":
                return await self.kb_server.load_kos_context(
                    context_name=task.get("name", "")
                )
                
            elif task_type == "list_directory":
                return await self.kb_server.list_kb_directory(
                    path=task.get("path", "/"),
                    pattern=task.get("pattern", "*.md")
                )
                
            elif task_type == "navigate_index":
                return await self.kb_server.navigate_kb_index(
                    start_path=task.get("start_path", "/"),
                    max_depth=task.get("max_depth", 3)
                )
                
            elif task_type == "synthesize":
                return await self.kb_server.synthesize_contexts(
                    source_contexts=task.get("contexts", []),
                    focus=task.get("focus")
                )
                
            else:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}",
                    "task": task
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def _compress_results(
        self, 
        results: List[Dict], 
        strategy: str
    ) -> Dict[str, Any]:
        """Compress task results to manage token usage"""
        
        if strategy == "summary":
            # Create summary of all results
            successful = [r for r in results if r.get("success")]
            failed = [r for r in results if not r.get("success")]
            
            return {
                "summary": {
                    "total_tasks": len(results),
                    "successful": len(successful),
                    "failed": len(failed),
                    "error_summary": [r.get("error") for r in failed]
                },
                "key_findings": self._extract_key_findings(successful),
                "full_results_available": True
            }
            
        elif strategy == "merge":
            # Merge similar results
            merged = {
                "search_results": [],
                "file_contents": [],
                "contexts": [],
                "errors": []
            }
            
            for result in results:
                if not result.get("success"):
                    merged["errors"].append(result)
                elif "results" in result:  # Search result
                    merged["search_results"].extend(result["results"])
                elif "content" in result:  # File content
                    merged["file_contents"].append(result)
                elif "context" in result:  # Context data
                    merged["contexts"].append(result["context"])
            
            return merged
            
        else:  # strategy == "raw"
            return {"raw_results": results}
    
    def _extract_key_findings(self, successful_results: List[Dict]) -> List[str]:
        """Extract key findings from successful task results"""
        findings = []
        
        for result in successful_results:
            if "results" in result and result["results"]:
                # Search results
                count = len(result["results"])
                query = result.get("query", "unknown")
                findings.append(f"Found {count} matches for '{query}'")
                
            elif "context" in result:
                # Context loading
                context = result["context"]
                name = context.get("name", "unknown")
                file_count = len(context.get("files", []))
                findings.append(f"Loaded context '{name}' with {file_count} files")
                
            elif "content" in result:
                # File reading
                path = result.get("path", "unknown")
                size = len(result.get("content", ""))
                findings.append(f"Read file '{path}' ({size} characters)")
        
        return findings[:10]  # Limit to top 10 findings

# Global instance
kb_server = KBMCPServer(kb_path=getattr(settings, 'KB_PATH', '/kb'))
kb_orchestrator = KBTaskOrchestrator(kb_server)