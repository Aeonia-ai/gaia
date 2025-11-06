#!/usr/bin/env python3
"""
Unified Command System Test Script

Tests the GAIA experience command system across multiple protocols:
- `direct`: The refactored /experience/interact HTTP endpoint.
- `chat`: The legacy /api/v0.3/experience/chat HTTP endpoint.
- `websocket`: The /ws/experience WebSocket endpoint.

Usage:
    python tests/manual/test_command_system.py --protocol direct --test basic
"""

import asyncio
import json
import sys
import os
import argparse
import time
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    import requests
    import websockets
    import websockets.protocol
except ImportError:
    print("❌ Required libraries not installed. Please run: pip install requests websockets")
    sys.exit(1)

# --- Configuration ---

# Colors for output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

# --- Test Runner Class ---

class TestRunner:
    def __init__(self, protocol: str, base_url: str, experience: str, test_filter: str):
        self.protocol = protocol
        self.base_url = base_url
        self.experience = experience
        self.test_filter = test_filter
        self.jwt_token = self._get_jwt()
        self.user_id = self._get_user_id_from_jwt()
        self.stats = {"run": 0, "passed": 0, "failed": 0}
        self.websocket = None

    def _get_jwt(self) -> str:
        token_script_path = os.path.join(os.path.dirname(__file__), 'get_test_jwt.py')
        try:
            token = os.popen(f"python3 {token_script_path}").read().strip().split('\n')[-1]
            if not token.startswith("ey"): raise ValueError("Invalid token format")
            return token
        except Exception as e:
            self._print_header("FATAL ERROR")
            print(f"{Colors.RED}❌ Failed to get JWT token: {e}{Colors.NC}")
            sys.exit(1)

    def _get_user_id_from_jwt(self) -> Optional[str]:
        try:
            import jwt
            payload = jwt.decode(self.jwt_token, options={"verify_signature": False})
            return payload.get('sub')
        except ImportError:
            print("PyJWT not installed, cannot decode user_id. Skipping.")
            return None
        except Exception:
            return None

    def _print_header(self, title: str):
        print("\n" + "="*60)
        print(title)
        print("="*60 + "\n")

    def _print_result(self, success: bool, test_name: str, message: str = ""):
        self.stats["run"] += 1
        if success:
            self.stats["passed"] += 1
            print(f"{Colors.GREEN}✅ PASS{Colors.NC}: {test_name}")
            if message: print(f"    {message}")
        else:
            self.stats["failed"] += 1
            print(f"{Colors.RED}❌ FAIL{Colors.NC}: {test_name}")
            if message: print(f"    {message}")

    async def send_command(self, command: str) -> Optional[Dict[str, Any]]:
        print(f"{Colors.BLUE}Command: {command}{Colors.NC}")
        response = None
        try:
            if self.protocol == 'direct':
                response = self._send_direct_command(command)
            elif self.protocol == 'chat':
                response = self._send_chat_command(command)
            elif self.protocol == 'websocket':
                response = await self._send_websocket_command(command)
            else:
                raise ValueError(f"Unknown protocol: {self.protocol}")
            
            print(f"{Colors.YELLOW}Full Response:{Colors.NC}\n{json.dumps(response, indent=2)}")
            return response
        except Exception as e:
            print(f"{Colors.RED}Error sending command: {e}{Colors.NC}")
            return None

    def _send_direct_command(self, command: str) -> Dict[str, Any]:
        url = f"{self.base_url}/experience/interact"
        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        payload = {"message": command, "experience": self.experience}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def _send_chat_command(self, command: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v0.3/experience/chat"
        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        payload = {"message": command, "experience": self.experience, "user_id": self.user_id}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _send_websocket_command(self, command: str) -> Dict[str, Any]:
        if not self.websocket or self.websocket.state == websockets.protocol.State.CLOSED:
            raise ConnectionError("WebSocket is not connected.")
        
        # For this test script, we assume commands are sent as actions
        # A more complex script could handle different message types
        ws_command = {
            "type": "chat",
            "text": command
        }
        await self.websocket.send(json.dumps(ws_command))
        response_str = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
        return json.loads(response_str)

    async def run_test_suite(self, name: str, tests: list):
        if self.test_filter not in ['all', name]:
            return
        self._print_header(f"RUNNING SUITE: {name.upper()}")
        for test_func in tests:
            await test_func()

    async def run(self):
        self._print_header("UNIFIED EXPERIENCE COMMAND TESTING FRAMEWORK")
        print(f"URL: {self.base_url}")
        print(f"Protocol: {self.protocol}")
        print(f"Experience: {self.experience}")
        print(f"User: {self.user_id}")

        # Connect WebSocket if needed
        if self.protocol == 'websocket':
            ws_url = self.base_url.replace("http", "ws") + f"/ws/experience?token={self.jwt_token}"
            try:
                self.websocket = await websockets.connect(ws_url)
                print("\nWebSocket connected successfully.")
                welcome_msg = await self.websocket.recv()
                print(f"Welcome message: {welcome_msg}")
            except Exception as e:
                self._print_header("FATAL ERROR")
                print(f"{Colors.RED}❌ Failed to connect to WebSocket: {e}{Colors.NC}")
                sys.exit(1)

        # Define and run test suites
        await self.run_test_suite("basic", [self.test_look_around, self.test_inventory])
        # Add other suites here...

        # Disconnect WebSocket
        if self.websocket and self.websocket.state != websockets.protocol.State.CLOSED:
            await self.websocket.close()
            print("\nWebSocket connection closed.")

        # Print summary
        self._print_header("TEST SUMMARY")
        print(f"Total tests: {self.stats['run']}")
        print(f"Passed: {Colors.GREEN}{self.stats['passed']}{Colors.NC}")
        print(f"Failed: {Colors.RED}{self.stats['failed']}{Colors.NC}")
        if self.stats['failed'] > 0:
            sys.exit(1)

    # --- Individual Tests ---
    async def test_look_around(self):
        response = await self.send_command("look around")
        self._print_result(response is not None, "Command: look around", "Response received")
        if response:
            self._print_result("narrative" in response, "Response contains narrative")

    async def test_inventory(self):
        response = await self.send_command("check inventory")
        self._print_result(response is not None, "Command: check inventory", "Response received")
        if response:
            self._print_result("narrative" in response, "Response contains narrative")


def main():
    parser = argparse.ArgumentParser(description="Unified Command System Test Script")
    parser.add_argument("--protocol", default="direct", choices=['direct', 'chat', 'websocket'], help="The protocol to test.")
    parser.add_argument("--test", default="all", help="The test suite to run (e.g., basic, items, all)." )
    parser.add_argument("--url", default="http://localhost:8001", help="The base URL for the KB service.")
    parser.add_argument("--experience", default="wylding-woods", help="The experience to test.")
    args = parser.parse_args()

    runner = TestRunner(
        protocol=args.protocol,
        base_url=args.url,
        experience=args.experience,
        test_filter=args.test
    )
    asyncio.run(runner.run())

if __name__ == "__main__":
    main()
