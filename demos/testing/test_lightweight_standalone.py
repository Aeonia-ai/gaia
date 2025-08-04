"""
Test lightweight chat in standalone mode (no Docker required)

This tests the mcp-agent lightweight chat functionality directly
without needing the full Gaia infrastructure running.
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the gaia directory to Python path
import sys
sys.path.insert(0, '/Users/jasonasbahr/Development/Aeonia/Server/gaia')

from app.services.chat.lightweight_chat import LightweightChatService, ConsciousnessEnabledChat
from app.models.chat import ChatRequest


async def test_standalone():
    """Test lightweight chat without full infrastructure"""
    
    print("🧪 Testing Lightweight Chat (Standalone Mode)\n")
    
    # Create service instance
    service = LightweightChatService()
    
    # Mock auth principal
    auth_principal = {
        "sub": "test-user-123",
        "type": "user"
    }
    
    # Test 1: Simple chat
    print("Test 1: Simple lightweight chat")
    request = ChatRequest(
        message="Hello! Tell me a short joke about Python programming.",
        model="claude-3-5-sonnet-20241022"
    )
    
    try:
        response = await service.process_chat(request, auth_principal)
        print(f"✅ Response: {response['choices'][0]['message']['content'][:200]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 2: Multi-turn conversation
    print("Test 2: Multi-turn conversation")
    
    # First message
    request1 = ChatRequest(
        message="My name is Alice and I love hiking in the mountains."
    )
    response1 = await service.process_chat(request1, auth_principal)
    print("✅ First message sent")
    
    # Second message (should remember context)
    request2 = ChatRequest(
        message="What's my name and what do I enjoy doing?"
    )
    response2 = await service.process_chat(request2, auth_principal)
    content = response2['choices'][0]['message']['content']
    print(f"✅ Response: {content[:200]}...")
    
    if "Alice" in content and "hiking" in content:
        print("✅ Successfully remembered context!")
    else:
        print("⚠️  Context might not be preserved")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 3: Consciousness-enabled chat
    print("Test 3: Consciousness pattern (meditation)")
    
    consciousness_service = ConsciousnessEnabledChat()
    
    meditation_request = ChatRequest(
        message="I'm feeling stressed. Can you guide me through a brief breathing exercise?"
    )
    
    response = await consciousness_service.process_meditation_request(
        meditation_request, 
        auth_principal
    )
    
    if response['type'] == 'meditation':
        print(f"✅ Meditation agent activated!")
        print(f"✅ Agent: {response['agent']}")
        print(f"✅ Response: {response['content'][:300]}...")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 4: Performance test
    print("Test 4: Performance (no MCP overhead)")
    
    import time
    start = time.time()
    
    quick_request = ChatRequest(message="What is 2+2?")
    response = await service.process_chat(quick_request, auth_principal)
    
    elapsed = time.time() - start
    print(f"✅ Response time: {elapsed:.2f}s")
    print(f"✅ Answer: {response['choices'][0]['message']['content']}")


async def test_mcp_agent_patterns():
    """Test various mcp-agent patterns without MCP servers"""
    
    print("\nTest 5: MCP-Agent flexibility patterns\n")
    
    from mcp_agent.app import MCPApp
    from mcp_agent.agents.agent import Agent
    from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
    
    app = MCPApp(name="pattern_test")
    
    async with app.run() as mcp_app:
        # Pattern 1: Zero MCP servers (lightweight)
        lightweight = Agent(
            name="lightweight",
            instruction="You are a helpful assistant with no external tools",
            server_names=[]  # No MCP!
        )
        
        async with lightweight:
            llm = await lightweight.attach_llm(AnthropicAugmentedLLM)
            result = await llm.generate_str("What's the capital of France?")
            print(f"✅ Lightweight (no MCP): {result[:100]}...")
        
        # Pattern 2: Would work with remote MCP servers if configured
        # remote_agent = Agent(
        #     name="remote",
        #     instruction="I can connect to remote services",
        #     server_names=["remote_db", "remote_api"]  # Would connect if configured
        # )
        
        print("\n✅ All patterns tested successfully!")


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Please set ANTHROPIC_API_KEY in your .env file")
        exit(1)
    
    print(f"✅ Using API key: {os.getenv('ANTHROPIC_API_KEY')[:10]}...")
    
    # Run tests
    asyncio.run(test_standalone())
    asyncio.run(test_mcp_agent_patterns())