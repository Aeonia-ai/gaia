# 000 - MVP File-Based Design

**Status:** Proposed
**Version:** 1.0
**Purpose:** This document describes the design of the file-based MVP for the Dynamic Experiences feature. This design is intended to be a simple, zero-infrastructure solution that can be implemented quickly.

## 1. Core Principle: Templates vs. Instances

The fundamental principle of the system is the separation between **templates** and **instances**:

*   **Templates:** The "design-time" definition of a game element (e.g., the character of Louisa, the properties of a sword). These are stored as Markdown files in the Knowledge Base (KB).
*   **Instances:** The "live" state of an element in the game world (e.g., a specific instance of Louisa at a specific location, a specific sword in a player's inventory). In the file-based MVP, these are stored as JSON files in the KB.

## 2. Directory Structure

The following directory structure will be used to store the templates, instances, and player progress in the KB:

```
kb/
├── experiences/
│   └── wylding-woods/
│       ├── +wylding-woods.md  (The index file for this experience)
│       ├── templates/         (The "design time" templates)
│       │   ├── npcs/
│       │   │   └── louisa.md
│       │   └── items/
│       │       └── sword.md
│       └── instances/         (The "live" instances of the templates)
│           ├── npcs/
│           │   └── louisa_instance_1.json
│           └── items/
│               └── sword_instance_1.json
└── players/
    └── user123/
        └── wylding-woods/
            └── progress.json    (The player's progress for this experience)
```

## 3. File Formats

*   **Templates:** Markdown (`.md`) files will be used for templates to allow for rich text formatting and human-readability.
*   **Instances and Player Progress:** JSON (`.json`) files will be used for instances and player progress to allow for structured data that can be easily parsed and manipulated by the system.

## 4. Three-Layer Architecture

The game state will be managed using a three-layer architecture:

*   **Layer 1: World Instances (Shared State):** These are the game objects that are shared by all players (e.g., NPC spawn locations, world items). These will be stored as JSON files in the `instances` directory within each experience.
*   **Layer 2: Player Progress (Per-Player State):** This is the data that is unique to each player, such as their inventory and quest progress. This will be stored in a separate `progress.json` file for each player and experience.
*   **Layer 3: Player World View (Computed at Runtime):** This is what the player actually sees. It's a combination of the world instances and their own personal progress. For example, if a player has collected an item, it would be removed from their world view. This view is computed at runtime and is not stored directly.

## 5. LLM Integration and Semantic Names

To ensure reliable interaction with the LLM, the following strategy will be used:

*   **The Problem:** LLMs are not reliable at handling specific, technical identifiers like UUIDs or file paths.
*   **The Solution:** The LLM will work with human-readable "semantic names" (e.g., "dream_bottle"). The server is then responsible for resolving these semantic names to the actual file paths or instance IDs.

This approach will prevent issues with the LLM hallucinating invalid identifiers.

## 6. The KB Intelligent Agent

The "brain" of the system is the **KB Intelligent Agent**. This agent is responsible for:

*   **Interpreting Knowledge:** Reading Markdown files from the KB and using them as rules to make decisions (e.g., calculating combat damage based on a `combat.md` file).
*   **Executing Workflows:** Following step-by-step instructions defined in a Markdown file to perform complex tasks.
*   **Validating Actions:** Checking if a proposed action is allowed based on a set of rules in the KB.

The KB Agent will have its own embedded LLM client, allowing it to function independently of the chat service.

## 7. API Endpoints

The following API endpoints will be used to interact with the KB Agent:

*   `POST /agent/interpret`: Interpret knowledge from the KB to answer queries or make decisions.
*   `POST /agent/execute-workflow`: Execute a workflow defined in a KB Markdown file.
*   `POST /agent/validate`: Validate an action against rules in the KB.

## 8. KB Tools

The LLM will be able to interact with the file-based KB using the following tools:

*   `search_knowledge_base`: Search for information in the KB.
*   `load_kos_context`: Load a KOS context.
*   `read_kb_file`: Read the content of a specific file in the KB.
*   `list_kb_directory`: List the files and directories in a given path in the KB.
*   `load_kb_context`: Load a topic-based context.
*   `synthesize_kb_information`: Synthesize information from multiple sources in the KB.

## 9. Querying and Performance

In the file-based MVP, querying the game state will involve:

*   Reading and parsing JSON files.
*   Searching for files in the directory structure.
*   Using text-based search tools like `grep` to find specific information.

This approach has known performance limitations and is not suitable for a large-scale, production environment. However, it is a simple and effective solution for the MVP.
