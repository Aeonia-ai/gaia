#!/usr/bin/env python3
"""
Parameterized Quest Flow Test Script

Tests complete quest flow with proper logging and Unity AOI verification.
Writes results to file instead of console for better debugging.

Usage:
    python3 test_quest_flow.py --experience wylding-woods --output test-results.log
    python3 test_quest_flow.py --reset --verify-aoi
"""

import asyncio
import websockets
import json
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import subprocess


def get_test_jwt() -> str:
    """Get JWT token by running get_test_jwt.py script."""
    root_dir = Path(__file__).parent.parent.parent
    result = subprocess.run(
        ["python3", str(root_dir / "tests/manual/get_test_jwt.py")],
        capture_output=True,
        text=True,
        cwd=root_dir
    )
    if result.returncode != 0:
        raise Exception(f"Failed to get JWT token: {result.stderr}")

    # Extract token from stdout (last line)
    return result.stdout.strip().split('\n')[-1]


class QuestTestRunner:
    """Test runner for quest flow with logging and verification."""

    def __init__(
        self,
        experience_id: str = "wylding-woods",
        ws_url: str = "ws://localhost:8001",
        output_file: Optional[str] = None,
        verify_aoi: bool = False
    ):
        self.experience_id = experience_id
        self.ws_url = ws_url
        self.output_file = output_file or f"test-{experience_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        self.verify_aoi = verify_aoi
        self.log_buffer: List[str] = []

    def log(self, message: str, level: str = "INFO"):
        """Log message to buffer and optionally console."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] {level:5s} | {message}"
        self.log_buffer.append(log_line)
        print(log_line)  # Also print to console

    def write_log_file(self):
        """Write log buffer to file."""
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open('w') as f:
            f.write(f"Quest Flow Test Results\n")
            f.write(f"Experience: {self.experience_id}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            f.write("\n".join(self.log_buffer))

        self.log(f"📄 Log written to: {output_path}", "INFO")

    async def wait_for_action_response(self, ws) -> Dict[str, Any]:
        """Helper to read messages until we get action_response."""
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            if msg.get("type") == "action_response":
                return msg
            elif msg.get("type") == "world_update":
                self.log(f"  Received world_update event", "DEBUG")

    async def verify_aoi_structure(self, aoi_msg: Dict[str, Any]) -> bool:
        """Verify AOI message matches Unity v0.5 requirements."""
        self.log("🔍 Verifying AOI structure for Unity v0.5...", "INFO")

        errors = []

        # Check required top-level fields
        required_fields = ["type", "timestamp", "snapshot_version", "zone", "areas", "player"]
        for field in required_fields:
            if field not in aoi_msg:
                errors.append(f"Missing required field: {field}")

        # Check zone structure
        zone = aoi_msg.get("zone", {})
        zone_fields = ["id", "name", "description", "gps"]
        for field in zone_fields:
            if field not in zone:
                errors.append(f"Zone missing field: {field}")

        # Check GPS structure
        gps = zone.get("gps", {})
        if "lat" not in gps or "lng" not in gps:
            errors.append("GPS missing lat/lng coordinates")

        # Check areas contain spots (v0.5 requirement)
        areas = aoi_msg.get("areas", {})
        for area_id, area_data in areas.items():
            if "spots" not in area_data:
                errors.append(f"Area '{area_id}' missing 'spots' dictionary (v0.5 requirement)")
            else:
                # Check spot structure
                spots = area_data["spots"]
                for spot_id, spot_data in spots.items():
                    if "items" not in spot_data or "npcs" not in spot_data:
                        errors.append(f"Spot '{spot_id}' missing items/npcs arrays")

                    # Verify items have required fields
                    for item in spot_data.get("items", []):
                        item_fields = ["instance_id", "template_id", "semantic_name", "collectible", "visible"]
                        for field in item_fields:
                            if field not in item:
                                errors.append(f"Item in '{spot_id}' missing field: {field}")

        # Check player state
        player = aoi_msg.get("player", {})
        player_fields = ["current_location", "inventory"]
        for field in player_fields:
            if field not in player:
                errors.append(f"Player missing field: {field}")

        if errors:
            self.log("❌ AOI structure validation FAILED:", "ERROR")
            for error in errors:
                self.log(f"   - {error}", "ERROR")
            return False
        else:
            self.log("✅ AOI structure matches Unity v0.5 requirements", "INFO")

            # Log structure summary
            self.log(f"   Zone: {zone.get('name')} ({zone.get('id')})", "INFO")
            self.log(f"   GPS: {gps.get('lat')}, {gps.get('lng')}", "INFO")
            self.log(f"   Areas: {len(areas)}", "INFO")

            total_spots = sum(len(area.get("spots", {})) for area in areas.values())
            total_items = sum(
                len(spot.get("items", []))
                for area in areas.values()
                for spot in area.get("spots", {}).values()
            )
            self.log(f"   Total Spots: {total_spots}", "INFO")
            self.log(f"   Total Items: {total_items}", "INFO")

            return True

    async def test_reset(self, ws) -> bool:
        """Test @reset experience command."""
        self.log("🔄 Testing @reset experience command...", "INFO")

        # Step 1: Preview (without CONFIRM)
        await ws.send(json.dumps({
            "type": "action",
            "action": "@reset experience"
        }))

        resp = await self.wait_for_action_response(ws)
        if resp.get("success"):
            self.log("   ❌ Reset should require CONFIRM", "ERROR")
            return False

        self.log("   ✅ Preview mode works (confirmation required)", "INFO")

        # Step 2: Execute (with CONFIRM)
        await ws.send(json.dumps({
            "type": "action",
            "action": "@reset experience CONFIRM"
        }))

        resp = await self.wait_for_action_response(ws)
        if not resp.get("success"):
            self.log(f"   ❌ Reset failed: {resp.get('message')}", "ERROR")
            return False

        self.log("   ✅ Reset executed successfully", "INFO")
        return True

    async def test_collect_all_bottles(self, ws) -> bool:
        """Collect all 4 dream bottles."""
        self.log("📦 Collecting bottles...", "INFO")

        bottles = ["bottle_mystery", "bottle_energy", "bottle_joy", "bottle_nature"]

        for i, bottle in enumerate(bottles, 1):
            await ws.send(json.dumps({
                "type": "action",
                "action": "collect_item",
                "instance_id": bottle
            }))

            resp = await self.wait_for_action_response(ws)
            if resp.get("success"):
                self.log(f"   {i}/4 ✅ {bottle}", "INFO")
            else:
                self.log(f"   {i}/4 ❌ {bottle}: {resp.get('message')}", "ERROR")
                return False

        return True

    async def test_give_bottles_to_louisa(self, ws) -> bool:
        """Give all bottles to Louisa and verify quest progression."""
        self.log("🎁 Giving bottles to Louisa...", "INFO")

        bottles = ["bottle_mystery", "bottle_energy", "bottle_joy", "bottle_nature"]

        for i, bottle in enumerate(bottles, 1):
            await ws.send(json.dumps({
                "type": "action",
                "action": "give_item",
                "instance_id": bottle,
                "target_npc_id": "louisa"
            }))

            resp = await self.wait_for_action_response(ws)
            if not resp.get("success"):
                self.log(f"   ❌ Bottle {i}/4 ({bottle}): {resp.get('message')}", "ERROR")
                return False

            # Extract dialogue
            dialogue = resp.get("message", "")
            if "Louisa:" in dialogue:
                dialogue = dialogue.split("Louisa:")[1].strip()

            self.log(f"   {i}/4 Louisa: {dialogue[:60]}...", "INFO")

            # Check quest progress
            metadata = resp.get("metadata", {})
            quest = metadata.get("hook_result", {}).get("quest_updates", {})

            if quest:
                collected = quest.get("bottles_collected")
                complete = quest.get("quest_complete", False)

                if complete:
                    self.log(f"        ✨ QUEST COMPLETE! ✨", "INFO")
                    return True
                else:
                    self.log(f"        Progress: {collected}/4 bottles", "INFO")

        self.log("   ❌ Quest not completed after all bottles given", "ERROR")
        return False

    async def run_full_test(self) -> bool:
        """Run complete quest flow test."""
        self.log("╔═══════════════════════════════════════════════╗", "INFO")
        self.log("║   Louisa Dream Bottle Quest - Full Test      ║", "INFO")
        self.log("╚═══════════════════════════════════════════════╝", "INFO")
        self.log("", "INFO")

        try:
            # Get JWT token
            self.log("🔐 Getting JWT token...", "INFO")
            jwt_token = get_test_jwt()
            self.log("   ✅ Token obtained", "INFO")

            # Connect to WebSocket
            ws_url = f"{self.ws_url}/ws/experience?token={jwt_token}&experience={self.experience_id}"
            self.log(f"🔌 Connecting to {self.ws_url}...", "INFO")

            async with websockets.connect(ws_url) as ws:
                # Read welcome message
                welcome = json.loads(await ws.recv())
                self.log(f"   ✅ Connected (type: {welcome.get('type')})", "INFO")

                # Test reset first
                if not await self.test_reset(ws):
                    return False

                self.log("", "INFO")

                # Reconnect after reset (player view was cleared)
                self.log("🔌 Reconnecting after reset...", "INFO")

            async with websockets.connect(ws_url) as ws:
                welcome = json.loads(await ws.recv())
                self.log("   ✅ Reconnected", "INFO")

                # Navigate to main_room
                self.log("📍 Navigating to main_room...", "INFO")
                await ws.send(json.dumps({"type": "action", "action": "go", "destination": "main_room"}))
                nav_resp = await self.wait_for_action_response(ws)

                if not nav_resp.get("success"):
                    self.log(f"   ❌ Navigation failed: {nav_resp.get('message')}", "ERROR")
                    return False

                self.log("   ✅ Arrived at main_room", "INFO")
                self.log("", "INFO")

                # Verify AOI if requested
                if self.verify_aoi and "initial_state" in nav_resp:
                    await self.verify_aoi_structure(nav_resp["initial_state"])
                    self.log("", "INFO")

                # Collect bottles
                if not await self.test_collect_all_bottles(ws):
                    return False

                self.log("", "INFO")

                # Give bottles to Louisa
                if not await self.test_give_bottles_to_louisa(ws):
                    return False

                self.log("", "INFO")
                self.log("✅ ALL TESTS PASSED! Quest flow complete!", "INFO")
                return True

        except Exception as e:
            self.log(f"❌ Test failed with exception: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
        finally:
            self.write_log_file()


def main():
    parser = argparse.ArgumentParser(description="Test quest flow with proper logging")
    parser.add_argument("--experience", default="wylding-woods", help="Experience ID to test")
    parser.add_argument("--ws-url", default="ws://localhost:8001", help="WebSocket URL")
    parser.add_argument("--output", help="Output log file path")
    parser.add_argument("--verify-aoi", action="store_true", help="Verify AOI structure for Unity")

    args = parser.parse_args()

    runner = QuestTestRunner(
        experience_id=args.experience,
        ws_url=args.ws_url,
        output_file=args.output,
        verify_aoi=args.verify_aoi
    )

    success = asyncio.run(runner.run_full_test())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
