"""
Standalone Complex Multiagent Demo

Demonstrates sophisticated mcp-agent multiagent workflows without Gaia dependencies.
Shows the power of agent orchestration for MMOIRL applications.
"""
import asyncio
import logging
from typing import Dict, Any, List
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.orchestrator.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_game_master_orchestration():
    """
    Demo: Game Master orchestrating multiple NPCs for dynamic storytelling
    
    This shows how MMOIRL can use sophisticated agent coordination
    to create rich, interactive experiences where multiple AI characters
    work together to respond to player actions.
    """
    print("\n🎮 MMOIRL Game Master Orchestration Demo")
    print("Scenario: Player enters a tavern seeking information")
    print("=" * 60)
    
    app = MCPApp(name="mmoirl_gamemaster_demo")
    
    async with app.run() as mcp_app:
        # Create specialized NPC agents with distinct personalities
        bartender_agent = Agent(
            name="tavern_bartender",
            instruction="""You are Grimjaw, a gruff but wise tavern bartender in a medieval fantasy world.
            You know local gossip, serve ales, and give cryptic advice to adventurers.
            Keep responses authentic to character - gruff exterior, hidden wisdom.
            You've heard rumors about bandit attacks on trade routes.""",
            server_names=[]
        )
        
        musician_agent = Agent(
            name="tavern_musician", 
            instruction="""You are Lyralei, an elvish bard who performs in the tavern.
            You sing tales of adventure, know ancient lore, and can inspire or warn through song.
            Speak poetically, reference old songs and legends.
            You know a ballad about a cursed caravan from years past.""",
            server_names=[]
        )
        
        patron_agent = Agent(
            name="tavern_patron",
            instruction="""You are Marcus, a weathered merchant who frequents this tavern.
            You trade stories for drinks, know about distant lands and political intrigue.
            Speak like a well-traveled merchant with insider knowledge.
            You've heard concerning reports from other merchants.""",
            server_names=[]
        )
        
        guard_agent = Agent(
            name="city_guard",
            instruction="""You are Captain Elena, off-duty city guard having a drink.
            You're cautious but fair, know about local threats and law enforcement.
            Speak with authority but can be friendly when relaxed.
            You're investigating the missing caravan case officially.""",
            server_names=[]
        )
        
        # Create Game Master orchestrator
        def llm_factory(agent: Agent):
            return AnthropicAugmentedLLM(agent=agent)
        
        game_master = Orchestrator(
            llm_factory=llm_factory,
            available_agents=[bartender_agent, musician_agent, patron_agent, guard_agent],
            plan_type="iterative",  # Dynamic, responsive storytelling
            name="tavern_game_master"
        )
        
        # Player enters and asks for information
        player_action = """
        A hooded figure enters the tavern, scanning the room nervously before approaching the bar. 
        They lower their hood, revealing a young woman with worried eyes, and speak quietly:
        
        "I seek information about the merchant caravan that disappeared on the northern road 
        three days ago. My brother was the caravan guard... Please, does anyone here know 
        what happened to them? I can pay for information."
        
        Game Master: Coordinate all four NPCs (Grimjaw the bartender, Lyralei the bard, 
        Marcus the merchant, and Captain Elena the guard) to respond naturally to this situation. 
        Each should react according to their personality and what they know. Create a rich, 
        immersive scene that feels like a living world where NPCs have their own agendas 
        and relationships.
        """
        
        print("🎭 Game Master coordinating multiple NPCs...")
        print(f"\nPlayer Action: {player_action.split('Game Master:')[0].strip()}")
        print("\n⚡ Orchestrating agent responses...")
        
        try:
            result = await game_master.generate_str(
                message=player_action,
                request_params=RequestParams(
                    model="claude-3-5-sonnet-20241022",
                    maxTokens=2500,
                    max_iterations=3
                )
            )
            
            print(f"\n🎲 Orchestrated Tavern Scene:")
            print("-" * 50)
            print(result)
            
            print(f"\n✨ This demonstrates:")
            print("• Multiple specialized agents with distinct personalities")
            print("• Orchestrator coordinating complex multi-character interactions")
            print("• Dynamic storytelling that responds to player input")
            print("• Rich NPC behavior that creates immersive game worlds")
            print("• How MMOIRL can use multiagent systems for sophisticated gameplay")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            logger.error(f"Orchestration error: {e}", exc_info=True)

async def demo_collaborative_specialists():
    """
    Demo: Multiple specialist agents collaborating on complex problem
    
    Shows how MMOIRL can use specialized agents working together
    to solve complex challenges that require multiple expertise areas.
    """
    print("\n🧠 Collaborative Specialists Demo")
    print("Challenge: Designing a complex multiplayer puzzle")
    print("=" * 50)
    
    app = MCPApp(name="collaborative_specialists")
    
    async with app.run() as mcp_app:
        # Create specialist agents
        game_designer = Agent(
            name="game_design_specialist",
            instruction="""You are a game design expert specializing in multiplayer mechanics.
            Focus on player engagement, cooperation requirements, difficulty balance, and fun factor.
            Consider how to make puzzles that require teamwork but aren't frustrating.""",
            server_names=[]
        )
        
        puzzle_engineer = Agent(
            name="puzzle_engineering_specialist",
            instruction="""You are a puzzle design engineer who creates logical, solvable challenges.
            Focus on mechanical complexity, solution paths, fail-safes, and technical implementation.
            Ensure puzzles are challenging but fair with clear feedback systems.""",
            server_names=[]
        )
        
        social_psychologist = Agent(
            name="social_psychology_specialist",
            instruction="""You are a social psychology expert specializing in group dynamics.
            Focus on communication requirements, leadership emergence, conflict resolution, and team coordination.
            Consider how different personality types will interact in puzzle scenarios.""",
            server_names=[]
        )
        
        async with game_designer, puzzle_engineer, social_psychologist:
            # Attach LLMs to each specialist
            design_llm = await game_designer.attach_llm(AnthropicAugmentedLLM)
            engineering_llm = await puzzle_engineer.attach_llm(AnthropicAugmentedLLM)
            psychology_llm = await social_psychologist.attach_llm(AnthropicAugmentedLLM)
            
            # Complex design challenge
            challenge = """
            Design a multiplayer puzzle called "The Resonance Chamber" for 6-8 players where:
            
            - Players must coordinate in real-time to manipulate magical crystals
            - Each player controls different aspects (frequency, amplitude, timing, direction)
            - Success requires precise teamwork and communication
            - The puzzle should take 15-20 minutes to solve
            - It should be engaging for both leaders and followers
            - Include contingencies for when teams get stuck
            - Consider how to handle players joining/leaving mid-puzzle
            
            Focus on your area of expertise and provide detailed recommendations.
            """
            
            print("🔬 Specialists analyzing the challenge...")
            
            # Each specialist works in parallel on their domain
            design_analysis = design_llm.generate_str(
                message=f"{challenge}\n\nAnalyze from GAME DESIGN perspective.",
                request_params=RequestParams(maxTokens=800)
            )
            
            engineering_analysis = engineering_llm.generate_str(
                message=f"{challenge}\n\nAnalyze from PUZZLE ENGINEERING perspective.", 
                request_params=RequestParams(maxTokens=800)
            )
            
            psychology_analysis = psychology_llm.generate_str(
                message=f"{challenge}\n\nAnalyze from SOCIAL PSYCHOLOGY perspective.",
                request_params=RequestParams(maxTokens=800)
            )
            
            # Wait for all specialists to complete their analysis
            design_result, engineering_result, psychology_result = await asyncio.gather(
                design_analysis, engineering_analysis, psychology_analysis
            )
            
            print("\n📋 Specialist Analysis Results:")
            
            print("\n🎮 GAME DESIGN PERSPECTIVE:")
            print(design_result[:400] + "...\n")
            
            print("⚙️ PUZZLE ENGINEERING PERSPECTIVE:")
            print(engineering_result[:400] + "...\n")
            
            print("👥 SOCIAL PSYCHOLOGY PERSPECTIVE:")
            print(psychology_result[:400] + "...\n")
            
            # Create synthesis agent to combine insights
            synthesizer = Agent(
                name="design_synthesizer",
                instruction="Combine multiple expert perspectives into a unified, implementable design solution.",
                server_names=[]
            )
            
            async with synthesizer:
                synthesis_llm = await synthesizer.attach_llm(AnthropicAugmentedLLM)
                
                synthesis_prompt = f"""
                Synthesize these three expert analyses into a complete, implementable design 
                for "The Resonance Chamber" multiplayer puzzle:
                
                GAME DESIGN EXPERT SAYS:
                {design_result}
                
                PUZZLE ENGINEERING EXPERT SAYS:
                {engineering_result}
                
                SOCIAL PSYCHOLOGY EXPERT SAYS:
                {psychology_result}
                
                Create a unified design that incorporates insights from all three experts.
                Include specific mechanics, player roles, success conditions, and implementation details.
                """
                
                final_design = await synthesis_llm.generate_str(
                    message=synthesis_prompt,
                    request_params=RequestParams(maxTokens=1500)
                )
                
                print("🎯 SYNTHESIZED DESIGN SOLUTION:")
                print("-" * 40)
                print(final_design)
                
                print(f"\n✨ This demonstrates:")
                print("• Parallel processing by specialized agents")
                print("• Domain expertise applied to complex problems")
                print("• Multi-perspective analysis and synthesis")
                print("• How MMOIRL can use collaborative AI for sophisticated content creation")

async def main():
    """Run the multiagent demonstrations"""
    print("🤖 Complex Multiagent Functionality Demonstrations")
    print("Showcasing sophisticated agent coordination for MMOIRL")
    print("=" * 70)
    
    try:
        # Run the game master demo
        await demo_game_master_orchestration()
        
        print("\n" + "="*70)
        
        # Run the collaborative specialists demo
        await demo_collaborative_specialists()
        
        print("\n🎉 Multiagent demonstrations completed!")
        print("\n🎯 Key Multiagent Capabilities Shown:")
        print("✅ Orchestrator-Workers pattern for complex coordination")
        print("✅ Multiple specialized agents with distinct expertise")
        print("✅ Parallel agent processing for efficiency")
        print("✅ Dynamic response to user input")
        print("✅ Synthesis of multiple perspectives into unified solutions")
        print("✅ Rich NPC behavior and personality simulation")
        print("\n🚀 These patterns enable MMOIRL to create:")
        print("• Sophisticated multiplayer experiences")
        print("• Dynamic, responsive game worlds")
        print("• Complex problem-solving scenarios")
        print("• Rich character interactions")
        print("• Collaborative content creation")
        
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "gamemaster":
        asyncio.run(demo_game_master_orchestration())
    elif len(sys.argv) > 1 and sys.argv[1] == "specialists":
        asyncio.run(demo_collaborative_specialists())
    else:
        asyncio.run(main())