# Unified State Model

This section documents the architecture and schemas for the unified state model, which is designed to provide a consistent and flexible framework for managing game state across different types of experiences.

---

## Key Documents

**[experience-config-schema.md](experience-config-schema.md)**
*   **Summary**: This document provides the JSON schema for the `config.json` file that is required for each experience. This configuration defines critical parameters for how the experience manages its state (shared vs. isolated), handles multiplayer interactions, bootstraps new players, and declares its capabilities (e.g., GPS-based, AR-enabled, inventory system).

**[config-examples.md](config-examples.md)**
*   **Summary**: This document provides concrete examples of the target unified `config.json` architecture for different types of game experiences. It includes examples for a Shared Multiplayer AR game (Wylding Woods), an Isolated Single-Player text adventure (West of House), and a Simple Mini-Game (Rock Paper Scissors), serving as a practical guide for how to apply the schema.

**[markdown-command-format.md](markdown-command-format.md)**
*   **Summary**: This document describes a target architecture where game commands are defined as human-readable markdown files, intended for an LLM to interpret and execute. It specifies a detailed format for these files, including YAML frontmatter for metadata (command name, aliases) and structured sections for intent detection, input parameters, state access, execution logic, state updates, and response formats.
