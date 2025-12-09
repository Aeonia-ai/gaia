# Agent Interface Vision

**Status:** Living Document
**Created:** 2025-12-09
**Implementation:** [AEO-72 Single Chat Design](../../../scratchpad/aeo-72-single-chat-design.md)

## Overview

The Agent Interface is the primary way users interact with Gaia. It starts as a text chat but is designed to evolve into a multi-modal conversational interface supporting voice, visual generation, and mixed reality experiences.

## Core Concept

One persistent conversation per user that serves as the "agent interface" - similar to Claude Code or other AI assistants. This single conversation is backed by:

- **Memory:** Persistent conversation history
- **User tracking:** Preferences, context, state
- **Subagent capabilities:** Specialized tools and agents behind the scenes
- **Multi-modal output:** Text, images, audio, interactive elements

## Interface Modes

| Mode | Primary Input | Primary Output | Visual Elements |
|------|--------------|----------------|-----------------|
| **Text Chat** (current) | Keyboard | Text stream | Chat bubbles |
| **Voice Conversation** | Voice/mic | Audio + Text | Minimal during speech |
| **Visual Generation** | Text or Voice | Images/media + text | Dynamic content area |
| **Mixed/AR** | Gesture + Voice | Spatial + Audio | Overlays, 3D elements |

## Architectural Principles

### 1. Content Area Flexibility

The main content area should not be hardcoded to "chat bubbles only". It should support:

- Scrolling text messages
- Inline generated images
- Video/audio players
- Interactive canvases
- 3D/spatial content (future)

### 2. Sidebar as Optional Slot

Sidebars will be reintroduced as we discover new UI affordances. The sidebar should be:

- Hidden by default (CSS, not removed)
- Available for: tools, context panels, generated media, settings
- Slide-in capable for progressive disclosure

### 3. Swappable Input Components

The input area should be modular:

- Text input (current)
- Voice input with mic button and waveform
- Combined text + voice
- Gesture/touch for AR modes

### 4. Minimal, Consistent Header

Across all modes, the header should be:

- Gaia branding
- User info
- Essential controls (logout, settings)
- Unobtrusive

## Layout Template

```
┌─────────────────────────────────────────────────┐
│  Header                                         │
│  [Logo] [Brand]              [User] [Controls]  │
├─────────────────────────────────────────────────┤
│                                                 │
│              CONTENT AREA                       │
│         (flexible, mode-dependent)              │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Messages / Media / Interactive Content  │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
├─────────────────────┬───────────────────────────┤
│   SIDEBAR (opt)     │                           │
│   - hidden default  │                           │
│   - future tools    │                           │
└─────────────────────┴───────────────────────────┘
│  INPUT AREA (swappable)                         │
│  [Text input] [Send] or [Mic] [Waveform]        │
└─────────────────────────────────────────────────┘
```

## Mobile Considerations

- Voice interfaces are often mobile-first
- Sidebar hidden by default helps mobile
- Input area should adapt to screen size
- Consider thumb-reachable zones for controls

## Future Capabilities

### Voice Mode
- Push-to-talk or wake word
- Real-time transcription display
- Audio response playback
- Visual feedback during listening/speaking

### Visual Generation
- AI-generated images inline with conversation
- Gallery/carousel for multiple images
- Full-screen view option
- Download/share capabilities

### Memory & Context
- Conversation history sidebar
- User preferences panel
- Context/state visualization
- Memory management tools

### Subagents
- Specialized agent selection
- Tool availability indicators
- Agent handoff visualization
- Capability discovery

## Implementation Phases

### Phase 1: Single Chat (AEO-72) - Current
- Feature-flagged single conversation UI
- Text input/output
- Hidden sidebar slot
- Mobile responsive

### Phase 2: Voice Input (Future)
- Mic button in input area
- Speech-to-text integration
- Audio playback for responses

### Phase 3: Visual Output (Future)
- Inline image rendering
- Generated media support
- Rich content types

### Phase 4: Full Multi-Modal (Future)
- Combined voice + text + visual
- AR/spatial interfaces
- Advanced interaction patterns

## Related Documents

- [AEO-72 Implementation](../../../scratchpad/aeo-72-single-chat-design.md) - Current implementation work
- [Chat Service Implementation](../../../reference/chat/chat-service-implementation.md) - Backend architecture
- [Streaming API Guide](../../../reference/api/streaming/streaming-api-guide.md) - SSE streaming

## Design Principles Summary

1. **Content is king** - Maximize space for conversation/output
2. **Progressive disclosure** - Start minimal, reveal as needed
3. **Mode-agnostic structure** - Layout works for text, voice, visual
4. **Mobile-first** - Design for constrained screens first
5. **Future-ready** - Build hooks for capabilities we know are coming
