"""
KB-Enhanced Multiagent Orchestrator

Combines existing multiagent orchestration with KB MCP tools to enable
Knowledge Operating System (KOS) agent capabilities.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional

from fastapi import Depends, HTTPException

from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.orchestrator.orchestrator import Orchestrator

from app.shared.security import get_current_auth_legacy as get_current_auth
from app.models.chat import ChatRequest
from .kb_mcp_server import kb_server, kb_orchestrator

logger = logging.getLogger(__name__)

class KBEnhancedMultiagentOrchestrator:
    """
    KB-Enhanced multiagent orchestration service.
    
    Combines sophisticated agent coordination with Knowledge Base access:
    - Direct access to KB via MCP tools
    - Context-aware agent behaviors
    - Knowledge synthesis across domains
    - Multi-agent KB task delegation
    """
    
    def __init__(self):
        self.app = MCPApp(name="gaia_kb_multiagent")
        self.session_orchestrators: Dict[str, Any] = {}
        self._initialized = False
        self.kb_server = kb_server
        self.kb_orchestrator = kb_orchestrator
    
    async def initialize(self):
        """Initialize the KB-enhanced multiagent system"""
        if self._initialized:
            return
        
        logger.info("🧠 Initializing KB-enhanced multiagent orchestrator...")
        self._initialized = True
    
    def _create_kb_aware_agents(self, scenario: str) -> List[Agent]:
        """Create KB-aware agents based on scenario"""
        
        if scenario == "kb_research":
            return [
                Agent(
                    name="kb_researcher",
                    instruction="""You are a Knowledge Base researcher specializing in cross-domain analysis.
                    You can search KB content, load contexts, and synthesize insights across multiple domains.
                    Use KB tools to gather information and provide comprehensive analysis.""",
                    server_names=[]
                ),
                Agent(
                    name="context_specialist", 
                    instruction="""You are a context management specialist for KOS workflows.
                    You understand the structure of different knowledge domains and can efficiently
                    navigate between contexts. Help users switch between and relate different areas.""",
                    server_names=[]
                ),
                Agent(
                    name="synthesis_expert",
                    instruction="""You are a knowledge synthesis expert who identifies patterns
                    and connections across different domains. You excel at finding insights that
                    emerge from combining multiple perspectives and knowledge areas.""",
                    server_names=[]
                )
            ]
        
        elif scenario == "gamemaster_kb":
            return [
                Agent(
                    name="world_knowledge_keeper",
                    instruction="""You are the World Knowledge Keeper with access to all MMOIRL lore and design documents.
                    Use KB tools to access world building content, character backstories, and established canon.
                    Ensure consistency with existing world knowledge.""",
                    server_names=[]
                ),
                Agent(
                    name="npc_master",
                    instruction="""You are the NPC Master who brings characters to life using KB-stored personalities.
                    Access character profiles, dialogue patterns, and relationship maps from the KB.
                    Coordinate multiple NPCs for rich interactive scenes.""",
                    server_names=[]
                ),
                Agent(
                    name="quest_designer",
                    instruction="""You are the Quest Designer with access to story templates and narrative structures.
                    Use KB resources to create engaging quests that fit the world and character arcs.
                    Balance challenge, story, and player agency.""",
                    server_names=[]
                )
            ]
        
        elif scenario == "development_advisor":
            return [
                Agent(
                    name="architecture_advisor",
                    instruction="""You are a software architecture advisor with access to Gaia's codebase knowledge.
                    Use KB tools to understand current system design, patterns, and technical decisions.
                    Provide guidance that aligns with existing architecture.""",
                    server_names=[]
                ),
                Agent(
                    name="implementation_guide",
                    instruction="""You are an implementation guide who knows the current codebase and development practices.
                    Access KB documentation about coding standards, patterns, and lessons learned.
                    Help translate requirements into implementable solutions.""",
                    server_names=[]
                ),
                Agent(
                    name="integration_specialist",
                    instruction="""You are an integration specialist who understands how different components work together.
                    Use KB knowledge about service interactions, data flows, and integration patterns.
                    Ensure new features integrate smoothly with existing systems.""",
                    server_names=[]
                )
            ]
            
        else:  # Default KB-aware agents
            return [
                Agent(
                    name="kb_navigator",
                    instruction="""You are a Knowledge Base navigator who helps users find and access information.
                    Use KB tools to search content, load contexts, and guide users through knowledge domains.""",
                    server_names=[]
                ),
                Agent(
                    name="knowledge_synthesizer", 
                    instruction="""You are a knowledge synthesizer who combines information from multiple sources.
                    Use KB tools to gather related content and create comprehensive understanding.""",
                    server_names=[]
                )
            ]
    
    async def _execute_kb_enhanced_scenario(
        self, 
        scenario: str, 
        message: str, 
        auth_principal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a KB-enhanced multiagent scenario"""
        
        try:
            await self.initialize()
            
            logger.info(f"🧠 Executing KB-enhanced scenario: {scenario}")
            
            async with self.app.run() as mcp_app:
                # Create scenario-specific agents
                agents = self._create_kb_aware_agents(scenario)
                
                def llm_factory(agent: Agent):
                    return AnthropicAugmentedLLM(agent=agent)
                
                # Create orchestrator with KB-aware agents
                orchestrator = Orchestrator(
                    llm_factory=llm_factory,
                    available_agents=agents,
                    plan_type="iterative",
                    name=f"kb_{scenario}_orchestrator"
                )
                
                # Enhance prompt with KB context instructions
                enhanced_message = f"""
                KNOWLEDGE BASE INTEGRATION INSTRUCTIONS:
                You have access to advanced KB tools through the system. Use these capabilities:
                
                1. SEARCH: Use search_kb(query, contexts) to find relevant information
                2. CONTEXT LOADING: Use load_kos_context(name) to load domain knowledge
                3. FILE ACCESS: Use read_kb_file(path) to read specific documents
                4. SYNTHESIS: Use synthesize_contexts(contexts) for cross-domain insights
                5. NAVIGATION: Use navigate_kb_index() to explore knowledge structure
                
                ORIGINAL REQUEST:
                {message}
                
                APPROACH:
                1. First identify what knowledge might be relevant
                2. Use KB tools to gather necessary information
                3. Coordinate agent responses using gathered knowledge
                4. Synthesize insights that combine KB knowledge with agent expertise
                """
                
                # Execute orchestrated response
                result = await orchestrator.generate_str(
                    message=enhanced_message,
                    request_params=RequestParams(
                        model="claude-3-5-sonnet-20241022",
                        maxTokens=3000,
                        max_iterations=4
                    )
                )
                
                return {
                    "id": f"kb-multiagent-{scenario}-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "claude-3-5-sonnet-20241022", 
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {"prompt_tokens": 100, "completion_tokens": len(result.split()), "total_tokens": 100 + len(result.split())},
                    "scenario": scenario,
                    "kb_enhanced": True,
                    "agents_used": [agent.name for agent in agents]
                }
                
        except Exception as e:
            logger.error(f"KB-enhanced scenario {scenario} failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"KB multiagent scenario failed: {e}")
    
    async def kb_research_scenario(self, message: str, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
        """KB research with multiple specialized agents"""
        return await self._execute_kb_enhanced_scenario("kb_research", message, auth_principal)
    
    async def gamemaster_kb_scenario(self, message: str, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
        """Game mastering with KB-powered world knowledge"""
        return await self._execute_kb_enhanced_scenario("gamemaster_kb", message, auth_principal)
    
    async def development_advisor_scenario(self, message: str, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
        """Development guidance using KB codebase knowledge"""
        return await self._execute_kb_enhanced_scenario("development_advisor", message, auth_principal)
    
    async def adaptive_kb_scenario(self, message: str, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
        """Adaptive scenario that analyzes message to determine best KB approach"""
        
        # Analyze message to determine optimal scenario
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["search", "find", "knowledge", "research", "analysis"]):
            scenario = "kb_research"
        elif any(word in message_lower for word in ["game", "npc", "world", "story", "quest", "character"]):
            scenario = "gamemaster_kb"
        elif any(word in message_lower for word in ["code", "implement", "architecture", "development", "system"]):
            scenario = "development_advisor"
        else:
            scenario = "kb_research"  # Default
        
        logger.info(f"🎯 Auto-selected scenario: {scenario} for message: {message[:100]}...")
        return await self._execute_kb_enhanced_scenario(scenario, message, auth_principal)

# =============================================================================
# Direct KB Task Execution Endpoints
# =============================================================================

async def kb_search_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
    """Direct KB search using MCP tools"""
    try:
        query = request.message
        logger.info(f"🔍 Direct KB search: {query}")
        
        # Execute search using KB server
        search_result = await kb_server.search_kb(
            query=query,
            limit=20,
            include_content=True
        )
        
        if search_result["success"]:
            results = search_result["results"]
            total = search_result["total_results"]
            
            # Format results for chat response
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
            "id": f"kb-search-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "kb-search-tool",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant", 
                    "content": response_content
                },
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": len(response_content.split()), "total_tokens": 10 + len(response_content.split())},
            "kb_tool": "search"
        }
        
    except Exception as e:
        logger.error(f"KB search endpoint failed: {e}", exc_info=True)
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
            
            # Format context info for chat response
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
            "id": f"kb-context-{int(time.time())}",
            "object": "chat.completion", 
            "created": int(time.time()),
            "model": "kb-context-loader",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": len(response_content.split()), "total_tokens": 10 + len(response_content.split())},
            "kb_tool": "context_loader"
        }
        
    except Exception as e:
        logger.error(f"KB context loader failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB context loading failed: {e}")

async def kb_multi_task_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]) -> Dict[str, Any]:
    """Execute multiple KB tasks in parallel"""
    try:
        message = request.message
        logger.info(f"⚡ KB multi-task execution: {message}")
        
        # Parse tasks from message (simplified approach)
        # In practice, this could be more sophisticated parsing
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
            # Default tasks for demonstration
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
            "id": f"kb-multitask-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "kb-multi-task",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 20, "completion_tokens": len(response_content.split()), "total_tokens": 20 + len(response_content.split())},
            "kb_tool": "multi_task"
        }
        
    except Exception as e:
        logger.error(f"KB multi-task endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB multi-task execution failed: {e}")

# =============================================================================
# Main Endpoint Implementations
# =============================================================================

# Global orchestrator instance
kb_multiagent_orchestrator = KBEnhancedMultiagentOrchestrator()

async def kb_enhanced_multiagent_endpoint(
    request: ChatRequest, 
    scenario: str,
    auth_principal: Dict[str, Any]
) -> Dict[str, Any]:
    """Main KB-enhanced multiagent endpoint"""
    
    if scenario == "adaptive" or scenario == "auto":
        return await kb_multiagent_orchestrator.adaptive_kb_scenario(request.message, auth_principal)
    elif scenario == "research":
        return await kb_multiagent_orchestrator.kb_research_scenario(request.message, auth_principal)
    elif scenario == "gamemaster":
        return await kb_multiagent_orchestrator.gamemaster_kb_scenario(request.message, auth_principal)
    elif scenario == "development":
        return await kb_multiagent_orchestrator.development_advisor_scenario(request.message, auth_principal)
    elif scenario == "search":
        return await kb_search_endpoint(request, auth_principal)
    elif scenario == "context":
        return await kb_context_loader_endpoint(request, auth_principal)
    elif scenario == "multitask":
        return await kb_multi_task_endpoint(request, auth_principal)
    else:
        # Default to adaptive
        return await kb_multiagent_orchestrator.adaptive_kb_scenario(request.message, auth_principal)

# Scenario-specific endpoints
async def kb_research_scenario_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]):
    """KB research scenario endpoint"""
    return await kb_multiagent_orchestrator.kb_research_scenario(request.message, auth_principal)

async def kb_gamemaster_scenario_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]):
    """KB-enhanced game master scenario endpoint"""
    return await kb_multiagent_orchestrator.gamemaster_kb_scenario(request.message, auth_principal)

async def kb_development_scenario_endpoint(request: ChatRequest, auth_principal: Dict[str, Any]):
    """KB-enhanced development advisor endpoint"""
    return await kb_multiagent_orchestrator.development_advisor_scenario(request.message, auth_principal)