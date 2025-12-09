# Directive System for VR/AR Experiences


**Status**: 🟢 Implemented (Pause method)  
**Last Updated**: January 2025

## Overview

The directive system enables real-time control of conversation pacing and immersive experiences in VR/AR environments through JSON-RPC commands embedded directly in chat responses. This creates choreographed, multi-sensory experiences essential for meditation, training, and therapeutic applications.

## Core Concept

Directives are **inline JSON-RPC commands** that control timing and behavior:

```json
{"m":"method_name","p":{"param":"value"}}
```

These commands are embedded naturally within conversational text and parsed by client applications to create timed, interactive experiences.

## Current Implementation

### Pause Method

The only currently implemented directive creates timed delays:

```json
{"m":"pause","p":{"secs":2.0}}
```

**Parameters**:
- `secs`: Duration in seconds (supports decimals)
- Range: 0.1 to 30.0 seconds typically

**Usage Examples**:
```
"Take a deep breath... {"m":"pause","p":{"secs":4.0}} ...and exhale slowly."
"Let me think... {"m":"pause","p":{"secs":2.0}} I have an idea!"
"3... {"m":"pause","p":{"secs":1.0}} 2... {"m":"pause","p":{"secs":1.0}} 1... {"m":"pause","p":{"secs":1.0}} Go!"
```

## When Directives Are Enabled

### Automatic Activation

From `unified_chat.py`:

```python
def _is_directive_enhanced_context(self, context: dict) -> bool:
    # v0.3 API always uses directives
    if context.get("response_format") == "v0.3":
        return True
    
    # Explicit directive flag
    if context.get("enable_directives"):
        return True
    
    return False
```

### API Version Support
- **v0.3 API**: Always enabled (immersive experiences)
- **v1 API**: Optional via context flag
- **Legacy v0.2**: Not supported

## System Prompt Integration

When directives are enabled, the system adds instructions:

```python
directive_section = """
DIRECTIVE-ENHANCED RESPONSES:
For immersive virtual world interactions, embed JSON-RPC directives within your responses.

Directive Format: {"m":"method_name","p":{"param":"value"}}

Available Methods:

PAUSE:
- pause: {"m":"pause","p":{"secs":2.0}} - Pause for 2 seconds
- pause: {"m":"pause","p":{"secs":0.5}} - Brief pause
- pause: {"m":"pause","p":{"secs":5.0}} - Longer pause

Examples:
- "Let me think for a moment... {"m":"pause","p":{"secs":2.0}} I have an idea!"
- "Take a deep breath... {"m":"pause","p":{"secs":3.0}} ...and exhale slowly."

Guidelines:
- Embed directives naturally within conversational flow
- Multiple pauses can be used in one response
- Consider pacing for the specific activity
"""
```

## Real-World Applications

### 1. Guided Meditation (Mu Persona)

```json
Beep boop! Let's do a calming meditation together.

Find a comfortable position... {"m":"pause","p":{"secs":3.0}}

Close your eyes gently... {"m":"pause","p":{"secs":2.0}}

Now, breathe in slowly through your nose... 
{"m":"pause","p":{"secs":4.0}}

Hold the breath gently... 
{"m":"pause","p":{"secs":4.0}}

And release through your mouth... 
{"m":"pause","p":{"secs":6.0}}

Beautiful! Let's continue with this rhythm.

Inhale... {"m":"pause","p":{"secs":4.0}}
Hold... {"m":"pause","p":{"secs":4.0}}
Exhale... {"m":"pause","p":{"secs":6.0}}

Bleep bloop! You're doing wonderfully!
```

### 2. Exercise Routine

```json
Let's do some desk stretches!

First, roll your shoulders back... 
{"m":"pause","p":{"secs":3.0}}

Now forward... 
{"m":"pause","p":{"secs":3.0}}

Great! Raise your arms above your head... 
{"m":"pause","p":{"secs":2.0}}

Stretch to the left... 
{"m":"pause","p":{"secs":3.0}}

And to the right... 
{"m":"pause","p":{"secs":3.0}}

Excellent work!
```

### 3. Interactive Storytelling

```json
You enter the ancient temple...
{"m":"pause","p":{"secs":2.0}}

The door creaks open slowly...
{"m":"pause","p":{"secs":3.0}}

Suddenly, you hear footsteps!
{"m":"pause","p":{"secs":1.5}}

A figure emerges from the shadows...
{"m":"pause","p":{"secs":2.0}}

It's the guardian of the temple!
```

### 4. Therapeutic Breathing (4-7-8 Technique)

```json
Let's practice the 4-7-8 breathing technique for relaxation.

Empty your lungs completely...
{"m":"pause","p":{"secs":2.0}}

Now, inhale through your nose for 4 counts...
{"m":"pause","p":{"secs":4.0}}

Hold your breath for 7 counts...
{"m":"pause","p":{"secs":7.0}}

Exhale completely through your mouth for 8 counts...
{"m":"pause","p":{"secs":8.0}}

Wonderful! This technique helps activate your parasympathetic nervous system.
```

## Client Implementation

### Parsing Directives

```javascript
// JavaScript example for VR/AR client
function parseDirectives(text) {
    const directivePattern = /\{"m":"(\w+)","p":(\{[^}]+\})\}/g;
    const segments = [];
    let lastIndex = 0;
    
    let match;
    while (match = directivePattern.exec(text)) {
        // Add text before directive
        if (match.index > lastIndex) {
            segments.push({
                type: 'text',
                content: text.slice(lastIndex, match.index)
            });
        }
        
        // Add directive
        segments.push({
            type: 'directive',
            method: match[1],
            params: JSON.parse(match[2])
        });
        
        lastIndex = match.index + match[0].length;
    }
    
    // Add remaining text
    if (lastIndex < text.length) {
        segments.push({
            type: 'text',
            content: text.slice(lastIndex)
        });
    }
    
    return segments;
}
```

### Executing Directives

```javascript
// Execute parsed segments with timing
async function executeResponse(segments) {
    for (const segment of segments) {
        if (segment.type === 'text') {
            displayText(segment.content);
        } else if (segment.type === 'directive') {
            if (segment.method === 'pause') {
                await sleep(segment.params.secs * 1000);
            }
            // Future: handle other directive types
        }
    }
}
```

## Future Directive Types

### Planned Enhancements

```json
// Animation control
{"m":"animate","p":{"action":"wave","duration":2.0}}

// Sound effects
{"m":"sound","p":{"file":"bell.mp3","volume":0.7}}

// Haptic feedback
{"m":"haptic","p":{"pattern":"heartbeat","intensity":0.5}}

// Scene changes
{"m":"scene","p":{"location":"forest","transition":"fade"}}

// Visual effects
{"m":"effect","p":{"type":"particles","color":"blue"}}

// Avatar expressions
{"m":"expression","p":{"emotion":"happy","intensity":0.8}}

// Camera control
{"m":"camera","p":{"move":"zoom","target":"user","duration":2.0}}
```

### Complex Choreography Example

```json
Welcome to the meditation garden!
{"m":"scene","p":{"location":"garden","transition":"fade"}}
{"m":"pause","p":{"secs":2.0}}
{"m":"sound","p":{"file":"birds.mp3","volume":0.3}}

Let's begin our practice...
{"m":"animate","p":{"action":"sit","duration":2.0}}
{"m":"pause","p":{"secs":2.0}}

Notice the gentle breeze...
{"m":"effect","p":{"type":"wind","intensity":0.3}}
{"m":"haptic","p":{"pattern":"gentle_wave","intensity":0.2}}
```

## Performance Considerations

### Parsing Overhead
- Regex parsing: <1ms per response
- JSON parsing: <1ms per directive
- Negligible impact on response display

### Timing Accuracy
- Browser timers: ±16ms accuracy
- VR frameworks: ±1-2ms accuracy
- Sufficient for meditation/training apps

### Network Considerations
- Directives embedded in response: No extra requests
- Client-side execution: No server round-trips
- Offline capable once response received

## Use Cases by Industry

### Healthcare & Therapy
- Guided meditation sessions
- Breathing exercises for anxiety
- PTSD treatment protocols
- Physical therapy instructions
- Pain management techniques

### Education & Training
- Language learning with paced repetition
- Safety procedure walkthroughs
- Equipment operation tutorials
- Memory training exercises
- Public speaking practice

### Gaming & Entertainment
- Interactive storytelling
- Rhythm-based gameplay
- Dramatic scene pacing
- Character dialogue timing
- Tutorial sequences

### Fitness & Wellness
- Yoga flow instructions
- HIIT workout timing
- Stretching routines
- Dance choreography
- Martial arts forms

## Configuration

### Enabling for Specific Users

```python
# In request context
context = {
    "user_id": user_id,
    "response_format": "v0.3",  # Auto-enables directives
    "enable_directives": True,   # Explicit enable
    "directive_types": ["pause", "animate", "sound"]  # Future
}
```

### Persona-Specific Directives

```python
# In persona system_prompt
"You are Mu, a meditation guide...
When guiding exercises, use pause directives:
- Short pause (1-2s) between instructions
- Breathing pauses (4-6s) for inhale/exhale
- Longer pauses (10-30s) for meditation segments"
```

## Testing Directives

### Manual Testing

```bash
# Test with v0.3 API (directives enabled)
curl -X POST http://localhost:8666/api/v0.3/chat \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "messages": [
      {"role": "user", "content": "Guide me through a breathing exercise"}
    ]
  }'
```

### Automated Testing

```python
def test_directive_parsing():
    text = 'Breathe in... {"m":"pause","p":{"secs":4.0}} and out...'
    segments = parse_directives(text)
    
    assert len(segments) == 3
    assert segments[0]['type'] == 'text'
    assert segments[1]['type'] == 'directive'
    assert segments[1]['method'] == 'pause'
    assert segments[1]['params']['secs'] == 4.0
```

## Best Practices

### 1. Natural Integration
- Embed directives where natural pauses would occur
- Don't overuse - maintain conversation flow
- Consider the activity's rhythm

### 2. Appropriate Timing
- Breathing: 4-6 seconds per phase
- Instructions: 1-3 seconds between steps
- Dramatic effect: 0.5-2 seconds
- Meditation: 5-30 seconds for silence

### 3. User Control
- Allow users to adjust timing preferences
- Provide skip/speed controls
- Respect accessibility needs

### 4. Context Awareness
- Adjust timing for user's experience level
- Consider cultural differences in pacing
- Adapt to device capabilities (VR vs mobile)

## See Also
- [Chat Service Implementation](chat-service-implementation.md)
- [Persona System Guide](../services/persona-system-guide.md)
- [VR/AR Integration Guide](../../deployment/vr-ar-integration.md)

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

The directive system's implementation has been verified against the current codebase.

-   **✅ Core Concept and Implementation:**
    *   **Claim:** The system uses inline JSON-RPC commands, with the `pause` method (`{"m":"pause","p":{"secs":...}}`) being the current implementation.
    *   **Code Reference:** `app/services/chat/unified_chat.py` (within the `get_routing_prompt` method).
    *   **Verification:** This is **VERIFIED**. The `directive_section` string within the `get_routing_prompt` method explicitly defines the `pause` directive and its format, which is then added to the system prompt for the LLM.

-   **✅ Activation Logic:**
    *   **Claim:** Directives are enabled for the v0.3 API or when an `enable_directives` flag is set in the context.
    *   **Code Reference:** `app/services/chat/unified_chat.py` (the `_is_directive_enhanced_context` method).
    *   **Verification:** This is **VERIFIED**. The method checks for `context.get("response_format") == "v0.3"` or a truthy `context.get("enable_directives")`.

-   **✅ System Prompt Integration:**
    *   **Claim:** When directives are enabled, a `directive_section` is added to the system prompt.
    *   **Code Reference:** `app/services/chat/unified_chat.py` (the `get_routing_prompt` method).
    *   **Verification:** This is **VERIFIED**. The method constructs the final system prompt by combining the persona prompt with the tools section, which includes the directives.

**Overall Conclusion:** This document accurately describes the server-side implementation of the directive system. The logic for instructing the LLM to generate directives is correctly implemented in the `UnifiedChatHandler`. The actual execution of the directives is a client-side responsibility.