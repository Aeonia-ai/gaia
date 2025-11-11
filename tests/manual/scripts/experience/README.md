# Experience WebSocket Testing Scripts

**Location**: `scripts/experience/`
**Purpose**: Validated WebSocket test scripts for v0.4 WorldUpdate implementation
**Created**: 2025-11-10
**Status**: ✅ Validated against local server (localhost:8001)

---

## Overview

These scripts test the WebSocket experience system with proper timeout handling for LLM-driven command processing (25-30 second response times).

**Key Requirements**:
- JWT token in `/tmp/jwt_token.txt`
- Local server running on `localhost:8001`
- Python 3.11+ with `websockets` library
- 60-second timeouts for action commands

---

## Quick Start

### Prerequisites

```bash
# 1. Start local server
docker compose up

# 2. Generate JWT token
python3 tests/manual/get_test_jwt.py > /tmp/jwt_token.txt

# 3. Install dependencies (if needed)
pip install websockets
```

### Run Tests

```bash
# Main v0.4 WorldUpdate test (recommended)
./scripts/experience/test_websocket_v04.py

# Simple quick test
./scripts/experience/test_websocket_v04_simple.py

# Debug test (minimal, focused)
./scripts/experience/test_websocket_debug.py

# Hybrid test (HTTP + WebSocket)
./scripts/experience/test_websocket_hybrid.py
```

---

## Test Scripts

### 1. `test_websocket_v04.py` ⭐ MAIN TEST

**Purpose**: Complete v0.4 WorldUpdate validation with proper timeouts

**What it tests**:
- WebSocket connection and authentication
- Navigation: "go to spawn_zone_1"
- Collection: "collect dream bottle"
- v0.4 WorldUpdate event format validation

**Expected runtime**: 60-90 seconds (includes LLM processing)

**Usage**:
```bash
./scripts/experience/test_websocket_v04.py
```

---

### 2. `test_websocket_v04_simple.py`

**Purpose**: Simplified test focusing on core flow

**What it tests**:
- Basic connection
- Look command
- Navigation command
- Collection command
- WorldUpdate event

**Usage**:
```bash
./scripts/experience/test_websocket_v04_simple.py
```

---

### 3. `test_websocket_debug.py`

**Purpose**: Minimal debug test for troubleshooting

**What it tests**:
- Connection only
- Ping/pong
- Single collect action with 60s timeout

**Usage**:
```bash
./scripts/experience/test_websocket_debug.py
```

---

### 4. `test_websocket_hybrid.py`

**Purpose**: Test HTTP action trigger + WebSocket event listening

**What it tests**:
- WebSocket connection (for events)
- HTTP POST to `/experience/interact` (triggers action)
- WebSocket receives world_update event

**Usage**:
```bash
./scripts/experience/test_websocket_hybrid.py
```

---

## Related Documentation

**Testing**:
- `docs/scratchpad/testing-organization-plan.md` - How WebSocket testing is organized
- `docs/scratchpad/websocket-test-results-v04.md` - Expected results and known issues

**Implementation**:
- `docs/scratchpad/WORLD-UPDATE-AOI-ALIGNMENT-ANALYSIS.md` - v0.4 design decisions
- `docs/scratchpad/websocket-aoi-client-guide.md` - Protocol specification
- `docs/scratchpad/markdown-command-architecture.md` - How commands work

**Contact**: Report issues in Symphony `websockets` room

**Last Updated**: 2025-11-10
