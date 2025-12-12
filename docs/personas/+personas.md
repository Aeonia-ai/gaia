# Personas

This directory contains documentation related to the AI personas used within the Gaia platform. Each persona defines a specific personality, role, and set of capabilities that guide the LLM's behavior and responses.

---

## Persona Documents

**[game-master-persona.md](game-master-persona.md)**
*   **Summary**: This document details the "Game Master" persona, which has the database ID `7b197909-8837-4ed5-a67a-a05c90e817f1`. Its purpose is to transform the Chat LLM into a game command processor that bridges natural language and game mechanics by using the `execute_game_command` tool. The document provides the full system prompt stored in the database, which instructs the LLM on its core responsibilities, tool usage rules (for both player and admin commands), and output formats.
