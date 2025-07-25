#!/bin/bash

# Quick verification test for the changes
# Tests basic functionality without a full deployment

set -e

echo "🧪 Quick Verification Test"
echo "========================="
echo ""

# Test 1: Check Python syntax
echo "1. Checking Python syntax..."
python3 -m py_compile app/services/chat/multiagent_orchestrator.py
python3 -m py_compile app/services/chat/intelligent_router.py
python3 -m py_compile app/services/chat/intelligent_chat.py
python3 -m py_compile app/services/chat/main.py
echo "✅ Python syntax valid"
echo ""

# Test 2: Check imports
echo "2. Checking imports..."
python3 -c "
import sys
sys.path.append('.')
try:
    from app.services.chat.multiagent_orchestrator import MMOIRLMultiagentOrchestrator
    print('✅ Multiagent orchestrator imports successfully')
except Exception as e:
    print(f'❌ Import error: {e}')

try:
    from app.services.chat.intelligent_router import IntelligentRouter
    print('✅ Intelligent router imports successfully')
except Exception as e:
    print(f'❌ Import error: {e}')

try:
    from app.services.chat.intelligent_chat import IntelligentChatService
    print('✅ Intelligent chat imports successfully')
except Exception as e:
    print(f'❌ Import error: {e}')
"
echo ""

# Test 3: Check for obvious issues
echo "3. Checking for common issues..."
echo -n "  Checking for asyncio imports... "
grep -q "import asyncio" app/services/chat/multiagent_orchestrator.py && echo "✅" || echo "❌"

echo -n "  Checking lifespan includes orchestrator init... "
grep -q "multiagent_orchestrator.initialize" app/services/chat/main.py && echo "✅" || echo "❌"

echo -n "  Checking no pattern matching remains... "
! grep -q "simple_patterns" app/services/chat/intelligent_router.py && echo "✅" || echo "❌"

echo -n "  Checking single LLM call setup... "
grep -q "claude-3-5-sonnet" app/services/chat/intelligent_router.py && echo "✅" || echo "❌"

echo ""
echo "4. Test Summary"
echo "==============="
echo "If all checks passed, the code should work correctly."
echo "For full testing, you need to:"
echo "  1. Start the chat service locally or deploy"
echo "  2. Run ./scripts/test-mcp-agent-hot-loading.sh"
echo "  3. Run ./scripts/test-intelligent-routing-performance.sh"