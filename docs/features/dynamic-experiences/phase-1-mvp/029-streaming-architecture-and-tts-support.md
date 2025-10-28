# Streaming Architecture and TTS Support

**Status:** Planned
**Priority:** High
**Created:** 2025-10-27
**Related:** [016-conversation-id-streaming.md](016-conversation-id-streaming.md), [017-streaming-release-notes.md](017-streaming-release-notes.md)

## Overview

This document outlines the streaming architecture for GAIA's chat and KB systems, with special focus on progressive phrase delivery for Text-to-Speech (TTS) clients. Currently, the system uses **simulated streaming** (fetching complete responses then chunking them locally), when **real streaming** from LLM providers would provide significantly better user experience.

### Current State

**Unified Chat (`/chat/unified`):**
- ✅ Supports streaming mode (`stream=true`)
- ❌ **Simulated streaming** - waits for complete LLM response, then chunks locally
- ❌ 2-3 second delay before first content arrives
- ⚠️ StreamBuffer creates phrase boundaries, but on pre-fetched content

**Multi-Provider Chat (`/chat/multi-provider`):**
- ✅ Supports streaming mode
- ✅ **Real LLM streaming** - tokens arrive as generated
- ✅ ~300ms time-to-first-token
- ✅ Progressive phrase boundaries via StreamBuffer

**KB Agent:**
- ❌ No streaming support
- ❌ All 6 internal LLM calls are non-streaming
- ⚠️ NPC conversations (1-3s) perfect candidate for streaming

### Performance Impact

| Scenario | Current | With Real Streaming | Improvement |
|----------|---------|---------------------|-------------|
| Simple chat ("What is 2+2?") | 2.5s blank → rapid text | 300ms → progressive phrases | **2.2s faster perception** |
| NPC conversation | 2.5s wait → complete dialogue | 600ms → phrase-by-phrase | **1.9s faster perception** |
| KB search + synthesis | 2.5s wait → formatted results | 50ms metadata → 300ms synthesis | **2.2s faster perception** |

---

## Architecture Analysis

### Unified Chat Flow

```
┌─────────────────────────────────────────────────┐
│ POST /chat/unified (stream=true)                │
│ app/services/chat/chat.py:147-303               │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
        ┌─────────────────────┐
        │ process_stream()     │
        │ unified_chat.py:660  │
        └─────────┬────────────┘
                  │
                  ▼
     ┌────────────────────────────┐
     │ Routing Call (NON-STREAM)  │
     │ chat_service.chat_completion()  │ ← ⚠️ PROBLEM: Waits for complete response
     │ Line 727                   │
     └────────┬───────────────────┘
              │
      ┌───────┴────────┐
      │                │
   No Tools        Tool Calls
      │                │
      ▼                ▼
┌──────────────┐  ┌──────────────┐
│ Direct Path  │  │ KB/MCP Path  │
│ Line 1302    │  │ Line 750     │
└──────┬───────┘  └──────┬───────┘
       │                  │
       ▼                  ▼
  chunk complete    chunk complete
  response with     tool results with
  StreamBuffer      StreamBuffer
  (SIMULATED)       (SIMULATED)
```

**Key Issues:**

1. **Line 727** - Routing call is `chat_completion()` not `chat_completion_stream()`
2. **Lines 1302-1372** - Direct path chunks pre-fetched content
3. **Lines 750-853** - KB tools chunk pre-fetched results
4. All paths add artificial delays (`asyncio.sleep(0.003-0.01)`)

---

## Solution 1: Real Streaming for Direct Responses

### Implementation

**Replace unified_chat.py:727** with streaming call:

```python
# TODO(REAL-STREAMING): Replace chat_completion with chat_completion_stream for progressive TTS
#
# CURRENT: Non-streaming routing call waits for complete response (~2-3s), then simulates
#          streaming by chunking locally. Users wait 2-3s before seeing ANY content.
#
# OPTIMAL: Use chat_completion_stream() to get tokens as LLM generates them (~300ms to first token).
#          StreamBuffer creates phrase boundaries for TTS as complete sentences arrive.
#
# CHANGE:  Replace await chat_service.chat_completion(...) below with:
#          async for chunk in chat_service.chat_completion_stream(...)
#          Then accumulate content and tool_calls during streaming.
#
# BENEFIT: 2-3 second perceptual delay → 300ms time-to-first-phrase for TTS clients
#
# COMPLEXITY: Moderate - need to handle tool calls arriving mid-stream
#
# See: docs/features/dynamic-experiences/phase-1-mvp/029-streaming-architecture-and-tts-support.md

# Current non-streaming routing call
routing_response = await chat_service.chat_completion(
    messages=messages,
    system_prompt=system_prompt,
    tools=all_tools,
    tool_choice={"type": "auto"},
    temperature=0.7,
    max_tokens=4096,
    request_id=f"{request_id}-routing"
)
```

**Proposed Replacement:**

```python
# Real streaming with tool support
accumulated_content = ""
accumulated_tool_calls = []
buffer = StreamBuffer(preserve_json=True, sentence_mode=False)

async for chunk in chat_service.chat_completion_stream(
    messages=messages,
    system_prompt=system_prompt,
    tools=all_tools,
    tool_choice={"type": "auto"},
    temperature=0.7,
    max_tokens=4096,
    request_id=f"{request_id}-routing"
):
    chunk_type = chunk.get("type")

    # Handle content streaming (direct response)
    if chunk_type == "content":
        content = chunk.get("content", "")
        accumulated_content += content

        # Stream phrase boundaries for TTS
        async for phrase in buffer.process(content):
            yield {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": chunk.get("model", "unknown"),
                "choices": [{
                    "index": 0,
                    "delta": {"content": phrase},
                    "finish_reason": None
                }]
            }
            # ✅ No artificial delay - tokens arrive at natural LLM pace

    # Handle tool calls (routing to KB/MCP)
    elif chunk_type == "tool_call":
        tool_call = chunk.get("tool_call")
        accumulated_tool_calls.append(tool_call)

# Flush remaining content from buffer
async for phrase in buffer.flush():
    if phrase:
        yield {
            "id": request_id,
            "object": "chat.completion.chunk",
            "choices": [{
                "index": 0,
                "delta": {"content": phrase},
                "finish_reason": None
            }]
        }

# ✅ If tool calls were made, handle them AFTER streaming completes
if accumulated_tool_calls:
    # Execute KB tools or route to MCP (existing logic)
    # ... (lines 750-948 logic here)
```

### Benefits

- ✅ **300ms time-to-first-token** (vs 2-3s currently)
- ✅ **Progressive phrase boundaries** perfect for TTS
- ✅ **Natural token pace** (no artificial delays)
- ✅ **One LLM call** for direct responses (cost-efficient)
- ✅ **Maintains intelligent routing** (tool calls still work)

### Limitations

- ⚠️ KB tools still need **second streaming call** for synthesis (unavoidable)
- ⚠️ More complex state management (accumulate content + tool calls during stream)

---

## Solution 2: KB Agent Streaming

### KB Agent Internal LLM Calls

The KB agent makes 6 different LLM calls, all currently non-streaming:

| Location | Method | Purpose | Duration | Streaming Priority |
|----------|--------|---------|----------|-------------------|
| **Line 3331** | `_talk_to_npc()` | **NPC conversations** | 1-3s | ✅ **VERY HIGH** - Perfect for TTS |
| Line 86 | `interpret_knowledge()` | Synthesis/validation | 2-5s | ✅ **HIGH** - Long responses |
| Line 365 | `execute_knowledge_workflow()` | Multi-step workflows | 3-8s | ✅ **HIGH** - Progress updates |
| Line 413 | `validate_against_rules()` | Validate actions | 1-3s | ⚠️ **MEDIUM** |
| Line 202 | `execute_game_command()` | Parse commands | 300-800ms | ❌ **LOW** - Fast JSON |
| Line 1013 | `resolve_location()` | Parse location refs | 300-500ms | ❌ **LOW** - Fast JSON |

### Priority 1: NPC Conversation Streaming

**Current Code (kb_agent.py:3331-3337):**

```python
# 4. Generate response with LLM
llm_response = await self.llm_service.chat_completion(  # ❌ Non-streaming
    messages=[{"role": "user", "content": context}],
    model="claude-3-5-haiku-20241022",
    user_id=user_id,
    temperature=0.7  # Natural conversation
)
response_text = llm_response["response"]  # Wait for complete text

return {
    "success": True,
    "narrative": response_text,
    "actions": [...],
    "state_changes": {...}
}
```

**User Experience - Current:**

```
User: "Hello Louisa, can you tell me about the dream bottles?"
    ↓
⏱️ 0.3s  - Command parsed
⏱️ 2.5s  - Complete narrative arrives all at once
         "Ah, the dream bottles! They're quite special. Each one
         contains a captured dream from the Wylding Woods..."
```

**Proposed Streaming Version:**

```python
async def _talk_to_npc_stream(
    self,
    experience: str,
    npc_semantic_name: str,
    message: str,
    user_id: str,
    waypoint: str,
    sublocation: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream NPC conversation with progressive phrase delivery for TTS.

    Yields:
        - {"type": "metadata", "npc": name, "mood": ...} - Initial metadata
        - {"type": "content", "content": phrase, "npc": name} - Phrases as they complete
        - {"type": "metadata", "phase": "complete", "relationship": {...}} - Final state
    """
    try:
        # 1. Find NPC (same as non-streaming)
        manifest = await self._load_manifest(experience)
        npc_instance = None
        for inst in manifest["instances"]:
            if (inst["semantic_name"] == npc_semantic_name and
                inst["location"] == waypoint):
                if sublocation is None or inst.get("sublocation") == sublocation:
                    npc_instance = inst
                    break

        if not npc_instance:
            yield {
                "type": "error",
                "error": {"code": "npc_not_found", "message": f"No {npc_semantic_name} here"},
                "narrative": f"You don't see {npc_semantic_name} nearby."
            }
            return

        # 2. Load three-layer memory (same as non-streaming)
        template_text = await self._load_npc_template_text(experience, npc_instance["template"])
        instance_state = await self._load_npc_instance_state(experience, npc_instance["instance_file"])
        relationship = await self._load_npc_relationship(experience, user_id, npc_instance["template"])

        # 3. Send initial metadata
        yield {
            "type": "metadata",
            "phase": "conversation_start",
            "npc": npc_semantic_name,
            "mood": instance_state["state"].get("emotional_state", "neutral"),
            "trust": relationship["trust_level"]
        }

        # 4. Build context
        context = self._build_npc_context(
            template_text=template_text,
            instance_state=instance_state,
            relationship=relationship,
            message=message
        )

        # 5. ✅ Stream LLM response with phrase boundaries
        buffer = StreamBuffer(preserve_json=True, sentence_mode=False)
        accumulated_response = ""

        async for chunk in self.llm_service.chat_completion_stream(
            messages=[{"role": "user", "content": context}],
            model="claude-3-5-haiku-20241022",
            user_id=user_id,
            temperature=0.7
        ):
            if chunk.get("type") == "content":
                content = chunk.get("content", "")
                accumulated_response += content

                # Stream phrase boundaries for TTS
                async for phrase in buffer.process(content):
                    yield {
                        "type": "content",
                        "content": phrase,
                        "npc": npc_semantic_name
                    }

        # Flush remaining content
        async for phrase in buffer.flush():
            if phrase:
                yield {
                    "type": "content",
                    "content": phrase,
                    "npc": npc_semantic_name
                }

        # 6. Update relationship (after streaming completes)
        timestamp = datetime.utcnow().isoformat() + "Z"
        conversation_entry = {
            "timestamp": timestamp,
            "player": message,
            "npc": accumulated_response,
            "mood": instance_state["state"].get("emotional_state", "neutral")
        }

        relationship["conversation_history"].append(conversation_entry)
        if len(relationship["conversation_history"]) > 20:
            relationship["conversation_history"] = relationship["conversation_history"][-20:]

        relationship["total_conversations"] += 1
        relationship["last_interaction"] = timestamp

        if len(message) > 5:
            relationship["trust_level"] = min(100, relationship["trust_level"] + 2)

        await self._save_npc_relationship_atomic(experience, user_id, npc_instance["template"], relationship)

        # 7. Send completion metadata
        yield {
            "type": "metadata",
            "phase": "complete",
            "relationship": {
                "npc": npc_semantic_name,
                "trust": relationship["trust_level"],
                "conversations": relationship["total_conversations"]
            }
        }

    except Exception as e:
        logger.error(f"NPC conversation streaming failed: {e}", exc_info=True)
        yield {
            "type": "error",
            "error": {"code": "npc_talk_failed", "message": str(e)},
            "narrative": f"Something went wrong while talking to {npc_semantic_name}."
        }
```

**User Experience - With Streaming:**

```
User: "Hello Louisa, can you tell me about the dream bottles?"
    ↓
⏱️ 0.3s  - Command parsed
⏱️ 0.35s - Metadata: {"npc": "louisa", "mood": "friendly", "trust": 65}
          🎭 UI shows Louisa's mood/trust
⏱️ 0.6s  - First phrase: "Ah, the dream bottles!"
          🔊 TTS starts speaking immediately
⏱️ 1.0s  - Next phrase: "They're quite special."
          🔊 TTS continues naturally
⏱️ 1.5s  - Next phrase: "Each one contains a captured dream from the Wylding Woods."
          🔊 Conversation flows smoothly
⏱️ 2.0s  - Final phrase: "Some say they can show you visions of the past."
          🔊 Complete
⏱️ 2.1s  - Metadata: {"phase": "complete", "trust": 67, "conversations": 5}
          🎭 UI updates relationship stats
```

**Improvement: 2.5s blank wait → 600ms to first speech**

---

## Integration with Unified Chat

### Detect and Route NPC Conversations

**In unified_chat.py `process_stream()` method:**

```python
# When KB tool is "execute_game_command"
if tool_name == "execute_game_command":
    command = tool_args.get("command")
    experience = tool_args.get("experience")

    # Quick heuristic: Is this an NPC conversation?
    is_npc_conversation = (
        "talk" in command.lower() or
        "ask" in command.lower() or
        "hello" in command.lower() or
        "hi " in command.lower() or
        "tell me" in command.lower()
    )

    if is_npc_conversation:
        # Import KB agent
        from app.services.kb.kb_agent import kb_agent

        # Parse command quickly to extract NPC name
        # (Could use existing parse logic or simple regex)
        parsed = await kb_agent._parse_command_for_npc(command)

        if parsed.get("action") == "talk" and parsed.get("target"):
            # ✅ Stream NPC conversation
            async for event in kb_agent._talk_to_npc_stream(
                experience=experience,
                npc_semantic_name=parsed["target"],
                message=command,
                user_id=auth.get("user_id"),
                waypoint=tool_args.get("waypoint", "unknown"),
                sublocation=tool_args.get("sublocation")
            ):
                if event.get("type") == "content":
                    # Stream content to client
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "choices": [{
                            "index": 0,
                            "delta": {"content": event.get("content")},
                            "finish_reason": None
                        }],
                        "_metadata": {
                            "npc": event.get("npc"),
                            "source": "kb_npc_conversation"
                        }
                    }
                elif event.get("type") == "metadata":
                    # Send metadata about NPC state
                    yield {
                        "type": "metadata",
                        "data": event
                    }
        else:
            # Not a valid NPC conversation, fall back to non-streaming
            result = await kb_agent.execute_game_command(...)
            # Chunk the result with StreamBuffer (simulated streaming)
            buffer = StreamBuffer(preserve_json=True)
            async for chunk in buffer.process(result["narrative"]):
                yield {"choices": [{"delta": {"content": chunk}}]}
    else:
        # Non-conversation game commands (look, collect, return, inventory)
        # These are fast (35-95ms), no benefit from streaming
        result = await kb_agent.execute_game_command(...)

        # Send complete result
        buffer = StreamBuffer(preserve_json=True)
        async for chunk in buffer.process(result["narrative"]):
            yield {"choices": [{"delta": {"content": chunk}}]}
```

---

## Implementation Roadmap

### Phase 1: Direct Response Streaming (Week 1)

**Goal:** Enable real streaming for simple chat queries

**Tasks:**
1. ✅ Update `unified_chat.py:727` to use `chat_completion_stream()`
2. ✅ Accumulate content and tool_calls during streaming
3. ✅ Handle tool calls after stream completes
4. ✅ Remove artificial delays
5. ✅ Test time-to-first-token improvement (target: <500ms)

**Success Metrics:**
- Time-to-first-token: 2-3s → <500ms
- Phrase boundaries preserved for TTS
- Tool routing still works

---

### Phase 2: NPC Conversation Streaming (Week 2)

**Goal:** Stream NPC dialogues for natural TTS delivery

**Tasks:**
1. ✅ Add `_talk_to_npc_stream()` method to KB agent
2. ✅ Detect NPC conversations in unified chat
3. ✅ Route to streaming variant when detected
4. ✅ Send metadata events (mood, trust, etc.)
5. ✅ Test with Unity TTS client

**Success Metrics:**
- NPC conversation time-to-first-speech: 2.5s → <800ms
- Phrase boundaries natural for TTS
- Relationship updates work correctly

---

### Phase 3: Knowledge Operations Streaming (Week 3-4)

**Goal:** Stream knowledge synthesis and workflows

**Tasks:**
1. ✅ Add `interpret_knowledge_stream()` for synthesis
2. ✅ Add `execute_knowledge_workflow_stream()` for workflows
3. ✅ Stream progress metadata during multi-step operations
4. ✅ Update KB tools to use streaming variants

**Success Metrics:**
- Knowledge synthesis shows progress in <100ms
- Multi-step workflows stream intermediate results
- Long responses benefit from progressive delivery

---

## Testing Strategy

### Unit Tests

**Test streaming behavior:**

```python
# tests/services/chat/test_unified_chat_streaming.py

async def test_direct_response_real_streaming():
    """Test that direct responses use real LLM streaming."""
    handler = unified_chat_handler

    chunks = []
    first_chunk_time = None
    start_time = time.time()

    async for chunk in handler.process_stream(
        message="What is 2+2?",
        auth={"user_id": "test"},
        context={"stream": True}
    ):
        if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
            if first_chunk_time is None:
                first_chunk_time = time.time() - start_time
            chunks.append(chunk)

    # Verify real streaming (not simulated)
    assert first_chunk_time < 0.8, f"First chunk took {first_chunk_time}s (should be <800ms)"
    assert len(chunks) > 1, "Should receive multiple chunks"

    # Verify phrase boundaries
    full_content = "".join(
        chunk["choices"][0]["delta"]["content"]
        for chunk in chunks
        if chunk.get("choices")
    )
    assert "4" in full_content


async def test_npc_conversation_streaming():
    """Test NPC conversations stream with phrase boundaries."""
    from app.services.kb.kb_agent import kb_agent

    chunks = []
    metadata_events = []
    first_content_time = None
    start_time = time.time()

    async for event in kb_agent._talk_to_npc_stream(
        experience="wylding-woods",
        npc_semantic_name="louisa",
        message="Hello, can you tell me about the dream bottles?",
        user_id="test_player",
        waypoint="waypoint_28a",
        sublocation=None
    ):
        if event.get("type") == "content":
            if first_content_time is None:
                first_content_time = time.time() - start_time
            chunks.append(event["content"])
        elif event.get("type") == "metadata":
            metadata_events.append(event)

    # Verify streaming performance
    assert first_content_time < 1.0, f"First content took {first_content_time}s (should be <1s)"

    # Verify metadata
    assert any(e.get("phase") == "conversation_start" for e in metadata_events)
    assert any(e.get("phase") == "complete" for e in metadata_events)

    # Verify phrase boundaries (sentences end with punctuation)
    for chunk in chunks:
        assert chunk.strip(), "Chunks should not be empty"
        # Most chunks should end with sentence boundaries
        # (though not all, due to progressive streaming)

    # Verify complete narrative
    full_narrative = "".join(chunks)
    assert len(full_narrative) > 20, "Should have substantial response"
    assert "dream bottle" in full_narrative.lower() or "bottle" in full_narrative.lower()
```

### Integration Tests

**Test with Unity client:**

```python
# tests/e2e/test_tts_streaming.py

async def test_unity_tts_integration():
    """Test TTS client receives phrase boundaries progressively."""
    # Simulate Unity client connecting to streaming endpoint

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8666/api/v0.3/chat",
            json={
                "message": "talk to louisa about dream bottles",
                "stream": True,
                "experience": "wylding-woods",
                "waypoint": "waypoint_28a"
            },
            headers={"X-API-Key": TEST_API_KEY}
        ) as response:
            phrases = []
            first_phrase_time = None
            start_time = time.time()

            async for line in response.content:
                if line.startswith(b"data: "):
                    data = json.loads(line[6:])

                    if data.get("choices"):
                        content = data["choices"][0].get("delta", {}).get("content")
                        if content:
                            if first_phrase_time is None:
                                first_phrase_time = time.time() - start_time
                            phrases.append(content)

            # Verify TTS-friendly timing
            assert first_phrase_time < 1.0, "TTS should start within 1 second"
            assert len(phrases) >= 2, "Should receive multiple phrases for natural TTS"

            # Verify speakable units (not mid-word chunks)
            for phrase in phrases:
                # Phrases should generally end at natural boundaries
                # (though StreamBuffer may split on commas, periods, etc.)
                assert not phrase.endswith(" a") and not phrase.endswith(" the"), \
                    "Phrases should not cut articles"
```

---

## Performance Benchmarks

### Expected Improvements

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **Direct chat - time to first token** | 2-3s | <500ms | **80-85% faster** |
| **NPC conversation - time to first phrase** | 2.5s | <800ms | **68% faster** |
| **KB search - metadata delivery** | 2.5s | <100ms | **96% faster** |
| **KB synthesis - time to first phrase** | 2.5s | <500ms | **80% faster** |

### TTS Client Benefits

**Current (Simulated Streaming):**
- User waits 2.5s in silence
- Full response arrives in ~50ms burst
- TTS speaks rapidly, then finishes
- **Feels delayed and rushed**

**With Real Streaming:**
- Metadata arrives in 50-100ms (loading indicator)
- First phrase arrives in 300-800ms (TTS starts)
- Subsequent phrases arrive every 500ms-1s
- TTS paces naturally with generation
- **Feels conversational and immediate**

---

## Code Locations

### Files to Modify

1. **`app/services/chat/unified_chat.py`**
   - Line 727: Replace `chat_completion()` with `chat_completion_stream()`
   - Lines 1302-1372: Update direct response path
   - Lines 750-853: Update KB tools path

2. **`app/services/kb/kb_agent.py`**
   - Add `_talk_to_npc_stream()` method (after line 3331)
   - Add `interpret_knowledge_stream()` method (after line 86)
   - Add `execute_knowledge_workflow_stream()` method (after line 365)

3. **`app/services/kb/kb_agent_streaming.py`**
   - Already has `StreamingKBAgent` class
   - Consider merging methods into main KB agent

### New Files

1. **`tests/services/chat/test_unified_chat_real_streaming.py`**
   - Test real streaming vs simulated streaming
   - Verify phrase boundaries
   - Performance benchmarks

2. **`tests/services/kb/test_kb_agent_streaming.py`**
   - Test NPC conversation streaming
   - Test knowledge synthesis streaming
   - Verify metadata events

3. **`tests/e2e/test_tts_streaming_integration.py`**
   - End-to-end TTS client tests
   - Verify Unity integration
   - Performance regression tests

---

## Migration Strategy

### Backward Compatibility

**Maintain non-streaming methods:**

```python
# kb_agent.py

async def _talk_to_npc(self, ...) -> Dict[str, Any]:
    """Legacy non-streaming NPC conversation."""
    # Keep existing implementation for compatibility
    ...

async def _talk_to_npc_stream(self, ...) -> AsyncGenerator:
    """Streaming NPC conversation for TTS clients."""
    # New streaming implementation
    ...
```

**Feature detection in clients:**

```typescript
// Unity client
if (supportsStreaming) {
    // Use streaming endpoint
    await streamChat({ message, stream: true });
} else {
    // Fallback to non-streaming
    await sendChat({ message });
}
```

### Rollout Plan

1. **Week 1:** Deploy direct response streaming (low risk)
2. **Week 2:** Deploy NPC streaming (moderate risk, limited to game commands)
3. **Week 3:** Monitor performance metrics
4. **Week 4:** Deploy knowledge operations streaming
5. **Week 5:** Deprecation notice for simulated streaming
6. **Week 6+:** Remove simulated streaming code

---

## Related Documentation

- [016-conversation-id-streaming.md](016-conversation-id-streaming.md) - Conversation ID delivery in streaming
- [017-streaming-release-notes.md](017-streaming-release-notes.md) - Original streaming implementation
- [027-npc-communication-system.md](027-npc-communication-system.md) - NPC three-layer memory architecture
- [010-chat-endpoint-execution-paths.md](010-chat-endpoint-execution-paths.md) - Chat routing architecture

---

## Open Questions

1. **Should we support mixed streaming/non-streaming?**
   - Some operations (file reads) don't benefit from streaming
   - Could detect and skip streaming for these

2. **How to handle streaming errors gracefully?**
   - Send error events in stream
   - Close stream cleanly
   - Client retry logic

3. **Should knowledge synthesis always stream?**
   - Short responses (<2s) may not benefit
   - Could use heuristic based on expected length

4. **Cache streaming responses?**
   - NPC conversations change based on relationship
   - Direct responses could be cached
   - Trade-off: cache hit vs streaming latency

---

## Success Criteria

**Phase 1 Complete When:**
- ✅ Direct responses stream in <500ms
- ✅ Phrase boundaries preserved
- ✅ Tool routing works with streaming
- ✅ All tests passing

**Phase 2 Complete When:**
- ✅ NPC conversations stream in <800ms
- ✅ Unity TTS client integration working
- ✅ Relationship updates work correctly
- ✅ Metadata events delivered

**Phase 3 Complete When:**
- ✅ Knowledge synthesis streams progressively
- ✅ Workflows show intermediate results
- ✅ Performance benchmarks met
- ✅ Documentation complete

**Overall Success:**
- 🎯 80%+ reduction in time-to-first-content
- 🎯 TTS clients report natural conversation flow
- 🎯 No regression in tool routing accuracy
- 🎯 Zero increase in error rates