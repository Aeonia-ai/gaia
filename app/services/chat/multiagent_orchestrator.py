"""
MMOIRL Multiagent Orchestrator Service

TODO: This is Tech Debt, remove
Advanced multiagent coordination using mcp-agent framework within Gaia.
Demonstrates sophisticated agent orchestration for complex MMOIRL scenarios.
"""
from typing import Dict, Any, List, Optional
from fastapi import Depends, HTTPException
import logging
import time
import json
import asyncio

from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.orchestrator.orchestrator import Orchestrator

from app.shared.security import get_current_auth_legacy as get_current_auth
from app.models.chat import ChatRequest

logger = logging.getLogger(__name__)

class MMOIRLMultiagentOrchestrator:
    """
    Advanced multiagent orchestration service for MMOIRL scenarios.
    
    Provides sophisticated agent coordination patterns:
    - Game Master + multiple NPCs
    - Collaborative world building
    - Multi-perspective storytelling
    - Specialized expert teams
    """
    
    def __init__(self):
        self.app = MCPApp(name="gaia_mmoirl_multiagent")
        self.session_orchestrators: Dict[str, Any] = {}
        self._initialized = False
        self._mcp_context = None
        self._agents_cache: Dict[str, List[Agent]] = {}  # Cache agents by scenario type
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the multiagent system with hot-loaded MCP context"""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:  # Double-check after acquiring lock
                return
                
            logger.info("🤖 Initializing MMOIRL multiagent orchestrator with hot loading...")
            start_time = time.time()
            
            # Start MCPApp context and keep it running for the lifetime of the service
            self._mcp_context = self.app.run()
            await self._mcp_context.__aenter__()
            
            # Pre-create agents for each scenario type to avoid per-request initialization
            await self._precreate_agents()
            
            init_time = time.time() - start_time
            logger.info(f"✅ Hot-loaded multiagent orchestrator ready in {init_time:.2f}s")
            self._initialized = True
    
    async def _precreate_agents(self):
        """Pre-create and cache agents for all scenario types"""
        logger.info("Pre-creating agents for all scenarios...")
        
        # Create and cache agents for each scenario type
        self._agents_cache["gamemaster"] = self._create_game_master_agents()
        self._agents_cache["worldbuilding"] = self._create_world_building_agents()
        self._agents_cache["storytelling"] = self._create_storytelling_agents()
        self._agents_cache["problemsolving"] = self._create_expert_problem_solving_agents()
        
        # Initialize all agents
        for scenario_type, agents in self._agents_cache.items():
            for agent in agents:
                await agent.__aenter__()
            logger.debug(f"Initialized {len(agents)} agents for {scenario_type} scenario")
    
    async def cleanup(self):
        """Cleanup when service shuts down"""
        if self._initialized:
            logger.info("🛑 Shutting down hot-loaded multiagent orchestrator...")
            
            # Clean up all cached agents
            for agents in self._agents_cache.values():
                for agent in agents:
                    try:
                        await agent.__aexit__(None, None, None)
                    except Exception as e:
                        logger.error(f"Error cleaning up agent: {e}")
            
            # Clean up MCPApp context
            if self._mcp_context:
                try:
                    await self._mcp_context.__aexit__(None, None, None)
                except Exception as e:
                    logger.error(f"Error cleaning up MCP context: {e}")
            
            self._initialized = False
            self._agents_cache.clear()
    
    def _create_game_master_agents(self) -> List[Agent]:
        """Create specialized NPC agents for game master scenarios"""
        return [
            Agent(
                name="tavern_bartender",
                instruction="""You are Grimjaw, a gruff but wise tavern bartender in a medieval fantasy world.
                You know local gossip, serve ales, and give cryptic advice to adventurers.
                Keep responses authentic to character - gruff exterior, hidden wisdom.""",
                server_names=[]
            ),
            Agent(
                name="tavern_musician", 
                instruction="""You are Lyralei, an elvish bard who performs in the tavern.
                You sing tales of adventure, know ancient lore, and can inspire or warn through song.
                Speak poetically, reference old songs and legends.""",
                server_names=[]
            ),
            Agent(
                name="merchant_patron",
                instruction="""You are Marcus, a weathered merchant who frequents this tavern.
                You trade stories for drinks, know about distant lands and political intrigue.
                Speak like a well-traveled merchant with insider knowledge.""",
                server_names=[]
            ),
            Agent(
                name="city_guard",
                instruction="""You are Captain Elena, off-duty city guard having a drink.
                You're cautious but fair, know about local threats and law enforcement.
                Speak with authority but can be friendly when relaxed.""",
                server_names=[]
            )
        ]
    
    def _create_world_building_agents(self) -> List[Agent]:
        """Create specialist agents for collaborative world building"""
        return [
            Agent(
                name="geography_specialist",
                instruction="""You are a geography and environment designer for fantasy worlds.
                Create detailed landscapes, climates, natural resources, and terrain features.
                Consider how geography affects settlements, trade routes, and conflicts.""",
                server_names=[]
            ),
            Agent(
                name="culture_specialist",
                instruction="""You are a culture and society designer for fantasy worlds.
                Create detailed civilizations, customs, languages, religions, and social structures.
                Ensure cultures fit their geographic environment and have rich backstories.""",
                server_names=[]
            ),
            Agent(
                name="history_specialist",
                instruction="""You are a historical narrative designer for fantasy worlds.
                Create detailed timelines, major events, conflicts, heroes, and legends.
                Ensure history creates interesting current tensions and plot hooks.""",
                server_names=[]
            ),
            Agent(
                name="economics_specialist",
                instruction="""You are an economic systems designer for fantasy worlds.
                Create trade networks, resources, currencies, markets, and economic conflicts.
                Consider how economics drives politics and adventures.""",
                server_names=[]
            )
        ]
    
    def _create_storytelling_agents(self) -> List[Agent]:
        """Create agents for multi-perspective storytelling"""
        return [
            Agent(
                name="hero_narrator",
                instruction="""You tell stories from the hero's perspective - brave, noble, seeking justice.
                Focus on courage, sacrifice, protecting others, and moral choices.""",
                server_names=[]
            ),
            Agent(
                name="villain_narrator",
                instruction="""You tell stories from the villain's perspective - complex motivations, tragic backstory.
                Focus on how they justify their actions, their pain, and their twisted logic.""",
                server_names=[]
            ),
            Agent(
                name="commoner_narrator",
                instruction="""You tell stories from ordinary people's perspective - practical, survival-focused.
                Focus on daily struggles, family concerns, and how grand events affect regular folk.""",
                server_names=[]
            ),
            Agent(
                name="scholar_narrator",
                instruction="""You tell stories from an academic/historical perspective - analytical, long-term view.
                Focus on patterns, precedents, deeper meanings, and unintended consequences.""",
                server_names=[]
            )
        ]
    
    def _create_expert_problem_solving_agents(self) -> List[Agent]:
        """Create expert agents for complex problem solving"""
        return [
            Agent(
                name="game_design_expert",
                instruction="""You are a game design expert specializing in player engagement mechanics.
                Focus on player motivation, balance, progression, and fun factor.""",
                server_names=[]
            ),
            Agent(
                name="technical_expert",
                instruction="""You are a technical expert for real-time multiplayer systems.
                Focus on performance, scalability, networking, and technical feasibility.""",
                server_names=[]
            ),
            Agent(
                name="narrative_expert",
                instruction="""You are a narrative design expert for interactive storytelling.
                Focus on story integration, character development, and meaningful choices.""",
                server_names=[]
            ),
            Agent(
                name="psychology_expert",
                instruction="""You are a behavioral psychology expert for game systems.
                Focus on player behavior, social dynamics, and psychological engagement.""",
                server_names=[]
            )
        ]
    
    async def process_multiagent_request(
        self,
        request: ChatRequest,
        auth_principal: Dict[str, Any],
        scenario_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Process a request using sophisticated multiagent coordination.
        
        Args:
            request: Chat request with message and parameters
            auth_principal: Authentication details
            scenario_type: Type of multiagent scenario to use
        """
        # Ensure the service is initialized with hot-loaded context
        await self.initialize()
        
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
        if not auth_key:
            raise HTTPException(status_code=401, detail="Invalid auth")
        
        # No need for 'async with' - we're using the pre-initialized context
        start_time = time.time()
        
        # Determine scenario type from message content if auto
        if scenario_type == "auto":
            scenario_type = self._detect_scenario_type(request.message)
        
        logger.info(f"🎭 Processing multiagent request - scenario: {scenario_type}")
        
        # Use cached agents instead of creating new ones
        if scenario_type in self._agents_cache:
            agents = self._agents_cache[scenario_type]
        else:
            # Fallback to gamemaster if unknown scenario type
            scenario_type = "gamemaster"
            agents = self._agents_cache["gamemaster"]
        
        # Set orchestrator name and enhance prompt based on scenario
        orchestrator_configs = {
            "gamemaster": ("game_master", self._enhance_gamemaster_prompt),
            "worldbuilding": ("world_architect", self._enhance_worldbuilding_prompt),
            "storytelling": ("story_weaver", self._enhance_storytelling_prompt),
            "problemsolving": ("expert_team", self._enhance_problemsolving_prompt)
        }
        
        orchestrator_name, prompt_enhancer = orchestrator_configs.get(
            scenario_type, 
            ("adaptive_coordinator", lambda x: x)
        )
        scenario_prompt = prompt_enhancer(request.message)
        
        # Create LLM factory
        def llm_factory(agent: Agent):
            # TEMPORARY FIX: Bypass MCP agent due to authentication issues
            # Use direct Anthropic client instead of AnthropicAugmentedLLM
            import os
            import anthropic

            class DirectAnthropicLLM:
                def __init__(self, agent):
                    self.agent = agent
                    self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

                async def generate_str(self, message, request_params=None):
                    try:
                        response = self.client.messages.create(
                            model=request_params.model if request_params else "claude-3-5-sonnet-20241022",
                            max_tokens=request_params.maxTokens if request_params else 2000,
                            temperature=request_params.temperature if request_params else 0.7,
                            messages=[{"role": "user", "content": message}]
                        )
                        return response.content[0].text
                    except Exception as e:
                        logger.error(f"Direct Anthropic LLM error: {e}")
                        return f"[Agent {self.agent.name}] Error processing request"

            return DirectAnthropicLLM(agent)
        
        # Create orchestrator for this scenario (lightweight, just coordinates existing agents)
        orchestrator = Orchestrator(
            llm_factory=llm_factory,
            available_agents=agents,
            plan_type="iterative",  # Dynamic, responsive coordination
            name=orchestrator_name
        )
        
        # Process the request through multiagent orchestration
        response = await orchestrator.generate_str(
            message=scenario_prompt,
            request_params=RequestParams(
                model=request.model or "claude-3-5-sonnet-20241022",
                temperature=0.8,  # Higher creativity for storytelling
                maxTokens=2500,
                max_iterations=3
            )
        )
        
        elapsed = time.time() - start_time
        
        logger.info(f"✅ Multiagent coordination completed in {elapsed:.2f}s")
        
        # Return Gaia-compatible response with multiagent metadata
        return {
            "id": f"multiagent-{auth_key}-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model or "claude-3-5-sonnet-20241022",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(scenario_prompt.split()),
                "completion_tokens": len(response.split()),
                "total_tokens": len(scenario_prompt.split()) + len(response.split())
            },
            "_multiagent": {
                "scenario_type": scenario_type,
                "orchestrator": orchestrator_name,
                "agent_count": len(agents),
                "coordination_time_ms": int(elapsed * 1000),
                "agent_names": [agent.name for agent in agents],
                "hot_loaded": True  # Indicate this used hot-loaded agents
            }
        }
    
    def _detect_scenario_type(self, message: str) -> str:
        """Detect the appropriate multiagent scenario based on message content"""
        message_lower = message.lower()
        
        # Game master scenarios
        if any(word in message_lower for word in ['tavern', 'npc', 'character', 'dialogue', 'scene', 'roleplay']):
            return "gamemaster"
        
        # World building scenarios  
        elif any(word in message_lower for word in ['world', 'region', 'geography', 'culture', 'history', 'create']):
            return "worldbuilding"
        
        # Storytelling scenarios
        elif any(word in message_lower for word in ['story', 'narrative', 'perspective', 'tale', 'legend']):
            return "storytelling"
        
        # Problem solving scenarios
        elif any(word in message_lower for word in ['design', 'problem', 'solution', 'analyze', 'expert', 'complex']):
            return "problemsolving"
        
        else:
            return "gamemaster"  # Default
    
    def _enhance_gamemaster_prompt(self, message: str) -> str:
        """Enhance message for game master scenario"""
        return f"""
        As a Game Master, coordinate multiple NPCs to respond to this player interaction:
        
        PLAYER ACTION: {message}
        
        Orchestrate a rich, immersive scene where each NPC responds according to their 
        personality and knowledge. Create natural dialogue and interactions that make 
        the world feel alive and responsive.
        """
    
    def _enhance_worldbuilding_prompt(self, message: str) -> str:
        """Enhance message for world building scenario"""
        return f"""
        Collaborate as world-building specialists to create a rich, detailed response:
        
        WORLD BUILDING REQUEST: {message}
        
        Each specialist should contribute their expertise (geography, culture, history, economics)
        to create a cohesive, detailed world element that supports engaging gameplay.
        """
    
    def _enhance_storytelling_prompt(self, message: str) -> str:
        """Enhance message for storytelling scenario"""
        return f"""
        Create a rich, multi-perspective narrative response:
        
        STORY PROMPT: {message}
        
        Each narrator should tell this story from their unique perspective (hero, villain, 
        commoner, scholar) to create a layered, nuanced narrative that shows different 
        sides of the same events.
        """
    
    def _enhance_problemsolving_prompt(self, message: str) -> str:
        """Enhance message for problem solving scenario"""
        return f"""
        Collaborate as experts to solve this complex challenge:
        
        PROBLEM/CHALLENGE: {message}
        
        Each expert should analyze from their specialty (game design, technical, narrative, 
        psychology) and work together to create a comprehensive solution.
        """

# Global instance
multiagent_orchestrator = MMOIRLMultiagentOrchestrator()

# FastAPI endpoint
async def multiagent_orchestrator_endpoint(
    request: ChatRequest,
    scenario_type: str = "auto",
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Advanced multiagent orchestration endpoint for MMOIRL.
    
    Supports multiple sophisticated coordination patterns:
    - gamemaster: Game Master + NPCs for interactive scenes
    - worldbuilding: Collaborative specialists for world creation
    - storytelling: Multi-perspective narrative generation
    - problemsolving: Expert teams for complex challenges
    - auto: Automatically detect best scenario type
    """
    try:
        return await multiagent_orchestrator.process_multiagent_request(
            request, 
            auth_principal,
            scenario_type
        )
    except Exception as e:
        logger.error(f"Multiagent orchestration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Specific scenario endpoints
async def gamemaster_scenario_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Game Master orchestrating multiple NPCs for interactive scenes"""
    return await multiagent_orchestrator_endpoint(request, "gamemaster", auth_principal)

async def worldbuilding_scenario_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Collaborative world building with specialist agents"""
    return await multiagent_orchestrator_endpoint(request, "worldbuilding", auth_principal)

async def storytelling_scenario_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Multi-perspective storytelling with different narrative viewpoints"""
    return await multiagent_orchestrator_endpoint(request, "storytelling", auth_principal)

async def problemsolving_scenario_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Expert team collaboration for complex problem solving"""
    return await multiagent_orchestrator_endpoint(request, "problemsolving", auth_principal)