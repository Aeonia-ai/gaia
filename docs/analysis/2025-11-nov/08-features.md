# GAIA Platform Features

**Document Date:** 2025-11-20

---

## Core Platform

**Multi-Provider LLM Orchestration** — Claude, OpenAI, and other providers with intelligent routing. Simple queries take ~1s, complex ones take ~3s.

**Git-Synced Knowledge Base** — All game content (markdown + JSON) versioned in Git. Experiences, NPCs, items, quests defined as files.

**Real-Time State Sync** — NATS messaging publishes state changes, WebSocket delivers to Unity clients. Delta-based updates with version tracking.

**Supabase Authentication** — JWT tokens + API keys with mTLS between services. Dual auth for flexibility.

**Redis Caching** — 97% performance improvement on repeated queries. Persona caching, state caching.

---

## Experience System

**Fast Command Handlers** — Python handlers for deterministic actions: collect, drop, go, examine, inventory, give, use. Response time <10ms.

**LLM-Interpreted Commands** — For creative/narrative responses. Reads markdown game-logic files, calls Claude, parses response. 1-3 seconds.

**Admin Commands** — @ prefix bypasses LLM entirely. @examine, @where, @edit, @reset-experience. Response time <30ms.

**Server-Authoritative State** — world.json is the source of truth. Incremental `_version` counter for delta sync. File locking for concurrent access.

**Shared vs Isolated** — Multiplayer experiences use shared world state with locking. Single-player gets isolated copy per player.

---

## World Structure

**Zone > Area > Spot > Items** — GPS zones contain logical areas, areas contain AR anchor spots, spots contain items and NPCs.

**Template-Instance Pattern** — Items reference templates (blueprints) via template_id, have unique instance_id for tracking. TemplateLoader merges at runtime.

**Version-Based Delta Sync** — Each change increments version. Clients track their version. Deltas include base_version and snapshot_version so Unity knows if it can apply or needs fresh state.

---

## NPC & Quests

**NPC Dialogue** — Talk to NPCs using natural language. LLM generates in-character responses based on persona definition.

**Persona System** — Character personalities stored in database. System prompts define behavior, knowledge, speech patterns.

**Quest Tracking** — Quests have lifecycle: offered → active → completed/failed. Stored in player view with objectives and progress.

**Trust System** — Per-player relationship score with each NPC. Higher trust unlocks new dialogue options and quests.

---

## AR/GPS

**GPS-Based Filtering** — Haversine distance calculation filters waypoints by proximity. Returns only nearby points of interest.

**AR Waypoints** — 37 defined waypoints in Wylding Woods. Each has GPS coordinates, AR anchor data, associated content.

**Unity Integration** — WebSocket protocol v0.4. JSON messages for actions, world_update events for state changes.

---

## Asset Generation

**Image Generation** — Midjourney, DALL-E, Stability AI integrations for generating game art.

**3D Model Generation** — Meshy API for generating 3D models from text descriptions.

**Audio Generation** — OpenAI TTS for NPC speech, Freesound for sound effects.

---

## Admin/World Building

**@examine [type] [id]** — Inspect any object in world state. Shows full JSON data.

**@where [type] [name]** — Find objects by name or type. Returns locations.

**@edit [type] [id] [field] [value]** — Modify object properties in real-time.

**@reset-experience CONFIRM** — Reset world to pristine template state.

---

## Current Experience: Wylding Woods

**Setting** — Magical shop (Woander's) with fairy tale AR experience.

**NPCs** — Louisa the Dream Weaver fairy (primary), Woander the shopkeeper, Neebling the trickster.

**Quest** — Collect scattered dream bottles, return them to fairy houses.

**Demo Result** — Received applause at Woander store demonstration!

---

## Planned Features

**Live Transform Editing** — Change spot positions/rotations from admin commands, see updates in Unity immediately.

**Experience SDK** — Declarative Python API to define new experiences without deep platform knowledge.

**Multiple NPC Support** — Currently hardcoded to Louisa. Need to remove kludge to enable any NPC.

**Markdown-Driven Fast Handlers** — Parse game-logic/*.md at startup to reduce LLM calls for known patterns.

---

## Performance Tiers

The architecture separates operations into speed tiers:

**Tier 1: Admin Commands (<30ms)**
- Deterministic, no LLM
- World building operations
- Debugging and inspection

**Tier 2: Fast Handlers (<10ms)**
- Python handlers for game actions
- State reads and writes
- Real-time gameplay

**Tier 3: LLM Path (1-3 seconds)**
- Creative/narrative responses
- Complex reasoning
- NPC dialogue generation

This pattern balances responsiveness with AI capability—deterministic game logic runs instantly while reserving AI for genuinely creative moments.

---

## Technology Stack

**Backend**
- Python 3.11 + FastAPI
- PostgreSQL + Redis
- NATS messaging
- Docker Compose

**Authentication**
- Supabase (primary)
- JWT + API keys
- mTLS between services

**AI/ML**
- Anthropic Claude (primary LLM)
- OpenAI (fallback + TTS)
- ChromaDB (semantic search)

**Client**
- Unity 2022 LTS
- AR Foundation
- WebSocket client

**Infrastructure**
- Fly.io (deployment)
- GitHub (source + KB sync)
- Supabase (auth + storage)
