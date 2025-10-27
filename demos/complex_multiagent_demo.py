"""
Complex Multiagent Workflow Demonstration

Shows sophisticated agent coordination patterns for MMOIRL:
1. Game Master orchestrating multiple NPCs
2. Collaborative world building
3. Dynamic story generation with multiple perspectives
4. Complex problem solving with specialized agents
5. Real-time agent coordination patterns
"""
import asyncio
import logging
from typing import Dict, Any, List
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.orchestrator.orchestrator import Orchestrator
from mcp_agent.workflows.parallel.parallel_llm import ParallelLLM

from app.shared.logging import configure_logging_for_service

configure_logging_for_service("multiagent-demo")
logger = logging.getLogger(__name__)

class MMOIRLMultiagentDemo:
    """Demonstrate complex multiagent workflows for MMOIRL gaming"""
    
    def __init__(self):
        self.app = MCPApp(name="mmoirl_multiagent_demo")
    
    async def demo_game_master_orchestration(self):
        """
        Demo: Game Master orchestrating multiple NPCs for dynamic storytelling
        
        Shows how a central Game Master can coordinate multiple specialized
        NPCs to create rich, interactive game experiences.
        """
        print("\n🎮 Demo: Game Master Orchestration")
        print("Scenario: Player enters a tavern in medieval fantasy world")
        print("=" * 60)
        
        async with self.app.run() as mcp_app:
            # Create specialized NPC agents
            bartender_agent = Agent(
                name="tavern_bartender",
                instruction="""You are Grimjaw, a gruff but wise tavern bartender in a medieval fantasy world.
                You know local gossip, serve ales, and give cryptic advice to adventurers.
                Keep responses authentic to character - gruff exterior, hidden wisdom.""",
                server_names=[]
            )
            
            musician_agent = Agent(
                name="tavern_musician", 
                instruction="""You are Lyralei, an elvish bard who performs in the tavern.
                You sing tales of adventure, know ancient lore, and can inspire or warn through song.
                Speak poetically, reference old songs and legends.""",
                server_names=[]
            )
            
            patron_agent = Agent(
                name="tavern_patron",
                instruction="""You are Marcus, a weathered merchant who frequents this tavern.
                You trade stories for drinks, know about distant lands and political intrigue.
                Speak like a well-traveled merchant with insider knowledge.""",
                server_names=[]
            )
            
            guard_agent = Agent(
                name="city_guard",
                instruction="""You are Captain Elena, off-duty city guard having a drink.
                You're cautious but fair, know about local threats and law enforcement.
                Speak with authority but can be friendly when relaxed.""",
                server_names=[]
            )
            
            # Create Game Master orchestrator
            def llm_factory(agent: Agent):
                return AnthropicAugmentedLLM(agent=agent)
            
            game_master = Orchestrator(
                llm_factory=llm_factory,
                available_agents=[bartender_agent, musician_agent, patron_agent, guard_agent],
                plan_type="iterative",  # Dynamic storytelling
                name="tavern_game_master"
            )
            
            # Player enters tavern
            player_action = """
            A hooded figure enters the tavern, looking around nervously. They approach the bar 
            and quietly ask: "I seek information about the missing merchant caravan that 
            disappeared on the northern road. Can anyone here help me?"
            
            Coordinate the NPCs to create an engaging scene where each character responds 
            according to their personality and knowledge. Make it feel like a living world.
            """
            
            print("🎭 Game Master coordinating NPC responses...")
            print(f"Player Action: {player_action}")
            
            result = await game_master.generate_str(
                message=player_action,
                request_params=RequestParams(
                    model="claude-sonnet-4-5",
                    maxTokens=2000,
                    max_iterations=3
                )
            )
            
            print(f"\n🎲 Game Master's Orchestrated Scene:")
            print(result)
    
    async def demo_collaborative_world_building(self):
        """
        Demo: Multiple agents collaboratively building a game world
        
        Shows how different specialist agents can work together to create
        rich, consistent game environments.
        """
        print("\n🏰 Demo: Collaborative World Building")
        print("Building a new region for MMOIRL game")
        print("=" * 50)
        
        async with self.app.run() as mcp_app:
            # Specialist world-building agents
            geography_agent = Agent(
                name="geography_specialist",
                instruction="""You are a geography and environment designer for fantasy worlds.
                Create detailed landscapes, climates, natural resources, and terrain features.
                Consider how geography affects settlements, trade routes, and conflicts.""",
                server_names=[]
            )
            
            culture_agent = Agent(
                name="culture_specialist",
                instruction="""You are a culture and society designer for fantasy worlds.
                Create detailed civilizations, customs, languages, religions, and social structures.
                Ensure cultures fit their geographic environment and have rich backstories.""",
                server_names=[]
            )
            
            history_agent = Agent(
                name="history_specialist", 
                instruction="""You are a historical narrative designer for fantasy worlds.
                Create detailed timelines, major events, conflicts, heroes, and legends.
                Ensure history creates interesting current tensions and plot hooks.""",
                server_names=[]
            )
            
            economy_agent = Agent(
                name="economy_specialist",
                instruction="""You are an economic systems designer for fantasy worlds.
                Create trade networks, resources, currencies, markets, and economic conflicts.
                Consider how economics drives politics and adventures.""",
                server_names=[]
            )
            
            async with geography_agent, culture_agent, history_agent, economy_agent:
                # Attach LLMs
                geo_llm = await geography_agent.attach_llm(AnthropicAugmentedLLM)
                culture_llm = await culture_agent.attach_llm(AnthropicAugmentedLLM)
                history_llm = await history_agent.attach_llm(AnthropicAugmentedLLM)
                economy_llm = await economy_agent.attach_llm(AnthropicAugmentedLLM)
                
                # World building prompt
                world_concept = """
                Create a new region called "The Crimson Reaches" - a frontier territory 
                where ancient magic meets industrial innovation. This region will be 
                a new zone in our MMOIRL game where players can establish settlements, 
                trade, and engage in both cooperation and conflict.
                
                Make it detailed enough for rich player interactions but leave room 
                for emergent gameplay and player-driven stories.
                """
                
                print("🗺️  Specialist agents collaborating...")
                
                # Each specialist works on their domain
                geography_task = geo_llm.generate_str(
                    message=f"{world_concept}\n\nFocus on: Geography, terrain, climate, natural features, resources.",
                    request_params=RequestParams(maxTokens=800)
                )
                
                culture_task = culture_llm.generate_str(
                    message=f"{world_concept}\n\nFocus on: Cultures, societies, settlements, customs, conflicts.",
                    request_params=RequestParams(maxTokens=800)
                )
                
                history_task = history_llm.generate_str(
                    message=f"{world_concept}\n\nFocus on: Historical events, legends, current tensions, mysteries.",
                    request_params=RequestParams(maxTokens=800)
                )
                
                economy_task = economy_llm.generate_str(
                    message=f"{world_concept}\n\nFocus on: Trade routes, resources, markets, economic opportunities.",
                    request_params=RequestParams(maxTokens=800)
                )
                
                # Wait for all specialists to complete
                geography_result, culture_result, history_result, economy_result = await asyncio.gather(
                    geography_task, culture_task, history_task, economy_task
                )
                
                print("🏗️  World Building Results:")
                print("\n📍 GEOGRAPHY:")
                print(geography_result[:300] + "...\n")
                
                print("👥 CULTURE:")
                print(culture_result[:300] + "...\n")
                
                print("📜 HISTORY:")
                print(history_result[:300] + "...\n")
                
                print("💰 ECONOMY:")
                print(economy_result[:300] + "...\n")
                
                # Synthesis agent combines all perspectives
                synthesis_agent = Agent(
                    name="world_synthesis",
                    instruction="Synthesize multiple specialist inputs into a cohesive world design.",
                    server_names=[]
                )
                
                async with synthesis_agent:
                    synthesis_llm = await synthesis_agent.attach_llm(AnthropicAugmentedLLM)
                    
                    synthesis_prompt = f"""
                    Synthesize these specialist perspectives into a cohesive world region design:
                    
                    GEOGRAPHY: {geography_result}
                    
                    CULTURE: {culture_result}
                    
                    HISTORY: {history_result}
                    
                    ECONOMY: {economy_result}
                    
                    Create a unified vision that highlights how these elements interconnect 
                    and create opportunities for player engagement.
                    """
                    
                    final_world = await synthesis_llm.generate_str(
                        message=synthesis_prompt,
                        request_params=RequestParams(maxTokens=1200)
                    )
                    
                    print("🌍 FINAL SYNTHESIZED WORLD DESIGN:")
                    print(final_world)
    
    async def demo_dynamic_story_generation(self):
        """
        Demo: Multiple perspective agents creating branching narratives
        
        Shows how different agents can represent different viewpoints
        to create rich, multi-perspective storytelling.
        """
        print("\n📖 Demo: Dynamic Multi-Perspective Story Generation")
        print("Creating branching narrative from multiple viewpoints")
        print("=" * 55)
        
        async with self.app.run() as mcp_app:
            # Perspective agents
            hero_agent = Agent(
                name="hero_perspective",
                instruction="""You tell stories from the hero's perspective - brave, noble, seeking justice.
                Focus on courage, sacrifice, protecting others, and moral choices.""",
                server_names=[]
            )
            
            villain_agent = Agent(
                name="villain_perspective", 
                instruction="""You tell stories from the villain's perspective - complex motivations, tragic backstory.
                Focus on how they justify their actions, their pain, and their twisted logic.""",
                server_names=[]
            )
            
            common_folk_agent = Agent(
                name="commoner_perspective",
                instruction="""You tell stories from ordinary people's perspective - practical, survival-focused.
                Focus on daily struggles, family concerns, and how grand events affect regular folk.""",
                server_names=[]
            )
            
            scholar_agent = Agent(
                name="scholar_perspective",
                instruction="""You tell stories from an academic/historical perspective - analytical, long-term view.
                Focus on patterns, precedents, deeper meanings, and unintended consequences.""",
                server_names=[]
            )
            
            async with hero_agent, villain_agent, common_folk_agent, scholar_agent:
                # Attach LLMs
                hero_llm = await hero_agent.attach_llm(AnthropicAugmentedLLM)
                villain_llm = await villain_agent.attach_llm(AnthropicAugmentedLLM)
                folk_llm = await common_folk_agent.attach_llm(AnthropicAugmentedLLM)
                scholar_llm = await scholar_agent.attach_llm(AnthropicAugmentedLLM)
                
                # Story catalyst
                story_event = """
                A powerful magical artifact has been discovered in the ruins of an ancient city.
                Multiple factions want to claim it: the Royal Army (for protection), 
                the Mage Guild (for study), and the Underground (for profit).
                
                Meanwhile, the artifact seems to be affecting the surrounding area,
                causing strange phenomena and awakening ancient guardians.
                
                Tell this story from your unique perspective.
                """
                
                print("📚 Multiple agents creating different story perspectives...")
                
                # Generate all perspectives simultaneously
                hero_story = hero_llm.generate_str(
                    message=f"{story_event}\n\nTell from hero's perspective.",
                    request_params=RequestParams(maxTokens=600)
                )
                
                villain_story = villain_llm.generate_str(
                    message=f"{story_event}\n\nTell from villain's perspective.",
                    request_params=RequestParams(maxTokens=600)
                )
                
                folk_story = folk_llm.generate_str(
                    message=f"{story_event}\n\nTell from common folk's perspective.",
                    request_params=RequestParams(maxTokens=600)
                )
                
                scholar_story = scholar_llm.generate_str(
                    message=f"{story_event}\n\nTell from scholar's perspective.",
                    request_params=RequestParams(maxTokens=600)
                )
                
                # Wait for all stories
                hero_result, villain_result, folk_result, scholar_result = await asyncio.gather(
                    hero_story, villain_story, folk_story, scholar_story
                )
                
                print("📖 MULTI-PERSPECTIVE NARRATIVE:")
                print("\n🦸 HERO'S PERSPECTIVE:")
                print(hero_result)
                
                print("\n😈 VILLAIN'S PERSPECTIVE:")
                print(villain_result)
                
                print("\n👥 COMMON FOLK'S PERSPECTIVE:")
                print(folk_result)
                
                print("\n🔬 SCHOLAR'S PERSPECTIVE:")
                print(scholar_result)
    
    async def demo_specialized_problem_solving(self):
        """
        Demo: Specialized agents collaborating on complex problem solving
        
        Shows how different expert agents can tackle different aspects
        of a complex challenge that requires multiple skills.
        """
        print("\n🔬 Demo: Specialized Problem Solving")
        print("Challenge: Designing a complex MMOIRL encounter")
        print("=" * 50)
        
        async with self.app.run() as mcp_app:
            # Expert agents for different aspects
            game_design_agent = Agent(
                name="game_design_expert",
                instruction="""You are a game design expert specializing in player engagement mechanics.
                Focus on player motivation, balance, progression, and fun factor.""",
                server_names=[]
            )
            
            technical_agent = Agent(
                name="technical_expert",
                instruction="""You are a technical expert for real-time multiplayer systems.
                Focus on performance, scalability, networking, and technical feasibility.""",
                server_names=[]
            )
            
            narrative_agent = Agent(
                name="narrative_expert", 
                instruction="""You are a narrative design expert for interactive storytelling.
                Focus on story integration, character development, and meaningful choices.""",
                server_names=[]
            )
            
            psychology_agent = Agent(
                name="psychology_expert",
                instruction="""You are a behavioral psychology expert for game systems.
                Focus on player behavior, social dynamics, and psychological engagement.""",
                server_names=[]
            )
            
            def llm_factory(agent: Agent):
                return AnthropicAugmentedLLM(agent=agent)
            
            # Create orchestrator for the problem-solving team
            problem_solving_team = Orchestrator(
                llm_factory=llm_factory,
                available_agents=[game_design_agent, technical_agent, narrative_agent, psychology_agent],
                plan_type="full",  # Complete planning approach
                name="mmoirl_design_team"
            )
            
            # Complex design challenge
            design_challenge = """
            Design a sophisticated MMOIRL encounter called "The Living City Council" where:
            
            1. 50-100 players must work together in real-time to govern a virtual city
            2. Decisions affect both virtual and real-world outcomes (urban planning education)
            3. Players have different roles (mayor, citizens, businesses, activists)
            4. The system must handle complex negotiations and voting in real-time
            5. AI NPCs represent different city departments and interest groups
            6. Economic, social, and environmental factors all interact
            7. Sessions last 2-3 hours with persistent consequences
            
            This needs to be educational, engaging, technically feasible, and psychologically compelling.
            Create a complete design that addresses all these requirements.
            """
            
            print("🧠 Expert team collaborating on complex design challenge...")
            
            result = await problem_solving_team.generate_str(
                message=design_challenge,
                request_params=RequestParams(
                    model="claude-sonnet-4-5",
                    maxTokens=3000,
                    max_iterations=4
                )
            )
            
            print("💡 COLLABORATIVE DESIGN SOLUTION:")
            print(result)

async def run_all_multiagent_demos():
    """Run all complex multiagent demonstrations"""
    demo = MMOIRLMultiagentDemo()
    
    print("🤖 Complex Multiagent Workflow Demonstrations")
    print("Showcasing sophisticated agent coordination for MMOIRL")
    print("=" * 70)
    
    try:
        await demo.demo_game_master_orchestration()
        await demo.demo_collaborative_world_building()
        await demo.demo_dynamic_story_generation()
        await demo.demo_specialized_problem_solving()
        
        print("\n🎉 All multiagent demonstrations completed!")
        print("\n🎯 Key Capabilities Demonstrated:")
        print("✅ Orchestrator-Workers pattern for complex coordination")
        print("✅ Parallel agent processing for efficiency")
        print("✅ Specialized agents with distinct expertise")
        print("✅ Multi-perspective narrative generation")
        print("✅ Collaborative problem solving")
        print("✅ Dynamic NPC coordination")
        print("✅ Real-time agent collaboration patterns")
        
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
        print(f"❌ Demo failed: {e}")

async def run_single_demo(demo_name: str):
    """Run a specific demonstration"""
    demo = MMOIRLMultiagentDemo()
    
    demo_map = {
        "gamemaster": demo.demo_game_master_orchestration,
        "worldbuilding": demo.demo_collaborative_world_building,
        "storytelling": demo.demo_dynamic_story_generation,
        "problemsolving": demo.demo_specialized_problem_solving
    }
    
    if demo_name in demo_map:
        await demo_map[demo_name]()
    else:
        print(f"Unknown demo: {demo_name}")
        print(f"Available demos: {', '.join(demo_map.keys())}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        demo_name = sys.argv[1]
        asyncio.run(run_single_demo(demo_name))
    else:
        print("Usage:")
        print("  python demos/complex_multiagent_demo.py [demo_name]")
        print("\nAvailable demos:")
        print("  gamemaster     - Game Master orchestrating NPCs")
        print("  worldbuilding  - Collaborative world building")
        print("  storytelling   - Multi-perspective narratives")  
        print("  problemsolving - Specialized expert collaboration")
        print("  (no args)      - Run all demos")
        print()
        asyncio.run(run_all_multiagent_demos())