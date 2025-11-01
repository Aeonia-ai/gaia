# LLM Module Documentation

## Overview

The LLM module (`app/services/llm/`) is a provider-agnostic library that provides abstractions for interacting with multiple Large Language Model providers (Claude, OpenAI, etc.). It is NOT a standalone microservice but rather a shared library used by the Chat service.

## Architecture

### Core Components

1. **Base Abstractions** (`base.py`)
   - `LLMProvider`: Base class for all LLM providers
   - `LLMRequest/Response`: Standardized request/response models
   - `ModelCapability`: Defines what each model can do
   - `StreamChunk`: Streaming response handling

2. **Provider Registry** (`registry.py`)
   - Central registry for all available providers
   - Health monitoring and statistics tracking
   - Provider failover and load balancing

3. **Provider Implementations**
   - `claude_provider.py`: Anthropic Claude integration
   - `openai_provider.py`: OpenAI GPT integration

4. **Multi-Provider Selection** (`multi_provider_selector.py`)
   - Intelligent model selection based on context
   - Cost optimization
   - Capability matching

5. **Chat Service Helper** (`chat_service.py`)
   - High-level chat interface used by the Chat microservice
   - Session management
   - Response formatting

## Usage

The LLM module is used internally by the Chat service via direct Python imports:

```python
from app.services.llm.chat_service import chat_service
from app.services.llm import LLMProvider, ModelCapability
```

## Key Points

- **NOT a microservice** - It's a shared library/module
- **No Docker container** - Runs within the Chat service process
- **No API endpoints** - Accessed via Python imports only
- **Used by**: Chat Service (`app/services/chat/`)

## Configuration

Configured via environment variables in the Chat service:
- `CLAUDE_API_KEY`: Anthropic API key
- `OPENAI_API_KEY`: OpenAI API key
- `DEFAULT_LLM_PROVIDER`: Default provider selection

## Integration

The Chat service uses this module to:
- Route requests to appropriate LLM providers
- Handle streaming responses
- Manage provider failover
- Track usage and costs