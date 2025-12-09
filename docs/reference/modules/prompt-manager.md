# Prompt Manager Module


## Overview

The Prompt Manager (`app/shared/prompt_manager.py`) manages system prompts for the chat service, integrating with the persona system to provide personalized AI behavior based on user preferences.

## Current Implementation

The module contains a single `PromptManager` class with one method:

### Methods

#### `get_system_prompt(user_id: str = None) -> str`
- **Purpose**: Retrieve the system prompt for a specific user
- **Behavior**: 
  1. If no user_id provided: Returns default prompt
  2. If user_id provided: Attempts to fetch user's persona
  3. Falls back to default persona if user has none
  4. Returns persona's system_prompt or default if unavailable

### Default Prompt
```python
"You are a helpful AI assistant."
```

## Integration with Persona System

The module integrates with the PostgreSQL-based persona service:

```python
from app.services.chat.persona_service_postgres import PostgresPersonaService
```

### Persona Lookup Flow
1. Check for user-specific persona
2. Fall back to default persona
3. Fall back to hardcoded default prompt

## Usage

Used by the Chat service to customize AI behavior:

```python
from app.shared.prompt_manager import PromptManager

# Get system prompt for a user
prompt = await PromptManager.get_system_prompt(user_id="user123")
```

## Dependencies

- `PostgresPersonaService` - For persona retrieval
- PostgreSQL database with personas table

## Status

- **Status**: ✅ Active
- **Priority**: High (core chat functionality)
- **Used by**: Chat service for all LLM interactions

## Error Handling

- Silently catches all exceptions
- Always returns a valid prompt (never None)
- Falls back to default prompt on any error