# Architectural Overview: KB's Distributed Simulation & State Management

---

**📊 Note on Metrics**: Any performance numbers or latency projections mentioned in this document are **illustrative examples** for architectural discussion, NOT based on actual testing or measurements. System behavior depends on LLM provider response times, network conditions, hardware specifications, and deployment configuration. Treat all metrics as directional guidance for understanding architectural trade-offs.

---

The Aeonia Knowledge Base (KB) employs a unique, distributed approach to "simulation" and world state management, diverging from traditional monolithic simulation engines. Its architecture is characterized by a symbolic server (GAIA) issuing directives, a client-side (Unity) system responsible for physical resolution and spatial intelligence, and a markdown-driven game logic layer.

## 1. Core Principles:

*   **Symbolic Server Authority:** GAIA maintains the high-level, symbolic state of the world and its entities. It does not perform real-time physics or complex environmental simulations. Instead, it issues abstract directives to clients.
*   **Client-Side Physical Resolution:** The Unity client is responsible for translating GAIA's symbolic directives into concrete, physically resolved actions within the game world. This offloads computationally intensive tasks from the server.
*   **Markdown-Driven Game Logic:** Game rules, interactions, and state transitions are defined in human-readable markdown files, interpreted and executed by an LLM. This provides a flexible, content-driven approach to game design.
*   **Event-Driven Communication:** Server-Sent Events (SSE) facilitate real-time, unidirectional streaming of LLM responses and state updates from GAIA to connected clients.

## 2. Key Architectural Components & Interactions:

### GAIA (Server):
*   **Symbolic State Management:** Stores and manages the abstract state of entities (e.g., `entity_id`, `goal`).
*   **Directive Emitter:** Generates and sends high-level commands to clients (e.g., `{"entity_id":"bottle_of_joy","goal":"instantiate_at_spot","spot_id":"ww_store.shelf_a.slot_3"}`).
*   **Markdown Logic Execution:** Utilizes an LLM to interpret and execute game logic defined in markdown files, leading to state changes and new directives.
*   **SSE Streaming:** Pushes real-time LLM responses and metadata to clients.
*   **State Reconciliation:** Receives acknowledgement payloads from clients to keep its symbolic state accurate based on client-side physical resolution outcomes.

### Unity Client:
*   **Woander Session Handshake:** Initiates communication by reporting its capabilities (build, venue, registry revision, anchoring capabilities).
*   **Spot Registry Resolver:** Locally resolves "Spots" which carry all physical context (anchoring hints, bounding volumes, interaction affordances). This registry is crucial for client-side understanding of the physical world.
*   **Runtime Resolution Engine:** Executes ordered strategies (VPS, GPS, relative, procedural fallbacks) to physically place entities based on GAIA's directives and the Spot Registry. It validates occupancy against registered bounding volumes.
*   **Spatial Intelligence Layer:** Utilizes the Spot Registry and local spatial data (meshes, planes) to drive client-side behaviors such as placement, collision checks, and interactions.
*   **Acknowledgement Payload:** Reports the outcome of physical resolution back to GAIA, ensuring server-side symbolic state accuracy.
*   **Behavior Wiring:** Spawns prefabs and wires behaviors based on successful physical resolution.

### Markdown Game Logic Files:
*   Structured markdown documents (`.md` files) defining game rules, intent detection, input parameters, state access, execution logic, state updates, and response formats.
*   These are the "code" for game mechanics, interpreted by the LLM on GAIA.

### Spot Registry:
*   A critical data structure (likely client-side cached, server-managed) containing detailed physical context for all interactive locations and objects in the world.
*   Enables clients to perform local physical resolution without constant server queries for granular spatial data.

## 3. The Nuance of "Simulation":

In this architecture, "simulation" is not a single, centralized process. Instead, it's a **distributed, hybrid model**:

*   **Symbolic Simulation (Server):** GAIA simulates the narrative and logical progression of the world through markdown-driven game logic and symbolic state updates.
*   **Physical Simulation (Client):** The Unity client simulates the physical presence, placement, and immediate interactions of entities within the 3D environment, guided by server directives and local spatial data.

This design allows for a highly flexible and scalable system where the server focuses on narrative and high-level game state, while clients handle the visual and physical fidelity, reporting back critical outcomes to maintain server-side consistency.

---

## 4. Latency & Responsiveness in Distributed Simulation

The distributed simulation model creates unique latency considerations, particularly for VR/AR experiences requiring sub-second responsiveness:

### **Perceived vs. Actual Latency**

**Actual Latency**: Total time from user action to complete response
```
User clicks bottle → Server processes → Narrative arrives
Projected Total: ~2-5 seconds (based on LLM API response times)
```

**Perceived Latency**: Time until user sees *any* feedback
```
User clicks bottle → Visual update (bottle disappears)
Projected: Sub-100ms (based on NATS pub/sub architecture)
```

### **Achieving Low Perceived Latency**

The architecture prioritizes perceived latency through:

1. **Immediate Visual Feedback** (NATS world updates):
   - KB Service publishes state changes to NATS immediately after applying updates
   - Chat Service streams `world_update` events to client via SSE
   - Client updates 3D scene before narrative arrives
   - **Projected Result**: Sub-100ms perceived latency (based on NATS messaging patterns)

2. **Asynchronous Narrative Delivery** (SSE streaming):
   - Narrative generation happens in parallel with visual updates
   - Client displays text progressively as it streams
   - Users tolerate multi-second narrative delays if visuals respond instantly
   - **Design Principle**: Visual changes feel instant, narrative provides context

3. **Client-Side Prediction** (optional, future):
   - Unity client can predict outcomes locally (optimistic UI)
   - Server confirms or corrects prediction via world_update
   - **Trade-off**: Requires rollback logic for incorrect predictions

### **Projected Latency Budget Breakdown** *(architectural estimate)*

For a "take bottle" interaction:
```
   0ms - User clicks bottle in Unity
 ~10ms - HTTP request to Gateway (local network)
 ~20ms - Gateway → KB Service (Docker internal network)
 ~50ms - KB Service processes command, updates state
 ~60ms - NATS publish (world_update)
 ~70ms - Chat Service receives NATS event
 ~80ms - SSE event sent to client
~100ms - Client receives world_update, bottle disappears ✅

[User sees visual change - feels instant!]

~1500ms - Pass 1 LLM completes (logic) - varies with API
~3500ms - Pass 2 LLM completes (narrative) - varies with API
~3520ms - Narrative SSE event arrives
        - Client displays: "You pick up the bottle..." ✅

**Important**: These timings are projected based on architectural patterns
and typical system behaviors, NOT actual measurements. Production latency
depends on:
- Geographic distance (client → server → LLM API)
- LLM provider API response times (highly variable)
- Network quality and congestion
- Server load and concurrent user count
```

**Key Architectural Insight**: The projected ~100ms visual update is what makes
the experience feel responsive, even though full narrative takes longer. This is
why NATS world updates are critical for VR/AR experiences - they optimize the
metric that matters most to user perception.

### **Validation Approach**

To measure actual latency in your deployment:

```javascript
// Client-side measurement
const actionStart = Date.now();

// On world_update event
const visualLatency = Date.now() - actionStart;
console.log(`Visual feedback latency: ${visualLatency}ms`);

// On narrative content event
const narrativeLatency = Date.now() - actionStart;
console.log(`Narrative latency: ${narrativeLatency}ms`);
```

**Recommendation**: Establish baseline metrics in your specific environment
before making optimization decisions. Projected numbers provide architectural
understanding, but actual performance varies significantly with deployment
specifics.
