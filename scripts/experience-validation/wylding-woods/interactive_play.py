#!/usr/bin/env python3
"""
Interactive gameplay for Wylding Woods.

This script lets you play the game with natural language commands.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

# Game state
current_waypoint = "waypoint_28a_store"
current_sublocation = "entrance"
user_id = "jason@aeonia.ai"

def send_command(command):
    """Send a game command and display the response."""
    payload = {
        "command": command,
        "experience": "wylding-woods",
        "user_context": {
            "user_id": user_id,
            "waypoint": current_waypoint,
            "sublocation": current_sublocation,
            "role": "player"
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/game/command",
            headers=HEADERS,
            json=payload,
            timeout=30
        )

        result = response.json()

        # Display narrative
        if result.get("narrative"):
            print(f"\n{result['narrative']}")

        # Display actions
        if result.get("actions"):
            print(f"\n📋 Actions:")
            for action in result["actions"]:
                print(f"   • {action.get('type', 'unknown')}")

        # Display state changes
        if result.get("state_changes"):
            print(f"\n🔄 Updates:")
            for key, value in result["state_changes"].items():
                if key == "relationship":
                    rel = value
                    print(f"   • {rel.get('npc')}: Trust {rel.get('trust')}/100, "
                          f"Conversations: {rel.get('conversations')}")
                elif key == "inventory":
                    items = value.get("items", [])
                    print(f"   • Inventory: {len(items)} item(s)")
                else:
                    print(f"   • {key}: {value}")

        # Check for errors
        if not result.get("success"):
            error = result.get("error", {})
            print(f"\n⚠️  {error.get('message', 'Unknown error')}")

        return result

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {"success": False}

def show_help():
    """Display available commands."""
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                    WYLDING WOODS - COMMANDS                           ║
╚═══════════════════════════════════════════════════════════════════════╝

🔍 EXPLORATION:
   • look around
   • examine shelf_1
   • look at the fairy door

📦 INVENTORY:
   • check inventory
   • what am I carrying?

✋ COLLECT ITEMS:
   • pick up the dream bottle
   • take the glowing bottle
   • grab that bottle

💬 NPC INTERACTION:
   • talk to Louisa
   • ask Louisa about the dream bottles
   • hello Louisa

🎯 QUEST:
   • return the dream bottle to the fairy door
   • give bottle to Louisa

📍 CHANGE LOCATION:
   • /goto <sublocation>  (e.g., /goto counter)
   • /waypoint <id>       (e.g., /waypoint waypoint_28a)

🛠️ ADMIN (requires admin role):
   • @list items
   • @inspect louisa
   • @reset instance 2 CONFIRM

⚙️ SYSTEM:
   • /help    - Show this help
   • /status  - Show current location
   • /quit    - Exit game

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

def show_status():
    """Display current game state."""
    print(f"""
╔═══════════════════════════════════════════════════════════════════════╗
║                         CURRENT STATUS                                ║
╚═══════════════════════════════════════════════════════════════════════╝

👤 Player: {user_id}
📍 Location: {current_waypoint}/{current_sublocation}
🎮 Experience: wylding-woods

To see your inventory: "check inventory"
To change location: /goto <sublocation>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

def main():
    """Run interactive gameplay."""
    global current_sublocation, current_waypoint

    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                  WYLDING WOODS - INTERACTIVE GAME                     ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")

    print("\n🌲 Welcome to the Wylding Woods!")
    print("   You are at Woander's Mystical Store.\n")
    print("   Type /help for commands, /quit to exit.\n")

    # Show initial location
    send_command("look around")

    # Game loop
    while True:
        try:
            command = input("\n🎮 > ").strip()

            if not command:
                continue

            # System commands
            if command.lower() == "/quit":
                print("\n👋 Thanks for playing Wylding Woods!")
                break
            elif command.lower() == "/help":
                show_help()
                continue
            elif command.lower() == "/status":
                show_status()
                continue
            elif command.startswith("/goto "):
                new_sublocation = command[6:].strip()
                current_sublocation = new_sublocation
                print(f"📍 Moved to: {current_waypoint}/{current_sublocation}")
                send_command("look around")
                continue
            elif command.startswith("/waypoint "):
                new_waypoint = command[10:].strip()
                current_waypoint = new_waypoint
                current_sublocation = "center"
                print(f"📍 Teleported to: {current_waypoint}")
                send_command("look around")
                continue

            # Send game command
            send_command(command)

        except KeyboardInterrupt:
            print("\n\n👋 Thanks for playing Wylding Woods!")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()
