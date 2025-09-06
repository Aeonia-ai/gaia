# KB Wiki Interface Mockup

## 1. Wiki Home Page (`/wiki`)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🏠 Gaia Platform                          💬 Chat  📚 Wiki  ⚙️ Settings  👤 User │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   📚 Knowledge Base                                                             │
│   ━━━━━━━━━━━━━━━━━━━                                                             │
│                                                                                 │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│   │  📄 1,247       │  │  🔗 3,892       │  │  ✏️ 23          │               │
│   │     Pages       │  │     Links       │  │  Recent Edits   │               │
│   │  [Browse All]   │  │  [View Graph]   │  │  [View Changes] │               │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘               │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────┐ 🔍 Search    │
│   │ Search knowledge base...                                   │ [    Go    ]  │
│   └─────────────────────────────────────────────────────────────┘               │
│                                                                                 │
│   📁 Browse by Category                                                         │
│   ━━━━━━━━━━━━━━━━━━━━━━                                                         │
│   ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ │
│   │ 🏗️ Gaia        │ │ 💭 Consciousness│ │ 🎮 MMOIRL      │ │ 📊 Project     │ │
│   │   Architecture │ │   Research      │ │   Design       │ │   Status       │ │
│   │   [42 pages]   │ │   [156 pages]   │ │   [89 pages]   │ │   [23 pages]   │ │
│   └────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘ │
│                                                                                 │
│   📝 Recent Changes                                                             │
│   ━━━━━━━━━━━━━━━━━━                                                             │
│   • gaia/specs/kb-integration.md - Updated MCP tools section (2 min ago)       │
│   • influences/consciousness/embodiment.md - Added new research (1 hour ago)   │
│   • mmoirl/game-mechanics/consciousness.md - Initial draft (3 hours ago)       │
│   • gaia/architecture/overview.md - Performance updates (1 day ago)            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. File Browser View (`/wiki/browse/gaia`)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🏠 Gaia Platform                          💬 Chat  📚 Wiki  ⚙️ Settings  👤 User │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  📁 Home > gaia                                                                 │
│  ━━━━━━━━━━━━━━━                                                                 │
│                                                                                 │
│  📄 New Page  📁 New Folder  ┌──────────────────────┐                          │
│                               │ Filter files...      │                          │
│                               └──────────────────────┘                          │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────┐ ┌───────────────┐ │
│  │ 📁 architecture/                          2024-01-16    │ │ 📊 Directory  │ │
│  │ 📁 specs/                                 2024-01-15    │ │    Info       │ │
│  │ 📁 implementation/                        2024-01-14    │ │ ━━━━━━━━━━━━━ │ │
│  │ 📄 README.md                              2024-01-13    │ │ 📁 3 folders  │ │
│  │ 📄 roadmap.md                             2024-01-12    │ │ 📄 2 files    │ │
│  │                                                         │ │ 📅 Last edit: │ │
│  │                                                         │ │    2 hrs ago  │ │
│  │                                                         │ │               │ │
│  │                                                         │ │ 🔗 Related    │ │
│  │                                                         │ │ ━━━━━━━━━━━━━ │ │
│  │                                                         │ │ • influences/ │ │
│  │                                                         │ │ • mmoirl/     │ │
│  │                                                         │ │ • status/     │ │
│  └─────────────────────────────────────────────────────────┘ └───────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Wiki Page View (`/wiki/page/gaia/specs/api-design`)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🏠 Gaia Platform                          💬 Chat  📚 Wiki  ⚙️ Settings  👤 User │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ API Design Specification                        ✏️ Edit  📋 History  🔗 Links │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ ┌─────────────────────────────────────────────────┐ ┌─────────────────────────┐ │
│ │ # API Design Specification                      │ │ 📊 Page Info            │ │
│ │                                                 │ │ ━━━━━━━━━━━━━━━━━━━━━━━ │ │
│ │ ## Overview                                     │ │ Last modified:          │ │
│ │                                                 │ │ 2024-01-16 14:30        │ │
│ │ This document outlines the API design for the  │ │                         │ │
│ │ Gaia platform, focusing on the [[gaia/         │ │ Author: jason.asbahr    │ │
│ │ architecture/microservices]] approach.         │ │                         │ │
│ │                                                 │ │ Size: 2,847 chars      │ │
│ │ ## Core Principles                              │ │                         │ │
│ │                                                 │ │ 🔗 Referenced By        │ │
│ │ 1. **RESTful Design**: Following REST          │ │ ━━━━━━━━━━━━━━━━━━━━━━━ │ │
│ │    principles for all endpoints                 │ │ • gaia/implementation/  │ │
│ │ 2. **Backward Compatibility**: Must work       │ │   gateway-service       │ │
│ │    with existing [[LLM Platform]] clients      │ │ • gaia/architecture/    │ │
│ │ 3. **Performance**: Sub-100ms response times   │ │   overview              │ │
│ │                                                 │ │ • mmoirl/integration/   │ │
│ │ ## Authentication                               │ │   api-integration       │ │
│ │                                                 │ │                         │ │
│ │ The API uses JWT tokens for user auth and      │ │ 🎯 Related              │ │
│ │ API keys for service-to-service calls, as      │ │ ━━━━━━━━━━━━━━━━━━━━━━━ │ │
│ │ described in [[gaia/specs/auth-design]].       │ │ • Database Schema       │ │
│ │                                                 │ │ • Error Handling        │ │
│ │ ## Endpoints                                    │ │ • Rate Limiting         │ │
│ │                                                 │ │                         │ │
│ │ ### Chat Endpoints                              │ │                         │ │
│ │ - `POST /api/v0.2/chat/completions`           │ │                         │ │
│ │ - `GET /api/v0.2/chat/history`                 │ │                         │ │
│ │                                                 │ │                         │ │
│ └─────────────────────────────────────────────────┘ └─────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 4. Edit Mode (`/wiki/edit/gaia/specs/api-design`)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🏠 Gaia Platform                          💬 Chat  📚 Wiki  ⚙️ Settings  👤 User │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ ✏️ Editing: API Design Specification         💾 Save  👁️ Preview  ❌ Cancel    │
│                                                                                 │
│ B I 🔗 📷 📝 │ [Insert Template ▼]                                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                                 │
│ ┌─────────────────────────────────────────┐ ┌─────────────────────────────────┐ │
│ │ # API Design Specification              │ │ # API Design Specification      │ │
│ │                                         │ │                                 │ │
│ │ ## Overview                             │ │ ## Overview                     │ │
│ │                                         │ │                                 │ │
│ │ This document outlines the API design   │ │ This document outlines the API  │ │
│ │ for the Gaia platform, focusing on the │ │ design for the Gaia platform,   │ │
│ │ [[gaia/architecture/microservices]]     │ │ focusing on the microservices   │ │
│ │ approach.                               │ │ approach.                       │ │
│ │                                         │ │                                 │ │
│ │ ## Core Principles                      │ │ ## Core Principles              │ │
│ │                                         │ │                                 │ │
│ │ 1. **RESTful Design**: Following REST   │ │ 1. **RESTful Design**: Following│ │
│ │    principles for all endpoints         │ │    REST principles for all      │ │
│ │ 2. **Backward Compatibility**: Must     │ │    endpoints                    │ │
│ │    work with existing [[LLM Platform]]  │ │ 2. **Backward Compatibility**:  │ │
│ │    clients                              │ │    Must work with existing LLM │ │
│ │ 3. **Performance**: Sub-100ms response  │ │    Platform clients             │ │
│ │    times                                │ │ 3. **Performance**: Sub-100ms   │ │
│ │                                         │ │    response times               │ │
│ │ ## Authentication                       │ │                                 │ │
│ │                                         │ │ ## Authentication               │ │
│ │ The API uses JWT tokens for user auth   │ │                                 │ │
│ │ and API keys for service-to-service     │ │ The API uses JWT tokens for     │ │
│ │ calls, as described in [[gaia/specs/    │ │ user auth and API keys for      │ │
│ │ auth-design]].                          │ │ service-to-service calls, as    │ │
│ │                                         │ │ described in auth-design.       │ │
│ │ ▌                                       │ │                                 │ │
│ └─────────────────────────────────────────┘ └─────────────────────────────────┘ │
│   Markdown Editor                           Live Preview                        │
│                                                                                 │
│ 💾 Auto-saved draft 30 seconds ago                                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 5. Search Results (`/wiki/search?q=consciousness`)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🏠 Gaia Platform                          💬 Chat  📚 Wiki  ⚙️ Settings  👤 User │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 🔍 Search Results for 'consciousness'                                          │
│ Found 27 results                                                               │
│                                                                                 │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ [Search]       │
│ │ consciousness    │ │ philosophy,ai    │ │ jason.asbahr     │               │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘               │
│   Search terms       Tags (comma-sep)     Author                              │
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ 💭 Consciousness Framework v2                                               │ │
│ │ "...framework for implementing digital consciousness using the principles   │ │
│ │ of embodied cognition and phenomenological awareness..."                    │ │
│ │ 📁 influences/consciousness/framework-v2.md  📅 2024-01-15  #philosophy #ai │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ 🎮 MMOIRL Consciousness Integration                                         │ │
│ │ "...how to integrate consciousness mechanics into the game world to create  │ │
│ │ meaningful player experiences and emergent narrative..."                    │ │
│ │ 📁 mmoirl/game-mechanics/consciousness.md  📅 2024-01-14  #game-design #ai  │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ 🧠 Embodied AI Research Notes                                               │ │
│ │ "...exploring the relationship between consciousness, embodiment, and AI    │ │
│ │ systems through phenomenological analysis..."                               │ │
│ │ 📁 influences/consciousness/embodiment.md  📅 2024-01-13  #research #theory │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ ... 24 more results                                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 6. Knowledge Graph Visualization (`/wiki/graph`)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🏠 Gaia Platform                          💬 Chat  📚 Wiki  ⚙️ Settings  👤 User │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 🕸️ Knowledge Graph                                                             │
│                                                                                 │
│ [All Pages ▼] 🔍 Focus  📸 Export                                              │
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ ┌───────────┐ │
│ │                    ●──── consciousness ────●                │ │ 🎯 Node   │ │
│ │                   ╱                        ╲               │ │   Details │ │
│ │              embodiment                  phenomenology     │ │ ━━━━━━━━━ │ │
│ │                 ╱                            ╲             │ │           │ │
│ │            ●───────────────●                   ●           │ │ Selected: │ │
│ │         game-design    mmoirl              gaia-arch      │ │ API Design│ │
│ │            ╱               ╲                   ╱           │ │           │ │
│ │      ●─────●           ●─────●─────●─────●─────●           │ │ Links to: │ │
│ │   character       narrative   chat   auth   microservices │ │ • Auth    │ │
│ │   creation           engine   service service     ╲       │ │ • Gateway │ │
│ │                                                    ●      │ │ • Chat    │ │
│ │                                                database   │ │           │ │
│ │                                                           │ │ Links fr: │ │
│ │                                                           │ │ • Overview│ │
│ │                                                           │ │ • Impl    │ │
│ │                                                           │ │           │ │
│ │                                                           │ │ 📊 Stats  │ │
│ │                                                           │ │ ━━━━━━━━━ │ │
│ │                                                           │ │ 1,247 pgs │ │
│ │                                                           │ │ 3,892 lnks│ │
│ │                                                           │ │ 5 clusters│ │
│ └─────────────────────────────────────────────────────────────┘ └───────────┘ │
│                                                                                 │
│ Click nodes to focus • Drag to explore • Hover for details                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 7. Chat Integration (Enhanced chat with KB references)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🏠 Gaia Platform                          💬 Chat  📚 Wiki  ⚙️ Settings  👤 User │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 💬 Chat with Gaia                                                              │
│                                                                                 │
│ 📚 Browse KB  🔍 Search KB  📝 Create Page                                     │
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ 👤 You: Tell me about our consciousness framework                            │ │
│ │                                                                             │ │
│ │ 🤖 Gaia: I can help you with the consciousness framework! Based on the KB,  │ │
│ │ we have several related documents:                                          │ │
│ │                                                                             │ │
│ │ ┌───────────────────────────────────────────────────────────────────────┐   │ │
│ │ │ 💭 Consciousness Framework v2                                         │   │ │
│ │ │ A comprehensive framework for implementing digital consciousness...   │   │ │
│ │ │ 📁 influences/consciousness/framework-v2.md                           │   │ │
│ │ └───────────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                             │ │
│ │ ┌───────────────────────────────────────────────────────────────────────┐   │ │
│ │ │ 🧠 Embodied AI Research                                               │   │ │
│ │ │ Research notes on embodiment and consciousness in AI systems...       │   │ │
│ │ │ 📁 influences/consciousness/embodiment.md                             │   │ │
│ │ └───────────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                             │ │
│ │ The framework focuses on phenomenological awareness and embodied cognition. │ │
│ │ Would you like me to explain any specific aspect?                           │ │
│ │                                                                             │ │
│ │ 👤 You: Update the framework doc with our latest research                   │ │
│ │                                                                             │ │
│ │ 🤖 Gaia: I'll help you update the consciousness framework document. Let me │ │
│ │ open it for editing and we can review the latest research together.        │ │ │
│ │                                                                             │ │
│ │ [Document opened in edit mode - /wiki/edit/influences/consciousness/       │ │
│ │ framework-v2.md]                                                            │ │
│ │                                                                             │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Type your message...                                                  Send  │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Key Visual Features:

1. **Consistent Navigation**: Same header with chat/wiki tabs
2. **Rich File Browser**: Tree view with metadata sidebar
3. **Clean Page View**: Content + backlinks + related pages
4. **Split-Screen Editor**: Live preview with formatting tools
5. **Smart Search**: Filtered results with excerpts and metadata
6. **Interactive Graph**: D3.js visualization with node details
7. **Chat Integration**: KB references shown as cards in chat

The design maintains FastHTML's clean aesthetic while adding powerful wiki features that feel natural and intuitive!