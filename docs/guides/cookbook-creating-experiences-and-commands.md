# Developer & Content Creator Cookbook

**Purpose**: This is a practical, step-by-step guide for developers and content creators to extend the GAIA "dynamic experiences" platform. It provides actionable instructions for common tasks like creating new experiences and adding game commands.

---

## Creating a New Experience

This guide shows how to create a new experience by using an existing one as a template. We'll create a single-player version of `wylding-woods` as an example.

### Step 1: Copy an Existing Experience

The easiest way to start is to copy an existing experience. All file operations should be done inside the `kb-service` container, as this reflects the true source of the knowledge base content.

```bash
# Get the container ID
docker compose ps -q kb-service

# Copy the directory inside the container
docker exec [container_id] cp -r /kb/experiences/wylding-woods /kb/experiences/my-new-experience
```

### Step 2: Modify `config.json`

This is the most critical step. The `config.json` file defines your experience's identity and its architectural model.

**File:** `/kb/experiences/my-new-experience/config.json`

Modify the following fields:
1.  **`id`**: Change this to match your new directory name (e.g., `"my-new-experience"`).
2.  **`name`**: Give your experience a human-readable name (e.g., `"My New Adventure"`).
3.  **`state.model`**: This is the key architectural decision.
    *   `"shared"`: For multiplayer experiences where all players interact with the same world.
    *   `"isolated"`: For single-player experiences where each player gets their own private copy of the world.

**Example Change:**
```diff
-  "id": "wylding-woods",
-  "name": "The Wylding Woods",
-  "model": "shared"
+  "id": "my-new-experience",
+  "name": "My New Adventure",
+  "model": "isolated"
```

### Step 3: Adapt the State File

The state model you chose in `config.json` determines what you do with the state file.

*   **If you chose `"shared"`:**
    *   Keep the file `state/world.json`. This file is the canonical, shared world that all players will interact with.

*   **If you chose `"isolated"`:**
    *   You must rename `state/world.json` to `state/world.template.json`.
    *   This file now serves as a blueprint. Every new player will get their own personal copy of this template.

```bash
# If you chose the 'isolated' model
docker exec [container_id] mv /kb/experiences/my-new-experience/state/world.json /kb/experiences/my-new-experience/state/world.template.json
```

### Step 4: Restart and Test

To ensure the `kb-service` recognizes the new experience and its configuration, a restart is the most reliable method.

```bash
docker compose restart kb-service
```

You can now test your new experience using the test scripts or the interactive CLI.

---

## Adding a New Player Command

Player commands use the "Content-First" workflow. You define the logic in Markdown, and the LLM interprets it at runtime.

### Step 1: Create the Markdown File

Create a new file in the `game-logic/` directory of your experience. The filename should be the primary name of the command.

**File:** `/kb/experiences/my-new-experience/game-logic/drop.md`

### Step 2: Define the Frontmatter

The frontmatter tells the system how to use your command.

```yaml
---
command: drop
aliases: [leave, place, put down]
description: Drop an item from your inventory into the current location.
requires_location: true
requires_target: true
---
```

*   **`command`**: The primary name used for routing.
*   **`aliases`**: Synonyms the LLM can use to detect intent.

### Step 3: Write the Execution Logic for the LLM

The rest of the markdown file is a detailed set of instructions for the LLM. You must tell it the command's intent, how to access state, what logic to execute, and what the response should look like.

**Example for `drop.md`:**
```markdown
# Drop Command

## Intent Detection
This command handles players wanting to remove an item from their inventory and place it in the world.

## Execution Logic
1.  **Parse Target:** Identify the item the player wants to drop from their message.
2.  **Check Inventory:** Verify the player actually has this item in their `player.inventory`.
3.  **Update State:**
    *   Remove the item from the `player.inventory` array.
    *   Add the item to the `world_state.locations[current_location].items` array.
4.  **Generate Narrative:** Describe the action of dropping the item.

## Response Format
Provide examples of the JSON the LLM should return for both success and failure cases.

### Success Response
```json
{
  "success": true,
  "narrative": "You drop the brass lantern on the ground.",
  "state_updates": {
    "player": { "path": "player.inventory", "operation": "remove", "item_id": "lantern_1" },
    "world": { "path": "locations.west_of_house.items", "operation": "add", "item": { ... } }
  },
  "available_actions": ["look around", "take brass lantern"]
}
```
```

---

## Adding a New Admin Command

Admin commands are for direct, fast, deterministic world manipulation. They use a hybrid "Content-and-Code" approach.

### Step 1: Create the Markdown File

Create a file in the `admin-logic/` directory, prefixed with `@`.

**File:** `/kb/experiences/my-new-experience/admin-logic/@spawn.md`

The markdown file serves for **discovery and documentation**, but the core logic is in Python for speed.

```yaml
---
command: @spawn
description: Spawn a new instance of an item or NPC from a template.
requires_admin: true
---

# @spawn Command
(Documentation on syntax, parameters, and examples)
```

### Step 2: Add the Core Logic in Python

For performance, the actual logic for admin commands is implemented in Python.

**File:** `app/services/kb/kb_agent.py` (or a dedicated admin handler)

You would add a new handler method, for example:

```python
async def _admin_spawn(self, args: List[str], experience: str, user_context: Dict) -> Dict:
    # 1. Parse arguments (e.g., item_template, location)
    if len(args) < 2:
        return {"success": False, "narrative": "Usage: @spawn <template> <location>"}

    template_name = args[0]
    location_str = args[1]

    # 2. Perform direct file operations
    #    - Read the template file
    #    - Create a new instance file
    #    - Update the manifest.json
    #    - All with atomic file writes

    # 3. Return a direct, deterministic response
    return {"success": True, "narrative": f"Successfully spawned {template_name} at {location_str}."}
```

This hybrid approach gives you the discoverability of markdown with the speed and reliability of direct Python execution for administrative tasks.

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

The core claims in this document have been verified against the source code.

-   **✅ Creating a New Experience (Sections 1-4):**
    *   **Claim:** The `state.model` in `config.json` ("shared" vs. "isolated") controls how world state is handled.
    *   **Code Reference:** `app/services/kb/unified_state_manager.py` (lines 501-541, `get_world_state` method).
    *   **Verification:** Confirmed that the `get_world_state` method checks the `state_model` from the loaded config. For the "shared" model, it reads `experiences/{exp}/state/world.json`. For the "isolated" model, it reads the player-specific `players/{user}/{exp}/view.json`.

-   **⚠️ Discrepancy in "Creating a New Experience":**
    *   **Claim (Step 3):** For an "isolated" model, you must rename `state/world.json` to `state/world.template.json`.
    *   **Code Reference:** `app/services/kb/unified_state_manager.py` (lines 968-995, `_copy_world_template_for_player` method).
    *   **Verification:** The `_copy_world_template_for_player` method, which is called when bootstrapping a player for an "isolated" experience, loads the template from the path specified in `config["bootstrap"]["world_template_path"]`. This path defaults to `"state/world.json"` (line 270).
    *   **Conclusion:** The cookbook's instruction to rename the file to `world.template.json` is incomplete. A user following this guide would also need to **manually update `config.json`** to change `world_template_path` to `"state/world.template.json"`. Without this change, the system would fail to find the template file.

-   **✅ Adding a New Player Command (Sections 1-3):**
    *   **Claim:** Player commands are defined in markdown files in the `game-logic/` directory and are interpreted by an LLM at runtime.
    *   **Code Reference:** `app/services/kb/kb_agent.py` (lines 953-1049, `_discover_available_commands` and lines 1155-1268, `_execute_markdown_command`).
    *   **Verification:** Confirmed that the `_discover_available_commands` method scans the `game-logic/` directory for `.md` files and parses their frontmatter. The `_execute_markdown_command` method then uses this markdown content to guide the LLM in executing the command.

-   **✅ Adding a New Admin Command (Sections 1-2):**
    *   **Claim:** Admin commands are prefixed with `@`, defined in `admin-logic/`, and executed by dedicated Python code for performance.
    *   **Code Reference:** `app/services/kb/kb_agent.py` (lines 859-871, `process_llm_command` and lines 1805-1855, `_execute_admin_command`).
    *   **Verification:** Confirmed that `process_llm_command` checks for the `@` prefix and routes the command to `_execute_admin_command`. This method then calls specific Python handlers (e.g., `_admin_spawn`), bypassing the LLM execution path. This matches the described hybrid "Content-and-Code" approach.
