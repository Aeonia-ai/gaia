"""
KB Service Implementation

Provides the core KB functionality using the KB MCP Server.
"""

import logging
from typing import Dict, Any
from fastapi import HTTPException

from app.models.chat import ChatRequest
from app.shared.config import settings

# Use RBAC-wrapped server when multi-user is enabled
if getattr(settings, 'KB_MULTI_USER_ENABLED', False):
    from .kb_rbac_integration import kb_server_with_rbac as kb_server
    from .kb_mcp_server import kb_orchestrator
else:
    from .kb_mcp_server import kb_server, kb_orchestrator

logger = logging.getLogger(__name__)

async def kb_search_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
    """Direct KB search using MCP tools"""
    try:
        query = request.message
        logger.info(f"🔍 KB search: {query}")
        
        # Get user_id if multi-user mode is enabled
        kwargs = {
            "query": query,
            "limit": 20,
            "include_content": True
        }
        
        if getattr(settings, 'KB_MULTI_USER_ENABLED', False):
            user_id = auth_principal.get("user_id")
            if user_id:
                kwargs["user_id"] = user_id
                logger.info(f"Multi-user KB search for user: {user_id}")
        
        # Execute search using KB server
        search_result = await kb_server.search_kb(**kwargs)
        
        if search_result["success"]:
            results = search_result["results"]
            total = search_result["total_results"]
            
            # Format results for response
            response_content = f"🔍 **KB Search Results for '{query}'**\n\n"
            response_content += f"Found {total} results:\n\n"
            
            for i, result in enumerate(results[:10], 1):
                path = result["relative_path"]
                excerpt = result["content_excerpt"]
                context = result.get("context", "unknown")
                
                response_content += f"**{i}. {path}**\n"
                response_content += f"Context: {context}\n"
                response_content += f"Excerpt: {excerpt[:200]}...\n\n"
            
            if total > 10:
                response_content += f"... and {total - 10} more results.\n"
                
        else:
            response_content = f"❌ Search failed: {search_result.get('error', 'Unknown error')}"
        
        return {
            "status": "success",
            "response": response_content,
            "metadata": {
                "total_results": search_result.get("total_results", 0),
                "query": query
            }
        }
        
    except Exception as e:
        logger.error(f"KB search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB search failed: {e}")

async def kb_context_loader_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
    """Load KOS context using MCP tools"""
    try:
        context_name = request.message.strip()
        logger.info(f"📚 Loading KOS context: {context_name}")
        
        # Load context using KB server
        context_result = await kb_server.load_kos_context(context_name)
        
        if context_result["success"]:
            context = context_result["context"]
            files = context["files"]
            keywords = context.get("keywords", [])
            
            # Format context info
            response_content = f"📚 **KOS Context: {context_name}**\n\n"
            response_content += f"**Summary:** {context.get('summary', 'No summary available')}\n\n"
            response_content += f"**Files:** {len(files)} documents\n"
            response_content += f"**Keywords:** {', '.join(keywords[:10])}\n"
            
            if context.get("dependencies"):
                response_content += f"**Dependencies:** {', '.join(context['dependencies'][:5])}\n"
            
            response_content += "\n**Recent Files:**\n"
            for file_path in files[:10]:
                response_content += f"- {file_path}\n"
                
            if len(files) > 10:
                response_content += f"... and {len(files) - 10} more files.\n"
                
        else:
            response_content = f"❌ Context loading failed: {context_result.get('error', 'Unknown error')}"
        
        return {
            "status": "success",
            "response": response_content,
            "metadata": {
                "context_name": context_name,
                "loaded": context_result["success"]
            }
        }
        
    except Exception as e:
        logger.error(f"KB context loader failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB context loading failed: {e}")

async def kb_multi_task_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
    """Execute multiple KB tasks in parallel"""
    try:
        message = request.message
        logger.info(f"⚡ KB multi-task execution: {message}")
        
        # Parse tasks from message
        tasks = []
        
        if "search" in message.lower():
            # Extract search terms
            search_terms = message.lower().split("search for ")[-1].split(" and ")
            for term in search_terms[:3]:  # Limit to 3 searches
                tasks.append({
                    "type": "search",
                    "query": term.strip(),
                    "limit": 10
                })
        
        if "context" in message.lower():
            # Look for context names mentioned
            common_contexts = ["gaia", "mmoirl", "influences", "kos"]
            for context in common_contexts:
                if context in message.lower():
                    tasks.append({
                        "type": "load_context",
                        "name": context
                    })
        
        if not tasks:
            # Default tasks
            tasks = [
                {"type": "search", "query": message, "limit": 5},
                {"type": "navigate_index", "start_path": "/", "max_depth": 2}
            ]
        
        # Execute tasks using orchestrator
        result = await kb_orchestrator.delegate_kb_tasks(
            tasks=tasks,
            parallel=True,
            compression_strategy="summary"
        )
        
        if result["success"]:
            compressed = result["results"]
            summary = compressed.get("summary", {})
            findings = compressed.get("key_findings", [])
            
            response_content = f"⚡ **Multi-Task KB Execution Complete**\n\n"
            response_content += f"**Tasks Executed:** {summary.get('total_tasks', 0)}\n"
            response_content += f"**Successful:** {summary.get('successful', 0)}\n"
            response_content += f"**Failed:** {summary.get('failed', 0)}\n\n"
            
            if findings:
                response_content += "**Key Findings:**\n"
                for finding in findings:
                    response_content += f"- {finding}\n"
            
            if summary.get("error_summary"):
                response_content += "\n**Errors:**\n"
                for error in summary["error_summary"]:
                    if error:
                        response_content += f"- {error}\n"
                        
        else:
            response_content = f"❌ Multi-task execution failed: {result.get('error', 'Unknown error')}"
        
        return {
            "status": "success",
            "response": response_content,
            "metadata": {
                "tasks_count": len(tasks),
                "execution_mode": "parallel"
            }
        }
        
    except Exception as e:
        logger.error(f"KB multi-task failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB multi-task execution failed: {e}")

async def kb_navigate_index_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
    """Navigate KB index system"""
    try:
        start_path = request.message.strip() or "/"
        logger.info(f"🧭 Navigating KB from: {start_path}")
        
        nav_result = await kb_server.navigate_kb_index(
            start_path=start_path,
            max_depth=3
        )
        
        if nav_result["success"]:
            nav_tree = nav_result["navigation"]
            
            def format_tree(node, indent=0):
                lines = []
                prefix = "  " * indent
                lines.append(f"{prefix}- **{node['name']}** ({node['path']})")
                if node.get("keywords"):
                    lines.append(f"{prefix}  Keywords: {', '.join(node['keywords'][:5])}")
                for child in node.get("children", []):
                    lines.extend(format_tree(child, indent + 1))
                return lines
            
            response_content = f"🧭 **KB Navigation from '{start_path}'**\n\n"
            response_content += "\n".join(format_tree(nav_tree))
        else:
            response_content = f"❌ Navigation failed: {nav_result.get('error', 'Unknown error')}"
        
        return {
            "status": "success",
            "response": response_content,
            "metadata": {
                "start_path": start_path
            }
        }
        
    except Exception as e:
        logger.error(f"KB navigation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB navigation failed: {e}")

async def kb_synthesize_contexts_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
    """Synthesize insights across contexts"""
    try:
        contexts_str = request.message.strip()
        contexts = [c.strip() for c in contexts_str.split(",")]
        logger.info(f"🔮 Synthesizing contexts: {contexts}")
        
        synth_result = await kb_server.synthesize_contexts(
            source_contexts=contexts,
            max_connections=10
        )
        
        if synth_result["success"]:
            insights = synth_result["insights"]
            
            response_content = f"🔮 **Cross-Domain Synthesis**\n\n"
            response_content += f"Contexts analyzed: {', '.join(contexts)}\n\n"
            
            if insights["common_themes"]:
                response_content += "**Common Themes:**\n"
                for theme in insights["common_themes"]:
                    response_content += f"- {theme}\n"
            
            if insights["potential_connections"]:
                response_content += "\n**Connections Found:**\n"
                for conn in insights["potential_connections"][:5]:
                    response_content += f"- {conn['context1']} ↔ {conn['context2']}: "
                    response_content += f"{', '.join(conn['shared_keywords'][:3])}\n"
        else:
            response_content = f"❌ Synthesis failed: {synth_result.get('error', 'Unknown error')}"
        
        return {
            "status": "success",
            "response": response_content,
            "metadata": {
                "contexts": contexts
            }
        }
        
    except Exception as e:
        logger.error(f"KB synthesis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB synthesis failed: {e}")

async def kb_get_threads_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
    """Get active KOS threads"""
    try:
        logger.info("🧵 Getting active threads")
        
        threads_result = await kb_server.get_active_threads()
        
        if threads_result["success"]:
            threads = threads_result["threads"]
            active_count = threads_result["active_count"]
            
            response_content = f"🧵 **Active KOS Threads**\n\n"
            response_content += f"Total: {len(threads)} | Active: {active_count}\n\n"
            
            for thread in threads[:10]:
                response_content += f"**{thread['title']}**\n"
                response_content += f"- ID: {thread['thread_id']}\n"
                response_content += f"- State: {thread['state']}\n"
                response_content += f"- Current: {thread['current_action']}\n"
                response_content += f"- Updated: {thread['last_updated']}\n\n"
        else:
            response_content = f"❌ Thread retrieval failed: {threads_result.get('error', 'Unknown error')}"
        
        return {
            "status": "success",
            "response": response_content,
            "metadata": {
                "total_threads": threads_result.get("total_threads", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"KB threads failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB threads failed: {e}")

async def kb_read_file_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
    """Read a specific KB file"""
    try:
        file_path = request.message.strip()
        logger.info(f"📄 Reading KB file: {file_path}")
        
        file_result = await kb_server.read_kb_file(file_path)
        
        if file_result["success"]:
            content = file_result["content"]
            metadata = file_result.get("frontmatter", {})
            
            response_content = f"📄 **File: {file_path}**\n\n"
            
            if metadata:
                response_content += "**Metadata:**\n"
                for key, value in list(metadata.items())[:5]:
                    response_content += f"- {key}: {value}\n"
                response_content += "\n"
            
            # Truncate content if too long
            if len(content) > 2000:
                response_content += f"**Content (truncated):**\n{content[:2000]}...\n"
                response_content += f"\n*Full content: {len(content)} characters*"
            else:
                response_content += f"**Content:**\n{content}"
        else:
            response_content = f"❌ File read failed: {file_result.get('error', 'Unknown error')}"
        
        return {
            "status": "success",
            "response": response_content,
            "metadata": {
                "file_path": file_path
            }
        }
        
    except Exception as e:
        logger.error(f"KB file read failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB file read failed: {e}")

async def kb_list_directory_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
    """List KB directory contents"""
    try:
        dir_path = request.message.strip() or "/"
        logger.info(f"📁 Listing KB directory: {dir_path}")
        
        list_result = await kb_server.list_kb_directory(dir_path)
        
        if list_result["success"]:
            files = list_result["files"]
            directories = list_result["directories"]
            
            response_content = f"📁 **Directory: {dir_path}**\n\n"
            
            if directories:
                response_content += "**Subdirectories:**\n"
                for d in directories[:10]:
                    response_content += f"- 📁 {d['name']}/\n"
                if len(directories) > 10:
                    response_content += f"... and {len(directories) - 10} more\n"
            
            if files:
                response_content += "\n**Files:**\n"
                for f in files[:15]:
                    size_kb = f.get("size", 0) / 1024
                    response_content += f"- 📄 {f['name']} ({size_kb:.1f} KB)\n"
                if len(files) > 15:
                    response_content += f"... and {len(files) - 15} more\n"
        else:
            response_content = f"❌ Directory listing failed: {list_result.get('error', 'Unknown error')}"
        
        return {
            "status": "success",
            "response": response_content,
            "metadata": {
                "directory": dir_path
            }
        }
        
    except Exception as e:
        logger.error(f"KB directory listing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB directory listing failed: {e}")