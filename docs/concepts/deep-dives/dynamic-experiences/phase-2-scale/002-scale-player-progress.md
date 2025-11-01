# Player Progress Storage Architecture

> **Purpose**: Storage strategy for player progress, state, and analytics
> **Status**: DESIGN PHASE
> **Created**: 2025-10-24
> **Related**:
> - [Experience Platform Architecture](./+experiences.md) - Overall architecture
> - [Database Architecture](../database/database-architecture.md) - General database design
> - [Experience Data Models](./experience-data-models.md) - Database schemas

## Problem Statement

Track player progress across interactive experiences:
- **Current state** - Where player is, what they have, active quests
- **Historical events** - Waypoints visited, achievements unlocked, actions taken
- **Analytics** - Completion rates, engagement metrics, player behavior
- **Resume capability** - Continue from where they left off
- **Cross-experience stats** - Global player level, total playtime, achievements

## Solution: Hybrid PostgreSQL + Redis

### Architecture Decision

**Use hybrid storage combining PostgreSQL and Redis:**

| Storage Layer | Technology | Purpose | Lifespan |
|--------------|-----------|---------|----------|
| **Hot State** | Redis | Active sessions, real-time data | Minutes-Hours |
| **Cold Storage** | PostgreSQL | History, analytics, permanent progress | Forever |
| **Flexible Schema** | JSONB columns | Game-specific mechanics | Evolves over time |

**Why Hybrid?**
- ✅ **Performance**: Redis provides sub-millisecond reads for active players
- ✅ **Durability**: PostgreSQL ensures no data loss
- ✅ **Queryability**: SQL enables complex analytics queries
- ✅ **Flexibility**: JSONB adapts to new game mechanics without migrations
- ✅ **Scalability**: Proven pattern (Discord, Slack, gaming platforms)
- ✅ **No new infrastructure**: Uses existing GAIA PostgreSQL + Redis

## Data Models

### 1. PlayerProfile (Global Player Data)

```python
class PlayerProfile(Base):
    """Player profile and cross-experience stats"""
    __tablename__ = "player_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                     unique=True, nullable=False)

    # Global stats
    total_experiences_played = Column(Integer, default=0)
    total_playtime_seconds = Column(Integer, default=0)
    total_distance_meters = Column(Float, default=0.0)  # AR experiences
    account_level = Column(Integer, default=1)

    # Flexible data for game-specific stats
    stats = Column(JSONB, default={})
    # Example: {
    #   "achievements": ["first_waypoint", "marathon_walker", "quest_master"],
    #   "preferences": {"difficulty": "normal", "ar_hints_enabled": true},
    #   "global_inventory": ["golden_compass", "master_key"]
    # }

    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(),
                       onupdate=func.current_timestamp())

    # Relationships
    user = relationship("User", back_populates="player_profile")
    experience_progress = relationship("ExperienceProgress", back_populates="player",
                                      cascade="all, delete-orphan")
```

**Purpose:** Track player data that spans multiple experiences.

**Example Data:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_experiences_played": 3,
  "total_playtime_seconds": 14400,
  "total_distance_meters": 5280.5,
  "account_level": 5,
  "stats": {
    "achievements": ["first_waypoint", "marathon_walker"],
    "preferences": {"ar_hints_enabled": true}
  }
}
```

### 2. ExperienceProgress (Per-Experience Progress)

```python
class ExperienceProgress(Base):
    """Player progress within a specific experience"""
    __tablename__ = "experience_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("player_profiles.id",
                       ondelete="CASCADE"), nullable=False)
    experience_id = Column(String(100), nullable=False)  # "wylding-woods", "west-of-house"

    # Progress tracking
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    last_played_at = Column(DateTime)

    # Stats
    playtime_seconds = Column(Integer, default=0)
    completion_percentage = Column(Float, default=0.0)

    # Current state (for resume)
    current_location = Column(String(255))  # Current waypoint/room ID

    # Flexible progress data (JSONB for game-specific mechanics)
    state = Column(JSONB, default={})
    # Example: {
    #   "inventory": ["brass_key", "lamp"],
    #   "visited_waypoints": ["1_inter_woander_storefront", "8_inter_gravity_car"],
    #   "completed_quests": ["find_the_library"],
    #   "active_quests": ["collect_artist_tools"],
    #   "unlocked_areas": ["el_paseo"],
    #   "collectibles": {"artist_tools": 2, "mystical_flowers": 5},
    #   "flags": {"mailbox_opened": true, "door_unlocked": false}
    # }

    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(),
                       onupdate=func.current_timestamp())

    # Relationships
    player = relationship("PlayerProfile", back_populates="experience_progress")
    events = relationship("PlayerProgressEvent", back_populates="experience_progress",
                         cascade="all, delete-orphan")
```

**Purpose:** Track player progress in each individual experience.

**Example Data (Wylding Woods Progress):**
```json
{
  "id": "660f9511-f3ac-52e5-b827-557766551111",
  "player_id": "550e8400-e29b-41d4-a716-446655440000",
  "experience_id": "wylding-woods",
  "started_at": "2025-10-20T10:00:00Z",
  "last_played_at": "2025-10-24T15:30:00Z",
  "playtime_seconds": 3600,
  "completion_percentage": 45.0,
  "current_location": "13_inter_lending_library_story_anchor",
  "state": {
    "inventory": ["compass", "map"],
    "visited_waypoints": [
      "1_inter_woander_storefront",
      "8_inter_gravity_car",
      "13_inter_lending_library_story_anchor"
    ],
    "completed_quests": ["discover_woander"],
    "active_quests": ["explore_el_paseo"],
    "collectibles": {"artist_tools": 2, "mystical_flowers": 5},
    "flags": {
      "gravity_car_activated": true,
      "library_story_unlocked": true
    }
  }
}
```

### 3. PlayerProgressEvent (Event Log)

```python
class PlayerProgressEvent(Base):
    """Event log for analytics and history (immutable append-only)"""
    __tablename__ = "player_progress_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experience_progress_id = Column(UUID(as_uuid=True),
                                   ForeignKey("experience_progress.id", ondelete="CASCADE"),
                                   nullable=False)

    # Event details
    event_type = Column(String(50), nullable=False)
    # Types: "waypoint_visited", "quest_started", "quest_completed",
    #        "item_collected", "achievement_unlocked", "location_reached"

    content_id = Column(String(255))  # Which waypoint/quest/item

    # Event data (flexible)
    data = Column(JSONB, default={})
    # Example: {
    #   "distance_traveled": 1.2,
    #   "time_spent": 45,
    #   "choices_made": ["left_path"],
    #   "interaction_method": "tap"
    # }

    # Location data (for AR experiences)
    location_lat = Column(Float)
    location_lng = Column(Float)

    timestamp = Column(DateTime, default=func.current_timestamp(), nullable=False)

    # Relationships
    experience_progress = relationship("ExperienceProgress", back_populates="events")
```

**Purpose:** Immutable event log for analytics, debugging, and audit trail.

**Example Events:**
```json
[
  {
    "event_type": "waypoint_visited",
    "content_id": "8_inter_gravity_car",
    "data": {
      "distance_traveled": 1.2,
      "time_spent": 120,
      "interaction_method": "wheel_rotation"
    },
    "location_lat": 37.905696,
    "location_lng": -122.547701,
    "timestamp": "2025-10-24T15:30:00Z"
  },
  {
    "event_type": "quest_completed",
    "content_id": "discover_woander",
    "data": {
      "completion_time_seconds": 1800,
      "steps_completed": 5
    },
    "timestamp": "2025-10-24T15:45:00Z"
  }
]
```

### Database Indexes

```sql
-- PlayerProfile indexes
CREATE INDEX idx_player_profiles_user_id ON player_profiles(user_id);
CREATE INDEX idx_player_profiles_account_level ON player_profiles(account_level);

-- ExperienceProgress indexes
CREATE INDEX idx_experience_progress_player_id ON experience_progress(player_id);
CREATE INDEX idx_experience_progress_experience_id ON experience_progress(experience_id);
CREATE INDEX idx_experience_progress_last_played ON experience_progress(last_played_at);
CREATE INDEX idx_experience_progress_player_exp ON experience_progress(player_id, experience_id);

-- PlayerProgressEvent indexes
CREATE INDEX idx_progress_events_experience_id ON player_progress_events(experience_progress_id);
CREATE INDEX idx_progress_events_type ON player_progress_events(event_type);
CREATE INDEX idx_progress_events_timestamp ON player_progress_events(timestamp);
CREATE INDEX idx_progress_events_content_id ON player_progress_events(content_id);

-- JSONB indexes for common queries
CREATE INDEX idx_experience_progress_state_inventory
  ON experience_progress USING GIN ((state->'inventory'));
CREATE INDEX idx_experience_progress_state_visited
  ON experience_progress USING GIN ((state->'visited_waypoints'));
```

## Redis Caching Layer

### Cache Structure

**Redis key patterns:**

```python
# 1. Active session state (TTL: 1 hour of inactivity)
"player:{user_id}:session" → {
    "current_experience": "wylding-woods",
    "current_location": "8_inter_gravity_car",
    "session_start": "2025-10-24T14:00:00Z",
    "last_activity": "2025-10-24T15:45:00Z"
}

# 2. Hot inventory (frequently accessed, TTL: 1 hour)
"player:{user_id}:inventory:{experience_id}" → Set["item1", "item2", "item3"]

# 3. Visited waypoints cache (TTL: 1 hour)
"player:{user_id}:visited:{experience_id}" → Set["waypoint1", "waypoint2"]

# 4. Real-time stats (for live leaderboards, TTL: 5 minutes)
"experience:{experience_id}:leaderboard:distance" → SortedSet

# 5. Active players count (TTL: 30 minutes)
"experience:{experience_id}:active_players" → Set[user_ids]
```

### Cache Operations

```python
# app/services/game/player_progress.py

class PlayerProgressManager:
    """Manages player progress with hybrid storage"""

    async def update_progress(
        self,
        user_id: str,
        experience_id: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Update player progress (dual-write to Redis + PostgreSQL)
        """
        # 1. Update hot cache (Redis) - immediate
        await redis_client.setex(
            f"player:{user_id}:session",
            3600,  # 1 hour TTL
            json.dumps({
                "current_experience": experience_id,
                "last_activity": datetime.utcnow().isoformat(),
                **data
            })
        )

        # 2. Update cold storage (PostgreSQL) - async/batch
        await self._write_progress_event(user_id, experience_id, event_type, data)

    async def get_player_state(self, user_id: str, experience_id: str) -> Dict:
        """
        Get current player state (Redis first, fallback to PostgreSQL)
        """
        # Try Redis cache first
        cached = await redis_client.get(f"player:{user_id}:session")
        if cached:
            logger.info(f"Cache HIT for player {user_id}")
            return json.loads(cached)

        logger.info(f"Cache MISS for player {user_id}, loading from PostgreSQL")

        # Fallback to database
        db = self._get_db()
        progress = db.query(ExperienceProgress).filter(
            ExperienceProgress.player_id == user_id,
            ExperienceProgress.experience_id == experience_id
        ).first()

        if progress:
            state = progress.state
            # Warm cache for next request
            await redis_client.setex(
                f"player:{user_id}:session",
                3600,
                json.dumps(state)
            )
            return state

        return {}

    async def add_to_inventory(self, user_id: str, experience_id: str, item: str):
        """Add item to player inventory (Redis + PostgreSQL)"""
        # Update Redis set
        await redis_client.sadd(f"player:{user_id}:inventory:{experience_id}", item)
        await redis_client.expire(f"player:{user_id}:inventory:{experience_id}", 3600)

        # Update PostgreSQL JSONB
        await self._append_to_jsonb_array(
            ExperienceProgress,
            {"player_id": user_id, "experience_id": experience_id},
            "state->inventory",
            item
        )

    async def has_visited_waypoint(
        self,
        user_id: str,
        experience_id: str,
        waypoint_id: str
    ) -> bool:
        """Check if player has visited a waypoint (Redis first)"""
        # Check Redis set
        visited = await redis_client.sismember(
            f"player:{user_id}:visited:{experience_id}",
            waypoint_id
        )

        if visited:
            return True

        # Fallback to PostgreSQL
        db = self._get_db()
        progress = db.query(ExperienceProgress).filter(
            ExperienceProgress.player_id == user_id,
            ExperienceProgress.experience_id == experience_id
        ).first()

        if progress and waypoint_id in progress.state.get("visited_waypoints", []):
            # Warm cache
            await redis_client.sadd(
                f"player:{user_id}:visited:{experience_id}",
                waypoint_id
            )
            await redis_client.expire(
                f"player:{user_id}:visited:{experience_id}",
                3600
            )
            return True

        return False
```

## Data Flow

### 1. Player Action (e.g., "Visit Waypoint")

```
Unity/Web Client
    ↓
POST /game/command {command: "scan marker", experience: "wylding-woods"}
    ↓
Gateway → Game Command Tool
    ↓
┌──────────────────────────────────────┐
│  execute_game_command()              │
│  1. Process command                  │
│  2. Generate response                │
│  3. Log progress event ────┐         │
└────────────────────────────┼─────────┘
                             ↓
                ┌────────────┴───────────┐
                ↓                        ↓
        Redis (instant)          PostgreSQL (durable)
     Update session state    Log event + update totals
     TTL: 1 hour            Permanent storage
                ↓                        ↓
        Return to client        Background: Analytics
```

### 2. Query Progress (e.g., "Show my inventory")

```
LLM Tool: track_content_engagement
    ↓
PlayerProgressManager.get_inventory(user_id, experience_id)
    ↓
Try Redis: GET player:{user_id}:inventory:{experience_id}
    ↓
├─ HIT: Return instantly (sub-millisecond)
│
└─ MISS: Query PostgreSQL
        ↓
    SELECT state->'inventory' FROM experience_progress
    WHERE player_id = ? AND experience_id = ?
        ↓
    Warm Redis cache (for next request)
        ↓
    Return result
```

### 3. Analytics Query (e.g., "How many players visited waypoint X?")

```
Designer: track_content_engagement("8_inter_gravity_car")
    ↓
PostgreSQL Query (PlayerProgressEvent table)
    ↓
SELECT COUNT(DISTINCT experience_progress_id)
FROM player_progress_events
WHERE event_type = 'waypoint_visited'
  AND content_id = '8_inter_gravity_car'
  AND timestamp > NOW() - INTERVAL '7 days'
    ↓
Return: {
  "total_visits": 1247,
  "unique_players": 423,
  "avg_time_spent": 120
}
```

## Storage Capacity Planning

### Example: 10,000 Players, Wylding Woods (37 Waypoints)

| Data Type | Storage Location | Size per Player | Total (10K players) |
|-----------|------------------|-----------------|---------------------|
| **Player Profile** | PostgreSQL | 1 KB | 10 MB |
| **Experience Progress** (1 experience) | PostgreSQL | 5 KB | 50 MB |
| **Progress Events** (50 events/player) | PostgreSQL | 100 bytes/event | 50 MB |
| **Active Session** (10% active) | Redis | 2 KB × 1K players | 2 MB |
| **Hot Inventory** (10% active) | Redis | 500 bytes × 1K players | 500 KB |
| **Visited Cache** (10% active) | Redis | 1 KB × 1K players | 1 MB |
| **Total** | | | **~113 MB** |

**Scalability:**
- **100K players**: ~1.1 GB PostgreSQL + ~35 MB Redis
- **1M players**: ~11 GB PostgreSQL + ~350 MB Redis
- **10M players**: ~110 GB PostgreSQL + ~3.5 GB Redis

**Conclusion:** Easily handles millions of players with proper indexing and Redis caching.

## Performance Benchmarks

### Target Performance

| Operation | Target | Strategy |
|-----------|--------|----------|
| **Read active session** | <10ms | Redis cache (99% hit rate) |
| **Write progress event** | <50ms | Async PostgreSQL write |
| **Query player inventory** | <20ms | Redis set lookup |
| **Check waypoint visited** | <15ms | Redis set membership |
| **Analytics query** | <500ms | Indexed PostgreSQL, pre-aggregation |
| **Full player history** | <1s | PostgreSQL with pagination |

### Cache Hit Rates

**Expected cache performance:**
- **Active players** (playing now): 95-99% Redis hit rate
- **Recently active** (within 1 hour): 80-90% Redis hit rate
- **Inactive players**: 0% (cache expired, query PostgreSQL)

## Migration Guide

### Phase 1: Add Tables (Day 1)

```bash
# Create migration file
./scripts/migrate-database.sh --env dev --migration migrations/002_add_player_progress.sql
```

```sql
-- migrations/002_add_player_progress.sql

-- PlayerProfile table
CREATE TABLE player_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    total_experiences_played INTEGER DEFAULT 0,
    total_playtime_seconds INTEGER DEFAULT 0,
    total_distance_meters FLOAT DEFAULT 0.0,
    account_level INTEGER DEFAULT 1,
    stats JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_player_profiles_user_id ON player_profiles(user_id);
CREATE INDEX idx_player_profiles_account_level ON player_profiles(account_level);

-- ExperienceProgress table
CREATE TABLE experience_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES player_profiles(id) ON DELETE CASCADE,
    experience_id VARCHAR(100) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_played_at TIMESTAMP,
    playtime_seconds INTEGER DEFAULT 0,
    completion_percentage FLOAT DEFAULT 0.0,
    current_location VARCHAR(255),
    state JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, experience_id)
);

CREATE INDEX idx_experience_progress_player_id ON experience_progress(player_id);
CREATE INDEX idx_experience_progress_experience_id ON experience_progress(experience_id);
CREATE INDEX idx_experience_progress_last_played ON experience_progress(last_played_at);
CREATE INDEX idx_experience_progress_player_exp ON experience_progress(player_id, experience_id);

-- PlayerProgressEvent table
CREATE TABLE player_progress_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experience_progress_id UUID NOT NULL REFERENCES experience_progress(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    content_id VARCHAR(255),
    data JSONB DEFAULT '{}',
    location_lat FLOAT,
    location_lng FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_progress_events_experience_id ON player_progress_events(experience_progress_id);
CREATE INDEX idx_progress_events_type ON player_progress_events(event_type);
CREATE INDEX idx_progress_events_timestamp ON player_progress_events(timestamp);
CREATE INDEX idx_progress_events_content_id ON player_progress_events(content_id);

-- JSONB indexes
CREATE INDEX idx_experience_progress_state_inventory
  ON experience_progress USING GIN ((state->'inventory'));
CREATE INDEX idx_experience_progress_state_visited
  ON experience_progress USING GIN ((state->'visited_waypoints'));
```

### Phase 2: Add SQLAlchemy Models (Day 1)

Update `app/models/database.py` with the three models shown above.

Update `User` model:
```python
class User(Base):
    # ... existing fields ...
    player_profile = relationship("PlayerProfile", back_populates="user",
                                 uselist=False, cascade="all, delete-orphan")
```

### Phase 3: Implement Progress Manager (Days 2-3)

Create `app/services/game/player_progress.py` with the code shown above.

### Phase 4: Integration (Day 4)

Update `app/shared/tools/game_commands.py`:

```python
from app.services.game.player_progress import player_progress_manager

async def execute_game_command(...):
    # ... existing command processing ...

    # Log progress event
    await player_progress_manager.log_event(
        user_id=user_context["user_id"],
        experience_id=experience,
        event_type="waypoint_visited",
        content_id="8_inter_gravity_car",
        data={
            "distance_traveled": 1.2,
            "time_spent": 120
        }
    )

    # Update current location
    await player_progress_manager.update_location(
        user_id=user_context["user_id"],
        experience_id=experience,
        location="8_inter_gravity_car"
    )
```

## Monitoring & Operations

### Key Metrics to Track

```python
# Prometheus metrics
player_progress_cache_hit_rate = Gauge('player_progress_cache_hit_rate',
                                       'Redis cache hit rate')
player_progress_write_latency = Histogram('player_progress_write_latency_seconds',
                                         'PostgreSQL write latency')
active_players = Gauge('active_players_total',
                      'Total active players')
```

### Health Checks

```python
@router.get("/health/player-progress")
async def player_progress_health():
    # Check Redis connectivity
    redis_ok = await redis_client.ping()

    # Check PostgreSQL connectivity
    db = get_db()
    pg_ok = db.query(PlayerProfile).count() >= 0

    return {
        "status": "healthy" if (redis_ok and pg_ok) else "degraded",
        "redis": "ok" if redis_ok else "error",
        "postgresql": "ok" if pg_ok else "error"
    }
```

## Security Considerations

### Data Privacy

- **PII Protection**: Player profiles contain user_id (UUID), not email
- **GDPR Compliance**: Support user deletion (CASCADE deletes all progress)
- **Data Encryption**: PostgreSQL data at rest encryption enabled
- **Access Control**: Only authenticated users can read their own progress

### Audit Trail

- **Immutable Events**: PlayerProgressEvent is append-only
- **Attribution**: All events linked to experience_progress_id → player_id → user_id
- **Timestamps**: All events have creation timestamp

## Summary

**Storage Strategy:**
- ✅ **PostgreSQL**: Durable storage for progress state and event history
- ✅ **Redis**: Performance cache for active sessions
- ✅ **JSONB**: Flexible schema for evolving game mechanics
- ✅ **Hybrid approach**: Best of both worlds (fast + durable + queryable)

**Capacity:**
- Easily handles **millions of players**
- **Sub-10ms** reads for active players (Redis)
- **<500ms** analytics queries (PostgreSQL + indexes)

**Next Steps:**
1. Create database migration (002_add_player_progress.sql)
2. Add SQLAlchemy models to app/models/database.py
3. Implement PlayerProgressManager service
4. Integrate with game command execution

**See Also:**
- [Experience Data Models](./experience-data-models.md) - Complete model definitions
- [Experience Tools API](./experience-tools-api.md) - Tools that query/update progress
