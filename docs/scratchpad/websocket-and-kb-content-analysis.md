# WebSocket and KB Content Analysis for Wylding Woods

## WebSocket Authentication and Service Trace

The WebSocket implementation in the KB service includes a robust authentication check using JWTs. Here's a step-by-step trace of the flow:

1.  **Client Connects with JWT:** A client initiates a connection to the `/ws/experience` endpoint, passing a valid JWT as a query parameter (e.g., `ws://<server>/ws/experience?token=<jwt_token>`).

2.  **Endpoint Receives Connection:** The `@router.websocket("/ws/experience")` function in `app/services/kb/websocket_experience.py` receives the request.

3.  **Authentication is Performed:** The endpoint immediately calls `get_current_user_ws(websocket, token)`.

4.  **JWT Validation (`get_current_user_ws`):** This function, located in `app/shared/security.py`, handles the authentication:
    *   It verifies the presence of the token.
    *   It attempts to retrieve a cached validation result from Redis.
    *   If not cached, it decodes the JWT using `SUPABASE_JWT_SECRET`, verifying its signature, expiration, and audience.
    *   Invalid tokens result in the WebSocket being closed with a `1008` error code.
    *   Valid tokens are cached, and their payload (including `user_id`) is returned.

5.  **Connection Accepted and Managed:**
    *   Upon successful authentication, the `websocket_experience_endpoint` calls `experience_manager.connect(...)` with the `user_id`.
    *   The `ExperienceConnectionManager` (`app/services/kb/experience_connection_manager.py`) accepts and stores the connection, linking it to the `user_id`.

6.  **Message Handling:**
    *   The server enters the `handle_message_loop`, processing incoming JSON messages from the client.
    *   Messages (e.g., `{"type": "action", "action": "collect_bottle", ...}`) are routed to appropriate handlers like `handle_action`.

7.  **KB Service Interaction:**
    *   Functions like `handle_collect_bottle` retrieve the `state_manager` from `kb_agent`.
    *   They then call `state_manager.update_player_view(...)` with the `user_id` and state changes, directly interacting with the core KB service logic to modify the game state for the authenticated user.

This flow ensures secure, authenticated communication and direct interaction with the game state managed by the KB service.

## Game Command Organization for `wylding-woods`

The game commands for the `wylding-woods` experience are structured as individual Markdown files within the `/kb/experiences/wylding-woods/game-logic/` directory. Each file defines the logic for a specific player action:

*   `collect.md`: Logic for picking up or collecting items.
*   `go.md`: Logic for player movement between locations.
*   `inventory.md`: Logic for managing the player's inventory.
*   `look.md`: Logic for observing the environment or items.
*   `talk.md`: Logic for interacting with characters.

This modular, Markdown-driven approach allows the KB service's LLM to dynamically interpret and execute game rules based on player input.

## `wylding-woods` Capabilities and Experience Details

The `config.json` file for the `wylding-woods` experience (`/kb/experiences/wylding-woods/config.json`) provides the following details:

*   **ID:** `wylding-woods`
*   **Name:** "The Wylding Woods"
*   **Description:** "AR fairy tale adventure with shared world state and GPS-based waypoints"
*   **State Management:**
    *   `model`: `shared`
    *   `coordination`: `locking_enabled: true`, `lock_timeout_ms: 5000`, `optimistic_versioning: true`
    *   `persistence`: `auto_save: true`, `save_interval_s: 30`, `backup_enabled: false`
*   **Multiplayer:**
    *   `enabled`: `true`
    *   `max_concurrent_players`: `null`
    *   `player_visibility`: `location`
    *   `shared_entities`: `true`
    *   `entity_ownership`: `first_interaction`
*   **Bootstrap:**
    *   `player_starting_location`: `woander_store`
    *   `player_starting_inventory`: `[]`
    *   `initialize_world_on_first_player`: `false`
*   **Content Paths:**
    *   `templates_path`: `templates/`
    *   `state_path`: `state/`
    *   `game_logic_path`: `game-logic/`
    *   `markdown_enabled`: `true`
    *   `hierarchical_loading`: `true`
*   **Capabilities:**
    *   `gps_based`: `true` (Utilizes GPS for location-based interactions and waypoints)
    *   `ar_enabled`: `true` (Designed for Augmented Reality experiences)
    *   `voice_enabled`: `false`
    *   `inventory_system`: `true`
    *   `quest_system`: `true`
    *   `combat_system`: `false` (No combat mechanics in this experience)
