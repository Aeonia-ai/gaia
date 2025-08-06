#!/usr/bin/env python3
"""
Quick test script for KB integration
Tests the KB MCP server independently before full integration
"""

import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_kb_server():
    """Test KB server functionality independently"""
    try:
        # Import the KB server
        from app.services.chat.kb_mcp_server import kb_server, kb_orchestrator
        
        logger.info("🧠 Testing KB MCP Server...")
        
        # Test 1: Check if KB path exists
        kb_path = Path("/Users/jasonasbahr/Development/Aeonia/Vaults/KB")
        if kb_path.exists():
            logger.info(f"✅ KB path exists: {kb_path}")
            
            # List some files
            md_files = list(kb_path.glob("**/*.md"))[:5]
            logger.info(f"✅ Found {len(md_files)} sample markdown files")
            for f in md_files[:3]:
                logger.info(f"   - {f.relative_to(kb_path)}")
        else:
            logger.warning(f"⚠️ KB path not found: {kb_path}")
            return
        
        # Test 2: Direct KB search
        logger.info("\n🔍 Testing KB search...")
        search_result = await kb_server.search_kb(
            query="consciousness",
            limit=5
        )
        
        if search_result["success"]:
            results = search_result["results"]
            logger.info(f"✅ Search successful: {len(results)} results")
            for result in results[:2]:
                logger.info(f"   - {result['relative_path']}: {result['content_excerpt'][:100]}...")
        else:
            logger.error(f"❌ Search failed: {search_result.get('error')}")
        
        # Test 3: File reading
        logger.info("\n📖 Testing file reading...")
        if md_files:
            test_file = md_files[0].relative_to(kb_path)
            file_result = await kb_server.read_kb_file(str(test_file))
            
            if file_result["success"]:
                content_length = len(file_result.get("content", ""))
                logger.info(f"✅ File read successful: {content_length} characters")
                logger.info(f"   Keywords: {file_result.get('keywords', [])[:5]}")
            else:
                logger.error(f"❌ File read failed: {file_result.get('error')}")
        
        # Test 4: Context loading (if gaia context exists)
        logger.info("\n📚 Testing context loading...")
        context_result = await kb_server.load_kos_context("gaia")
        
        if context_result["success"]:
            context = context_result["context"]
            logger.info(f"✅ Context loaded: {context['name']}")
            logger.info(f"   Files: {len(context['files'])}")
            logger.info(f"   Keywords: {context.get('keywords', [])[:5]}")
        else:
            logger.info(f"ℹ️ Context 'gaia' not found (this is normal if KB structure differs)")
        
        # Test 5: Multi-task orchestration
        logger.info("\n⚡ Testing multi-task orchestration...")
        tasks = [
            {"type": "search", "query": "multiagent", "limit": 3},
            {"type": "search", "query": "orchestration", "limit": 3}
        ]
        
        orchestration_result = await kb_orchestrator.delegate_kb_tasks(
            tasks=tasks,
            parallel=True,
            compression_strategy="summary"
        )
        
        if orchestration_result["success"]:
            summary = orchestration_result["results"]["summary"]
            logger.info(f"✅ Multi-task successful: {summary['successful']}/{summary['total_tasks']} tasks")
            findings = orchestration_result["results"].get("key_findings", [])
            for finding in findings[:3]:
                logger.info(f"   - {finding}")
        else:
            logger.error(f"❌ Multi-task failed: {orchestration_result.get('error')}")
        
        logger.info("\n🎉 KB integration test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧠 KB Integration Test")
    print("=" * 50)
    asyncio.run(test_kb_server())