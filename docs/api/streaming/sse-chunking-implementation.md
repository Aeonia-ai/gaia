# SSE Chunking Implementation in GAIA Chat Service

**Created**: January 2025  
**Purpose**: Document how Server-Sent Events (SSE) chunking is implemented in the GAIA chat service

## Overview

SSE chunking in GAIA converts the LLM's streaming response into properly formatted Server-Sent Events that can be consumed by clients. The implementation handles the conversion from various LLM provider formats to a standardized SSE format.

## SSE Format Specification

Each SSE event follows this structure:
```
data: {JSON_CONTENT}\n\n
```

The double newline (`\n\n`) is critical - it marks the end of an event and tells the client that a complete event has been received.

## Implementation Flow

### 1. Request Handler (`/chat/unified`)

When a request comes in with `stream: true`:

```python
# In chat.py - unified_chat_endpoint
if stream:
    async def stream_generator():
        """Generate SSE stream from unified chat handler"""
        try:
            # Process through unified handler with streaming
            async for chunk in unified_chat_handler.process_stream(
                message=message,
                auth=auth_principal,
                context=context
            ):
                # Format as SSE
                yield f"data: {json.dumps(chunk)}\n\n"
            
            # Send final done signal
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            # Error handling with SSE format
            error_chunk = {
                "error": {
                    "message": str(e),
                    "type": "streaming_error"
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*"
        }
    )
```

### 2. Key Components

#### StreamingResponse
- FastAPI's `StreamingResponse` class handles the HTTP response
- Sets `media_type="text/event-stream"` to indicate SSE format
- Returns an async generator that yields formatted events

#### Headers
- **`Cache-Control: no-cache`**: Prevents caching of stream
- **`Connection: keep-alive`**: Maintains persistent connection
- **`X-Accel-Buffering: no`**: Disables nginx buffering (critical for real-time streaming)
- **`Access-Control-Allow-Origin: *`**: CORS support

#### Event Generator Pattern
```python
async def stream_generator():
    # 1. Send start event
    yield f"data: {json.dumps({'type': 'start', 'timestamp': '...'})}\n\n"
    
    # 2. Stream content chunks
    async for chunk in llm_stream:
        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
    
    # 3. Send completion event
    yield f"data: {json.dumps({'type': 'done', 'finish_reason': 'stop'})}\n\n"
    
    # 4. Send final signal
    yield "data: [DONE]\n\n"
```

### 3. Event Types

The service generates different event types during streaming:

```python
# Start event - signals stream beginning
{"type": "start", "timestamp": "2025-01-01T00:00:00Z"}

# Content event - actual text chunks
{"type": "content", "content": "The answer is"}

# Metadata event - performance info
{"type": "metadata", "response_time_ms": 1234, "model": "claude-3"}

# Tool event - when tools are used
{"type": "tool_call", "tool": "search_kb", "arguments": {...}}

# Error event - if something goes wrong
{"type": "error", "error": {"message": "...", "code": "..."}}

# Done event - completion with metadata
{"type": "done", "finish_reason": "stop"}
```

### 4. Chunking Process

The chunking happens at multiple levels:

#### LLM Level
The underlying LLM (Claude, GPT, etc.) streams tokens/chunks:
```python
async for chunk in chat_service.chat_completion_stream(...):
    # Each chunk contains partial text
    # e.g., "The", " answer", " is", " 42"
```

#### Service Level
The service wraps each LLM chunk in SSE format:
```python
# LLM chunk: "The"
# SSE event: data: {"type": "content", "content": "The"}\n\n

# LLM chunk: " answer"  
# SSE event: data: {"type": "content", "content": " answer"}\n\n
```

#### Network Level
The network layer may further fragment the data:
- SSE events might be split across TCP packets
- Clients must buffer until they see `\n\n` to know they have a complete event

## Client-Side Buffering

Clients MUST implement proper buffering:

```python
# Python example from test-sse-streaming.py
buffer = ""
async for chunk in response.aiter_text():
    buffer += chunk
    
    # Process complete SSE events (separated by double newlines)
    while "\n\n" in buffer:
        event, buffer = buffer.split("\n\n", 1)
        
        if event.startswith("data: "):
            data_str = event[6:].strip()
            
            if data_str == "[DONE]":
                # Stream complete
                return
            
            data = json.loads(data_str)
            # Process the event
```

## Critical Implementation Details

### 1. Yielding Order
Always yield data BEFORE any cleanup operations:
```python
# CORRECT
yield f"data: {json.dumps(final_data)}\n\n"
yield "data: [DONE]\n\n"
# Then do cleanup

# WRONG - cleanup before final yield might not execute
# Do cleanup
yield "data: [DONE]\n\n"
```

### 2. JSON Serialization
All data must be JSON-serializable:
```python
chunk_data = {
    "type": "content",
    "content": text,
    "timestamp": datetime.utcnow().isoformat()  # Convert datetime to string
}
yield f"data: {json.dumps(chunk_data)}\n\n"
```

### 3. Error Handling
Errors are sent as SSE events, not HTTP errors:
```python
try:
    # streaming logic
except Exception as e:
    error_event = {
        "type": "error",
        "error": {"message": str(e)}
    }
    yield f"data: {json.dumps(error_event)}\n\n"
    yield "data: [DONE]\n\n"
```

### 4. The [DONE] Signal
The `[DONE]` signal is critical:
- It's a string literal, not JSON: `data: [DONE]\n\n`
- Clients use this to know the stream is complete
- Always send it, even after errors

## Performance Considerations

### Buffering Control
- `X-Accel-Buffering: no` - Disables nginx buffering
- `StreamFragmentSize = 1` - In client code, get data ASAP
- No internal buffering in the service layer

### Chunking Size
- LLMs typically send small chunks (words or partial words)
- No artificial batching - send chunks as they arrive
- This provides the best perceived performance

### Word and JSON Boundary Behavior

**UPDATED (v3)**: GAIA now implements intelligent streaming buffer that preserves boundaries while minimizing overhead.

#### Word Boundaries - ✅ Preserved in v3
The v3 StreamBuffer ensures word boundaries are never split:

```python
# What LLMs send (may split words):
"The qui", "ck brown ", "fox"

# What GAIA v3 sends to clients (words preserved):
"The ", "quick brown ", "fox"
```

**How it works**:
- Buffers incomplete words until a space/punctuation is detected
- Sends complete words immediately when possible
- Batches phrases at punctuation boundaries for efficiency
- Minimal latency impact (only buffers incomplete final words)

#### Embedded JSON Directives - ✅ Preserved in v3
JSON directives are now kept intact through intelligent detection:

```python
# Example response with embedded directive:
"I'll spawn a fairy! {"m":"spawn_character","p":{"type":"fairy"}}"

# What LLMs might send (split JSON):
"I'll spawn ", "a fairy! {\"m\":\"sp", "awn_char", "acter\",\"p\":{\"type\":\"fairy\"}}"

# What GAIA v3 sends (JSON preserved):
"I'll spawn a fairy! ", "{\"m\":\"spawn_character\",\"p\":{\"type\":\"fairy\"}}"
```

**Client Benefits with v3**:
1. **Simplified parsing** - JSON directives arrive complete
2. **Real-time extraction** - Can parse directives as they arrive
3. **No accumulation needed** - Each chunk is self-contained
4. **Reduced complexity** - No need to handle split words/JSON

```python
# With v3 - Parse directives immediately from each chunk
async for chunk in stream:
    if chunk["type"] == "content":
        # Safe to parse - JSON will be complete if present
        directives = extract_json_directives(chunk["content"])
        display_text = remove_directives(chunk["content"])
```

#### Implementation Details
The v3 StreamBuffer (`app/services/streaming_buffer.py`):
- **Pattern detection**: Identifies `{"m":` pattern to start JSON buffering
- **Brace counting**: Tracks `{` and `}` to find JSON boundaries
- **Phrase batching**: Sends complete sentences when possible
- **Configurable**: Can be disabled if raw pass-through is needed

#### Why This Matters
- **Better UX** - No flickering from split words in UI
- **Simpler clients** - Unity ChatClient doesn't need word reconstruction
- **Valid JSON** - Directives always parse correctly
- **Reduced overhead** - Fewer SSE events through phrase batching

### Connection Management
- Keep-alive connections reduce overhead
- Clients should handle reconnection for long streams
- Server timeouts should be set appropriately (30+ seconds)

## Testing SSE Streams

Use the test script to validate SSE implementation:
```bash
API_KEY="your-key" python3 scripts/test-sse-streaming.py
```

The script verifies:
- Proper event boundaries
- JSON parsing of events
- Complete message reconstruction
- No token splitting issues

## Common Issues and Solutions

### Issue: Events not appearing in real-time
**Solution**: Check for buffering at any layer (nginx, proxy, client)

### Issue: Partial events received
**Solution**: Implement proper buffering until `\n\n` is seen

### Issue: JSON parse errors
**Solution**: Ensure all data is properly escaped before JSON serialization

### Issue: Connection drops mid-stream
**Solution**: Implement client-side reconnection logic with resume capability

## Summary

SSE chunking in GAIA:
1. Receives streaming chunks from LLM providers
2. Wraps each chunk in SSE format with event type
3. Yields formatted events with proper `\n\n` delimiters
4. Uses `StreamingResponse` with `text/event-stream` content type
5. Sends `[DONE]` signal to indicate completion

The implementation prioritizes real-time delivery with minimal buffering while ensuring proper event boundaries for reliable client parsing.