#!/usr/bin/env python3
"""
Test script demonstrating markdown-based agent command execution.

This shows the DIFFERENCE between:
1. /agent/interpret - Loads markdown, LLM interprets rules
2. /game/command - Hardcoded Python, no markdown loading
"""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}


def agent_interpret(query, context_path, mode="decision"):
    """Test markdown-based agent interpretation."""
    print(f"\n{'='*60}")
    print(f"TESTING: /agent/interpret (Markdown-Based)")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"Context: {context_path}")
    print(f"Mode: {mode}")
    print(f"-"*60)

    response = requests.post(
        f"{BASE_URL}/agent/interpret",
        headers=HEADERS,
        json={
            "query": query,
            "context_path": context_path,
            "mode": mode
        },
        timeout=30
    )

    result = response.json()

    if response.status_code == 200:
        print(f"✅ SUCCESS")
        print(f"Response time: {response.elapsed.total_seconds():.2f}s")
        print(f"\nMarkdown files loaded: {result['result']['context_files']}")
        print(f"Model used: {result['result']['model_used']}")
        print(f"\nInterpretation:")
        print(result['result']['interpretation'][:500] + "...")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(json.dumps(result, indent=2))

    return result


def game_command(command, experience):
    """Test hardcoded game command (for comparison)."""
    print(f"\n{'='*60}")
    print(f"TESTING: /game/command (Hardcoded Python)")
    print(f"{'='*60}")
    print(f"Command: {command}")
    print(f"Experience: {experience}")
    print(f"-"*60)

    response = requests.post(
        f"{BASE_URL}/game/command",
        headers=HEADERS,
        json={
            "command": command,
            "experience": experience,
            "user_context": {
                "role": "player",
                "user_id": "player@test.com"
            }
        },
        timeout=30
    )

    result = response.json()

    if response.status_code == 200:
        print(f"✅ SUCCESS")
        print(f"Response time: {response.elapsed.total_seconds():.2f}s")
        print(f"\nNarrative: {result.get('narrative', 'N/A')[:300]}...")
        print(f"\nMarkdown loaded? NO - Uses hardcoded Python logic")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(json.dumps(result, indent=2))

    return result


def agent_workflow(workflow_path, parameters=None):
    """Test workflow execution from markdown."""
    print(f"\n{'='*60}")
    print(f"TESTING: /agent/workflow (Markdown Workflow)")
    print(f"{'='*60}")
    print(f"Workflow: {workflow_path}")
    print(f"Parameters: {parameters}")
    print(f"-"*60)

    response = requests.post(
        f"{BASE_URL}/agent/workflow",
        headers=HEADERS,
        json={
            "workflow_path": workflow_path,
            "parameters": parameters or {}
        },
        timeout=30
    )

    result = response.json()

    if response.status_code == 200:
        print(f"✅ SUCCESS")
        print(f"Response time: {response.elapsed.total_seconds():.2f}s")
        print(f"\nResult:")
        print(json.dumps(result['result'], indent=2)[:500] + "...")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(json.dumps(result, indent=2))

    return result


def agent_validate(action, rules_path, context=None):
    """Test action validation against markdown rules."""
    print(f"\n{'='*60}")
    print(f"TESTING: /agent/validate (Markdown Rules)")
    print(f"{'='*60}")
    print(f"Action: {action}")
    print(f"Rules: {rules_path}")
    print(f"-"*60)

    response = requests.post(
        f"{BASE_URL}/agent/validate",
        headers=HEADERS,
        json={
            "action": action,
            "rules_path": rules_path,
            "context": context or {}
        },
        timeout=30
    )

    result = response.json()

    if response.status_code == 200:
        print(f"✅ SUCCESS")
        print(f"Response time: {response.elapsed.total_seconds():.2f}s")
        print(f"\nValidation Result:")
        print(json.dumps(result['result'], indent=2)[:500] + "...")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║  Markdown Command Execution Test Suite                      ║
║  Comparing markdown-based vs hardcoded approaches            ║
╚══════════════════════════════════════════════════════════════╝
""")

    # Test 1: Markdown-based rule interpretation
    # This LOADS markdown files from rock-paper-scissors
    try:
        agent_interpret(
            query="Can I play rock in this game?",
            context_path="experiences/rock-paper-scissors",
            mode="decision"
        )
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")

    # Test 2: Hardcoded game command (for comparison)
    # This does NOT load markdown from wylding-woods
    try:
        game_command(
            command="look around",
            experience="wylding-woods"
        )
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")

    # Test 3: Validate action against markdown rules
    try:
        agent_validate(
            action="play scissors when opponent played rock",
            rules_path="experiences/rock-paper-scissors/rules",
            context={"player_choice": "scissors", "opponent_choice": "rock"}
        )
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")

    print(f"\n{'='*60}")
    print("KEY FINDINGS:")
    print("="*60)
    print("""
1. /agent/interpret - ✅ LOADS MARKDOWN from KB
   - Reads .md files recursively
   - LLM interprets content as rules
   - Returns narrative based on markdown
   - Used by: rock-paper-scissors

2. /game/command - ❌ DOES NOT LOAD MARKDOWN
   - Hardcoded Python action routing
   - Haiku parses command to action type
   - Returns hardcoded narrative strings
   - Used by: wylding-woods

3. /agent/workflow - ✅ LOADS MARKDOWN procedures
   - Step-by-step workflows from markdown
   - Parameterizable execution

4. /agent/validate - ✅ LOADS MARKDOWN rules
   - Validates actions against markdown rules
   - Returns validation result + reasoning
""")
