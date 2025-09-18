# CLI Game Interaction Guide

## Playing Games Through GAIA CLI Client

This guide explains how to play interactive games (like Zork) through the GAIA command-line interface, leveraging the revolutionary executable documentation system.

## Quick Start

```bash
# Start interactive game session
python3 scripts/gaia_client.py --env local

# At the prompt, start a game
👤 You: play zork

# Continue with game commands
👤 You: go north
👤 You: take lamp
👤 You: inventory
```

## How It Works

### The Magic: No Special Client Needed

The existing GAIA CLI client (`scripts/gaia_client.py`) works perfectly with games **without any modifications**. This is because:

1. **Games are just conversations** - The CLI already maintains conversation context
2. **State travels with responses** - JSON blocks embed invisibly in messages
3. **Commands are natural language** - No special syntax required

### What Happens Behind the Scenes

When you type a game command:

```
User Input: "go north"
     ↓
CLI sends to /api/v0.3/chat with conversation_id
     ↓
Chat service detects game command
     ↓
Game state extracted from conversation history
     ↓
KB Agent reads Zork markdown files
     ↓
Game logic executes from documentation
     ↓
Response includes narrative + embedded state
     ↓
CLI displays response (state visible but unobtrusive)
```

## Playing Different Games

### Text Adventures (Zork)

```bash
# Start the classic Zork adventure
python3 scripts/gaia_client.py --env local

👤 You: play zork
🤖 Assistant: 🎮 **Zork Adventure**

Welcome to the Great Underground Empire! You are standing in an open field
west of a white house, with a boarded front door. There is a small mailbox here.

---
📍 Location: West Of House | 🏆 Score: 0 | 👣 Moves: 0

```json:game_state
{"game": "zork", "room": "west_of_house", "inventory": [], "score": 0, "moves": 0}
```

👤 You: open mailbox
🤖 Assistant: You open the small mailbox, revealing a leaflet.

---
📍 Location: West Of House | 🏆 Score: 5 | 👣 Moves: 1

```json:game_state
{"game": "zork", "room": "west_of_house", "inventory": ["leaflet"], "score": 5, "moves": 1}
```
```

### Simple Games (Rock Paper Scissors)

```bash
👤 You: play rock paper scissors
🤖 Assistant: Let's play Rock Paper Scissors! Make your choice...

👤 You: rock
🤖 Assistant: You chose rock. I chose scissors. Rock crushes scissors - you win!

```json:game_state
{"game": "rock_paper_scissors", "player_score": 1, "ai_score": 0, "rounds_played": 1}
```
```

## CLI Features That Enhance Gaming

### 1. Session Persistence

The CLI maintains `conversation_id` automatically:
- Your game state persists between commands
- You can continue a game session later
- State is stored in PostgreSQL conversations

### 2. Logging Game Sessions

```bash
# Log your entire game session
python3 scripts/gaia_client.py --env local --log zork_adventure_1

# Session saved to: logs/zork_adventure_1.json
```

The log captures:
- Every command you entered
- Every game response
- All embedded game states
- Perfect for replay or debugging

### 3. Batch Mode for Quick Commands

```bash
# Single command execution
python3 scripts/gaia_client.py --env local --batch "look around"

# Useful for:
- Checking game state
- Quick actions
- Scripted gameplay
```

### 4. Environment Support

```bash
# Play on different environments
python3 scripts/gaia_client.py --env dev    # Development server
python3 scripts/gaia_client.py --env local  # Local testing
```

## Understanding Game Responses

### Response Format

Game responses include three components:

1. **Narrative Text**: The story and descriptions
2. **Status Bar**: Current location, score, moves
3. **JSON State Block**: Machine-readable game state

Example:
```
[Narrative]: You move north into a dark forest. The trees tower above you.

[Status]: 📍 Location: Forest | 🏆 Score: 10 | 👣 Moves: 2

[State Block]: ```json:game_state
{"game": "zork", "room": "forest", ...}
```
```

### Why JSON Blocks Are Visible

The JSON state blocks are **intentionally visible** because:
- **Transparency**: You can see your exact game state
- **Debugging**: Easy to verify game mechanics
- **Learning**: Understand how the game works
- **Cheating Prevention**: State is tamper-evident

## Advanced CLI Commands

### Game-Related Commands

While playing, you can use standard CLI commands:

| Command | Purpose | Example |
|---------|---------|---------|
| `/help` | Show available commands | `/help` |
| `/status` | Check connection and auth | `/status` |
| `/conversations` | List all conversations/games | `/conversations` |
| `/new` | Start new conversation/game | `/new Zork Session 2` |
| `/switch [id]` | Continue previous game | `/switch conv-abc123` |
| `/quit` | Exit CLI (game state saved) | `/quit` |

### Checking Game State

The JSON blocks show your current state:
```json
{
  "game": "zork",
  "room": "cellar",
  "inventory": ["lamp", "sword"],
  "score": 50,
  "moves": 25,
  "flags": {
    "lamp_lit": true,
    "grue_encountered": false
  }
}
```

## Tips for Optimal Gaming

### 1. Use Natural Language

The KB Agent understands variations:
- "go north" = "move north" = "walk north" = "n"
- "take lamp" = "get lamp" = "pick up lamp"
- "look" = "look around" = "examine room"

### 2. Save Your Sessions

```bash
# Start with logging enabled
python3 scripts/gaia_client.py --env local --log epic_adventure

# Your complete adventure is saved for posterity
```

### 3. Continue Games Later

```bash
# List your conversations
/conversations

# Find your game session and switch to it
/switch conv-xyz789

# Continue where you left off
👤 You: where am I?
```

### 4. Experiment Freely

The game state is preserved, so you can:
- Try different approaches
- Explore all options
- The game won't break or lose state

## Technical Details

### How State Persistence Works

1. **First Command**: Creates new conversation with ID
2. **Game Initialization**: Embeds initial state in response
3. **Each Command**: State extracted, updated, re-embedded
4. **Conversation Storage**: PostgreSQL saves all messages with states
5. **Resume Later**: Load conversation, extract latest state

### No Special Protocol Required

The CLI uses standard HTTP/JSON:
```python
# What the CLI sends (simplified)
{
    "message": "go north",
    "conversation_id": "conv-abc123"
}

# What it receives
{
    "response": "You move north...\n```json:game_state\n{...}\n```",
    "conversation_id": "conv-abc123"
}
```

### Performance Characteristics

- **Command Processing**: 2-3 seconds
- **State Extraction**: ~100ms
- **KB Agent Query**: 1-2 seconds
- **Total Response Time**: Acceptable for turn-based games

## Troubleshooting

### Game Not Starting

```bash
# Ensure you're using the right command
👤 You: play zork          # ✓ Correct
👤 You: start zork game    # ✓ Also works
👤 You: zork              # ✗ Too vague
```

### State Not Persisting

Check conversation ID is maintained:
```bash
/status
# Should show: Conversation: conv-abc123
```

### Commands Not Recognized

Be more explicit:
```bash
👤 You: n                  # Might be too short
👤 You: go north          # Better
👤 You: move north        # Also good
```

### Session Lost

Find and restore your game:
```bash
/conversations
# Look for your game session by timestamp
/switch conv-[your-game-id]
```

## The Revolutionary Aspect

What makes this special:

1. **No Game Engine**: The game runs from markdown documentation
2. **No Special Client**: Standard CLI works perfectly
3. **No State Database**: Conversations store everything
4. **No Compilation**: Documentation IS the game

You're not playing a traditional game - you're interacting with **executable documentation** that runs through AI interpretation!

## Examples of Complete Game Sessions

### Short Session

```bash
$ python3 scripts/gaia_client.py --env local --log quick_game

👤 You: play rock paper scissors
🤖 Assistant: Let's play! Choose rock, paper, or scissors.

👤 You: rock
🤖 Assistant: You chose rock. I chose paper. Paper covers rock - I win!

👤 You: play again, scissors this time
🤖 Assistant: You chose scissors. I chose rock. Rock crushes scissors - I win again!

👤 You: /quit
👋 Goodbye!

# Session saved to logs/quick_game.json
```

### Adventure Session

```bash
$ python3 scripts/gaia_client.py --env local

👤 You: I want to play a text adventure
🤖 Assistant: Starting Zork adventure...

👤 You: look around
🤖 Assistant: You are west of a white house. There's a mailbox here.

👤 You: open the mailbox
🤖 Assistant: Opening the mailbox reveals a leaflet.

👤 You: read leaflet
🤖 Assistant: "WELCOME TO ZORK! You are about to experience an adventure..."

👤 You: go north
🤖 Assistant: You are in a forest. A path leads north and south.

# Game continues with full state preservation...
```

## Conclusion

The GAIA CLI client proves that our game system is truly revolutionary:

- **Zero Modifications Needed**: Existing CLI works perfectly
- **Complete Game Experience**: Full games playable today
- **State Management Invisible**: JSON blocks don't interfere
- **Universal Compatibility**: Any client that can chat can play

This isn't just a game system - it's proof that **documentation can be directly executable** through AI interpretation. The future of gaming (and software) is here, and it works through your terminal!