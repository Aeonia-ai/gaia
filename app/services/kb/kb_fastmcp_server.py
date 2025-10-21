"""
FastMCP HTTP Server for KB Service

Exposes KB MCP tools via HTTP transport for Claude Code integration.
Uses the FastMCP framework to wrap existing KBMCPServer functionality.
"""

from fastmcp import FastMCP
from typing import Optional, List, Dict, Any
import logging

from app.services.kb.kb_mcp_server import kb_server, kb_orchestrator
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    name="GAIA KB Service",
    instructions="""
    You are connected to the GAIA Knowledge Base Service.

    This service provides access to:
    - Game content knowledge base (experiences, waypoints, lore)
    - Documentation knowledge base (developer docs, API references)
    - Semantic search with AI embeddings
    - Git-synchronized content with versioning

    Available capabilities:
    - Search KB content with ripgrep (fast full-text search)
    - Read specific files with frontmatter parsing
    - Load KOS contexts with dependencies
    - Navigate hierarchical index system
    - Synthesize cross-domain insights
    - Execute parallel multi-task workflows
    - Semantic search using natural language

    Use search_kb for keyword searches, search_semantic for conceptual queries.
    """
)

# =============================================================================
# FastMCP Tool Implementations
# =============================================================================

@mcp.tool()
async def search_kb(
    query: str,
    contexts: Optional[List[str]] = None,
    limit: int = 20,
    include_content: bool = False
) -> Dict[str, Any]:
    """
    Search KB using ripgrep for fast full-text search.

    Args:
        query: Search query string (supports regex)
        contexts: Optional list of context paths to search within (e.g., ["experiences", "docs"])
        limit: Maximum number of results to return (default: 20)
        include_content: Include full file content in results (default: false)

    Returns:
        Search results with file paths, excerpts, and relevance scores

    Example:
        search_kb(query="waypoint", contexts=["experiences/wylding-woods"], limit=10)
    """
    try:
        logger.info(f"MCP search_kb called: query='{query}', contexts={contexts}")
        result = await kb_server.search_kb(
            query=query,
            contexts=contexts,
            limit=limit,
            include_content=include_content
        )
        return result
    except Exception as e:
        logger.error(f"MCP search_kb error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def search_semantic(
    query: str,
    limit: int = 10,
    namespace: str = "root"
) -> Dict[str, Any]:
    """
    Search KB using pgvector semantic search for conceptual/natural language queries.

    Uses sentence transformers to generate embeddings and find semantically similar content
    via vector similarity search (cosine distance) in PostgreSQL with pgvector.

    Args:
        query: Natural language search query (e.g., "how does authentication work?")
        limit: Maximum number of results to return (default: 10)
        namespace: KB namespace to search within (default: "root")

    Returns:
        Search results ranked by semantic similarity with relevance scores

    Example:
        search_semantic(query="chat service architecture", limit=5)
    """
    try:
        logger.info(f"MCP search_semantic called: query='{query}', limit={limit}")
        # Import semantic search module
        from app.services.kb.kb_semantic_search import semantic_indexer

        if not semantic_indexer:
            return {"success": False, "error": "Semantic search not available"}

        result = await semantic_indexer.search_semantic(
            query=query,
            namespace=namespace,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"MCP search_semantic error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def read_file(
    path: str,
    parse_frontmatter: bool = True
) -> Dict[str, Any]:
    """
    Read a specific KB file by path.

    Args:
        path: File path relative to KB root (e.g., "experiences/wylding-woods/story.md")
        parse_frontmatter: Parse YAML frontmatter from markdown files (default: true)

    Returns:
        File content, frontmatter metadata, keywords, and wiki links

    Example:
        read_file(path="docs/architecture/overview.md")
    """
    try:
        logger.info(f"MCP read_file called: path='{path}'")
        result = await kb_server.read_kb_file(
            path=path,
            parse_frontmatter=parse_frontmatter
        )
        return result
    except Exception as e:
        logger.error(f"MCP read_file error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def load_context(
    context_name: str,
    include_dependencies: bool = True,
    depth: int = 2
) -> Dict[str, Any]:
    """
    Load a KOS context by reading its index file and related documents.

    Args:
        context_name: Name of context to load (e.g., "gaia", "mmoirl", "wylding-woods")
        include_dependencies: Follow wiki-link dependencies (default: true)
        depth: Maximum depth for following links (default: 2)

    Returns:
        Context structure with index content, file list, keywords, and dependencies

    Example:
        load_context(context_name="wylding-woods", include_dependencies=true)
    """
    try:
        logger.info(f"MCP load_context called: context='{context_name}'")
        result = await kb_server.load_kos_context(
            context_name=context_name,
            include_dependencies=include_dependencies,
            depth=depth
        )
        return result
    except Exception as e:
        logger.error(f"MCP load_context error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def list_directory(
    path: str = "/",
    pattern: str = "*.md",
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    List files in a KB directory with optional pattern matching.

    Args:
        path: Directory path to list (default: "/")
        pattern: Glob pattern for filtering files (default: "*.md")
        include_metadata: Include file metadata like size and modified date (default: true)

    Returns:
        Directory listing with files and subdirectories

    Example:
        list_directory(path="experiences", pattern="*.md")
    """
    try:
        logger.info(f"MCP list_directory called: path='{path}', pattern='{pattern}'")
        result = await kb_server.list_kb_directory(
            path=path,
            pattern=pattern,
            include_metadata=include_metadata
        )
        return result
    except Exception as e:
        logger.error(f"MCP list_directory error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def navigate_index(
    start_path: str = "/",
    max_depth: int = 3,
    filter_keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Navigate KB using the manual index system.

    Traverses directory hierarchy looking for index files (+name.md) and
    builds a navigation tree with metadata.

    Args:
        start_path: Starting path for navigation (default: "/")
        max_depth: Maximum depth to traverse (default: 3)
        filter_keywords: Optional keywords to filter by

    Returns:
        Hierarchical navigation tree with index summaries

    Example:
        navigate_index(start_path="experiences", max_depth=2)
    """
    try:
        logger.info(f"MCP navigate_index called: start_path='{start_path}'")
        result = await kb_server.navigate_kb_index(
            start_path=start_path,
            max_depth=max_depth,
            filter_keywords=filter_keywords
        )
        return result
    except Exception as e:
        logger.error(f"MCP navigate_index error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def synthesize_contexts(
    source_contexts: List[str],
    focus: Optional[str] = None,
    max_connections: int = 10
) -> Dict[str, Any]:
    """
    Generate cross-domain insights by analyzing multiple contexts.

    Identifies common themes, shared entities, and potential connections
    between different knowledge domains.

    Args:
        source_contexts: List of context names to analyze (e.g., ["gaia", "mmoirl"])
        focus: Optional focus area for synthesis
        max_connections: Maximum number of connections to identify (default: 10)

    Returns:
        Synthesis results with common themes, shared entities, and connection insights

    Example:
        synthesize_contexts(source_contexts=["wylding-woods", "mmoirl"], focus="gameplay")
    """
    try:
        logger.info(f"MCP synthesize_contexts called: contexts={source_contexts}")
        result = await kb_server.synthesize_contexts(
            source_contexts=source_contexts,
            focus=focus,
            max_connections=max_connections
        )
        return result
    except Exception as e:
        logger.error(f"MCP synthesize_contexts error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def delegate_tasks(
    tasks: List[Dict[str, Any]],
    parallel: bool = True,
    max_workers: int = 5,
    compression_strategy: str = "summary"
) -> Dict[str, Any]:
    """
    Execute multiple KB tasks in parallel for efficient batch processing.

    Tasks can be: search, read_file, load_context, list_directory, navigate_index, synthesize.

    Args:
        tasks: List of task dictionaries with "type" and task-specific parameters
        parallel: Execute tasks in parallel (default: true)
        max_workers: Maximum parallel workers (default: 5)
        compression_strategy: Result compression ("summary", "merge", "raw")

    Returns:
        Compressed results from all tasks with execution statistics

    Example:
        delegate_tasks(tasks=[
            {"type": "search", "query": "authentication"},
            {"type": "read_file", "path": "docs/auth.md"}
        ], parallel=true)
    """
    try:
        logger.info(f"MCP delegate_tasks called: {len(tasks)} tasks")
        result = await kb_orchestrator.delegate_kb_tasks(
            tasks=tasks,
            parallel=parallel,
            max_workers=max_workers,
            compression_strategy=compression_strategy
        )
        return result
    except Exception as e:
        logger.error(f"MCP delegate_tasks error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def get_active_threads() -> Dict[str, Any]:
    """
    Get all active KOS work threads.

    Reads thread files from /kos/sessions/threads/ and returns their current state,
    progress, and next steps.

    Returns:
        List of active threads with metadata and progress information

    Example:
        get_active_threads()
    """
    try:
        logger.info("MCP get_active_threads called")
        result = await kb_server.get_active_threads()
        return result
    except Exception as e:
        logger.error(f"MCP get_active_threads error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =============================================================================
# Server Info
# =============================================================================

logger.info("FastMCP server initialized with 9 KB tools")
logger.info("Tools: search_kb, search_semantic, read_file, load_context, list_directory, navigate_index, synthesize_contexts, delegate_tasks, get_active_threads")

# Helper function for FastAPI mounting
def get_mcp_app_for_mount():
    """Get FastMCP app configured for mounting at /mcp."""
    return mcp.http_app(path="/")
