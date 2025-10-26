# Experience Data Models

> **Purpose**: Database schema for experience platform (player progress, events, analytics)
> **Status**: DESIGN PHASE
> **Created**: 2025-10-24
> **Related**:
> - [Player Progress Storage](./player-progress-storage.md) - Storage architecture
> - [Database Architecture](../database/database-architecture.md) - General database design

## Overview

Three main tables support player progress tracking:
1. **PlayerProfile** - Global player data across all experiences
2. **ExperienceProgress** - Per-experience progress and state
3. **PlayerProgressEvent** - Immutable event log for analytics

## Database Schema

### PlayerProfile Model

**Purpose:** Track player data that spans multiple experiences (account level, global stats, achievements).

```python
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

class PlayerProfile(Base):
    """
    Player profile and cross-experience stats.

    One profile per user - contains global player data.
    """
    __tablename__ = "player_profiles"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to users table
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Global statistics
    total_experiences_played = Column(Integer, default=0,
        comment="Number of unique experiences player has started")

    total_playtime_seconds = Column(Integer, default=0,
        comment="Total playtime across all experiences")

    total_distance_meters = Column(Float, default=0.0,
        comment="Total distance traveled in AR experiences")

    account_level = Column(Integer, default=1,
        comment="Player account level (1-100)")

    # Flexible data storage (JSONB for evolving features)
    stats = Column(JSONB, default={},
        comment="Additional stats: achievements, preferences, global inventory")
    # Example stats structure:
    # {
    #   "achievements": ["first_waypoint", "marathon_walker", "quest_master"],
    #   "preferences": {
    #     "difficulty": "normal",
    #     "ar_hints_enabled": true,
    #     "notifications_enabled": true
    #   },
    #   "global_inventory": ["golden_compass", "master_key"],
    #   "custom_stats": {
    #     "total_quests_completed": 15,
    #     "favorite_experience": "wylding-woods"
    #   }
    # }

    # Timestamps
    created_at = Column(DateTime, default=func.current_timestamp(),
        comment="When player profile was created")

    updated_at = Column(DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="Last update to profile")

    # Relationships
    user = relationship("User", back_populates="player_profile")
    experience_progress = relationship(
        "ExperienceProgress",
        back_populates="player",
        cascade="all, delete-orphan",
        order_by="ExperienceProgress.last_played_at.desc()"
    )

    # Table constraints and indexes
    __table_args__ = (
        Index('idx_player_profiles_user_id', 'user_id'),
        Index('idx_player_profiles_account_level', 'account_level'),
        # JSONB index for achievement queries
        Index('idx_player_profiles_achievements',
              'stats', postgresql_using='gin',
              postgresql_ops={'stats': 'jsonb_path_ops'}),
        {'comment': 'Player profiles with global stats and cross-experience data'}
    )

    def __repr__(self):
        return f"<PlayerProfile(id={self.id}, user_id={self.user_id}, level={self.account_level})>"
```

---

### ExperienceProgress Model

**Purpose:** Track player progress within a specific experience (state, inventory, visited locations).

```python
class ExperienceProgress(Base):
    """
    Player progress within a specific experience.

    One record per (player, experience) combination.
    Stores current state, inventory, visited locations, etc.
    """
    __tablename__ = "experience_progress"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    player_id = Column(
        UUID(as_uuid=True),
        ForeignKey("player_profiles.id", ondelete="CASCADE"),
        nullable=False
    )

    # Experience identifier (matches KB experience ID)
    experience_id = Column(String(100), nullable=False,
        comment="Experience ID from KB (e.g., 'wylding-woods', 'west-of-house')")

    # Progress tracking
    started_at = Column(DateTime,
        comment="When player first started this experience")

    completed_at = Column(DateTime,
        comment="When player completed this experience (null if incomplete)")

    last_played_at = Column(DateTime,
        comment="Most recent play session")

    # Statistics
    playtime_seconds = Column(Integer, default=0,
        comment="Total time spent in this experience")

    completion_percentage = Column(Float, default=0.0,
        comment="Percentage complete (0.0 to 100.0)")

    # Current location (for resume/save point)
    current_location = Column(String(255),
        comment="Current waypoint/room ID (e.g., '8_inter_gravity_car')")

    # Flexible game state (JSONB for game-specific mechanics)
    state = Column(JSONB, default={},
        comment="Game-specific state: inventory, visited locations, flags, etc.")
    # Example state structure:
    # {
    #   "inventory": ["brass_key", "lamp", "compass"],
    #   "visited_waypoints": [
    #     "1_inter_woander_storefront",
    #     "8_inter_gravity_car",
    #     "13_inter_lending_library_story_anchor"
    #   ],
    #   "completed_quests": ["discover_woander", "find_the_library"],
    #   "active_quests": ["explore_el_paseo", "collect_artist_tools"],
    #   "unlocked_areas": ["downtown", "el_paseo"],
    #   "collectibles": {
    #     "artist_tools": 2,
    #     "mystical_flowers": 5,
    #     "story_fragments": 3
    #   },
    #   "flags": {
    #     "mailbox_opened": true,
    #     "door_unlocked": false,
    #     "gravity_car_activated": true
    #   },
    #   "choices": {
    #     "path_taken": "left",
    #     "alliance": "forest_spirits"
    #   }
    # }

    # Timestamps
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp())

    # Relationships
    player = relationship("PlayerProfile", back_populates="experience_progress")
    events = relationship(
        "PlayerProgressEvent",
        back_populates="experience_progress",
        cascade="all, delete-orphan",
        order_by="PlayerProgressEvent.timestamp.desc()"
    )

    # Table constraints and indexes
    __table_args__ = (
        # Unique constraint: one progress record per (player, experience)
        Index('idx_experience_progress_unique',
              'player_id', 'experience_id',
              unique=True),

        # Query indexes
        Index('idx_experience_progress_player_id', 'player_id'),
        Index('idx_experience_progress_experience_id', 'experience_id'),
        Index('idx_experience_progress_last_played', 'last_played_at'),
        Index('idx_experience_progress_completion', 'completion_percentage'),

        # Composite index for common query: "get player's progress in this experience"
        Index('idx_experience_progress_player_exp', 'player_id', 'experience_id'),

        # JSONB indexes for common queries
        Index('idx_experience_progress_inventory',
              'state', postgresql_using='gin',
              postgresql_ops={'state': 'jsonb_path_ops'}),
        Index('idx_experience_progress_visited',
              (func.jsonb_extract_path_text('state', 'visited_waypoints')),
              postgresql_using='gin'),

        {'comment': 'Player progress and state within individual experiences'}
    )

    def __repr__(self):
        return f"<ExperienceProgress(player={self.player_id}, exp={self.experience_id}, {self.completion_percentage}% complete)>"
```

---

### PlayerProgressEvent Model

**Purpose:** Immutable event log for analytics, debugging, and audit trail.

```python
class PlayerProgressEvent(Base):
    """
    Event log for player progress tracking.

    Append-only immutable log of all player actions/events.
    Used for analytics, debugging, and audit trail.
    """
    __tablename__ = "player_progress_events"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to experience progress
    experience_progress_id = Column(
        UUID(as_uuid=True),
        ForeignKey("experience_progress.id", ondelete="CASCADE"),
        nullable=False
    )

    # Event classification
    event_type = Column(String(50), nullable=False,
        comment="Type of event")
    # Common event types:
    # - "waypoint_visited"
    # - "quest_started"
    # - "quest_completed"
    # - "item_collected"
    # - "achievement_unlocked"
    # - "location_reached"
    # - "interaction_performed"
    # - "npc_dialogue"
    # - "area_unlocked"
    # - "player_death"
    # - "game_completed"

    # Content reference (which waypoint/quest/item)
    content_id = Column(String(255),
        comment="ID of related content (waypoint_id, quest_id, item_id, etc.)")

    # Event-specific data (JSONB for flexibility)
    data = Column(JSONB, default={},
        comment="Event-specific data and metadata")
    # Example data structures:
    # waypoint_visited: {
    #   "distance_traveled": 1.2,
    #   "time_spent": 120,
    #   "interaction_method": "wheel_rotation",
    #   "points_earned": 10
    # }
    # quest_completed: {
    #   "completion_time_seconds": 1800,
    #   "steps_completed": 5,
    #   "difficulty": "normal",
    #   "reward": {"xp": 100, "item": "golden_key"}
    # }
    # item_collected: {
    #   "collection_method": "pickup",
    #   "quantity": 1,
    #   "rarity": "rare"
    # }

    # Location data (for AR experiences)
    location_lat = Column(Float,
        comment="GPS latitude where event occurred")

    location_lng = Column(Float,
        comment="GPS longitude where event occurred")

    # Timestamp (immutable, never updated)
    timestamp = Column(DateTime,
        default=func.current_timestamp(),
        nullable=False,
        comment="When event occurred (UTC)")

    # Relationships
    experience_progress = relationship("ExperienceProgress", back_populates="events")

    # Table constraints and indexes
    __table_args__ = (
        # Query indexes
        Index('idx_progress_events_experience_id', 'experience_progress_id'),
        Index('idx_progress_events_type', 'event_type'),
        Index('idx_progress_events_timestamp', 'timestamp'),
        Index('idx_progress_events_content_id', 'content_id'),

        # Composite indexes for common analytics queries
        Index('idx_progress_events_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_progress_events_content_timestamp', 'content_id', 'timestamp'),

        # Location-based queries (AR experiences)
        Index('idx_progress_events_location', 'location_lat', 'location_lng'),

        # JSONB index for event data queries
        Index('idx_progress_events_data',
              'data', postgresql_using='gin',
              postgresql_ops={'data': 'jsonb_path_ops'}),

        {'comment': 'Immutable event log for player progress analytics'}
    )

    def __repr__(self):
        return f"<PlayerProgressEvent(type={self.event_type}, content={self.content_id}, time={self.timestamp})>"
```

---

## User Model Update

Update the existing `User` model to include player profile relationship:

```python
# In app/models/database.py

class User(Base):
    """User model compatible with existing schema"""
    __tablename__ = "users"

    # ... existing fields ...

    # Add new relationship
    player_profile = relationship(
        "PlayerProfile",
        back_populates="user",
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan"
    )
```

---

## Migration SQL

### Complete Migration Script

```sql
-- Migration: 002_add_player_progress.sql
-- Description: Add player progress tracking for experience platform
-- Created: 2025-10-24

-- =====================================================
-- PlayerProfile Table
-- =====================================================

CREATE TABLE player_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,

    -- Global statistics
    total_experiences_played INTEGER DEFAULT 0,
    total_playtime_seconds INTEGER DEFAULT 0,
    total_distance_meters FLOAT DEFAULT 0.0,
    account_level INTEGER DEFAULT 1,

    -- Flexible stats storage
    stats JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE player_profiles IS 'Player profiles with global stats and cross-experience data';
COMMENT ON COLUMN player_profiles.stats IS 'Achievements, preferences, global inventory, custom stats';

-- Indexes
CREATE INDEX idx_player_profiles_user_id ON player_profiles(user_id);
CREATE INDEX idx_player_profiles_account_level ON player_profiles(account_level);
CREATE INDEX idx_player_profiles_achievements ON player_profiles USING gin (stats jsonb_path_ops);


-- =====================================================
-- ExperienceProgress Table
-- =====================================================

CREATE TABLE experience_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES player_profiles(id) ON DELETE CASCADE,
    experience_id VARCHAR(100) NOT NULL,

    -- Progress tracking
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_played_at TIMESTAMP,

    -- Statistics
    playtime_seconds INTEGER DEFAULT 0,
    completion_percentage FLOAT DEFAULT 0.0,

    -- Current state
    current_location VARCHAR(255),
    state JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(player_id, experience_id)
);

COMMENT ON TABLE experience_progress IS 'Player progress and state within individual experiences';
COMMENT ON COLUMN experience_progress.state IS 'Game state: inventory, visited locations, flags, collectibles';

-- Indexes
CREATE INDEX idx_experience_progress_player_id ON experience_progress(player_id);
CREATE INDEX idx_experience_progress_experience_id ON experience_progress(experience_id);
CREATE INDEX idx_experience_progress_last_played ON experience_progress(last_played_at);
CREATE INDEX idx_experience_progress_completion ON experience_progress(completion_percentage);
CREATE INDEX idx_experience_progress_player_exp ON experience_progress(player_id, experience_id);

-- JSONB indexes for common queries
CREATE INDEX idx_experience_progress_inventory ON experience_progress USING gin (state jsonb_path_ops);
CREATE INDEX idx_experience_progress_visited ON experience_progress USING gin ((state->'visited_waypoints'));


-- =====================================================
-- PlayerProgressEvent Table
-- =====================================================

CREATE TABLE player_progress_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experience_progress_id UUID NOT NULL REFERENCES experience_progress(id) ON DELETE CASCADE,

    -- Event details
    event_type VARCHAR(50) NOT NULL,
    content_id VARCHAR(255),
    data JSONB DEFAULT '{}',

    -- Location data (AR experiences)
    location_lat FLOAT,
    location_lng FLOAT,

    -- Timestamp (immutable)
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON TABLE player_progress_events IS 'Immutable event log for player progress analytics';
COMMENT ON COLUMN player_progress_events.event_type IS 'Event type: waypoint_visited, quest_completed, etc.';
COMMENT ON COLUMN player_progress_events.data IS 'Event-specific metadata and details';

-- Indexes
CREATE INDEX idx_progress_events_experience_id ON player_progress_events(experience_progress_id);
CREATE INDEX idx_progress_events_type ON player_progress_events(event_type);
CREATE INDEX idx_progress_events_timestamp ON player_progress_events(timestamp);
CREATE INDEX idx_progress_events_content_id ON player_progress_events(content_id);
CREATE INDEX idx_progress_events_type_timestamp ON player_progress_events(event_type, timestamp);
CREATE INDEX idx_progress_events_content_timestamp ON player_progress_events(content_id, timestamp);
CREATE INDEX idx_progress_events_location ON player_progress_events(location_lat, location_lng);
CREATE INDEX idx_progress_events_data ON player_progress_events USING gin (data jsonb_path_ops);


-- =====================================================
-- Triggers for updated_at
-- =====================================================

-- PlayerProfile updated_at trigger
CREATE OR REPLACE FUNCTION update_player_profile_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER player_profile_updated_at
    BEFORE UPDATE ON player_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_player_profile_timestamp();

-- ExperienceProgress updated_at trigger
CREATE OR REPLACE FUNCTION update_experience_progress_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER experience_progress_updated_at
    BEFORE UPDATE ON experience_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_experience_progress_timestamp();


-- =====================================================
-- Sample Data (for testing)
-- =====================================================

-- Insert sample player profile (requires existing user)
-- INSERT INTO player_profiles (user_id, account_level, total_experiences_played, stats)
-- SELECT id, 1, 0, '{"achievements": [], "preferences": {"difficulty": "normal"}}'::jsonb
-- FROM users
-- WHERE email = 'dev@gaia.local';
```

---

## Common Query Patterns

### Get Player's Current State

```python
# Get player's progress in specific experience
progress = db.query(ExperienceProgress).filter(
    ExperienceProgress.player_id == player_id,
    ExperienceProgress.experience_id == "wylding-woods"
).first()

# Access JSONB fields
inventory = progress.state.get("inventory", [])
visited_waypoints = progress.state.get("visited_waypoints", [])
```

### Track New Event

```python
# Log waypoint visit
event = PlayerProgressEvent(
    experience_progress_id=progress.id,
    event_type="waypoint_visited",
    content_id="8_inter_gravity_car",
    data={
        "distance_traveled": 1.2,
        "time_spent": 120,
        "interaction_method": "wheel_rotation"
    },
    location_lat=37.905696,
    location_lng=-122.547701
)
db.add(event)
db.commit()
```

### Analytics: Waypoint Visit Count

```python
# How many times has a waypoint been visited?
visit_count = db.query(func.count(PlayerProgressEvent.id)).filter(
    PlayerProgressEvent.event_type == "waypoint_visited",
    PlayerProgressEvent.content_id == "8_inter_gravity_car",
    PlayerProgressEvent.timestamp >= datetime.now() - timedelta(days=7)
).scalar()
```

### Update Player Inventory

```python
# Add item to inventory (JSONB array append)
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB

db.query(ExperienceProgress).filter(
    ExperienceProgress.id == progress_id
).update({
    "state": func.jsonb_set(
        ExperienceProgress.state,
        cast(["inventory"], JSONB),
        func.jsonb_build_array("brass_key") + ExperienceProgress.state["inventory"],
        True
    )
})
db.commit()
```

---

## Performance Considerations

### JSONB Indexing

```sql
-- Index for inventory queries
CREATE INDEX idx_progress_inventory
  ON experience_progress USING gin ((state->'inventory'));

-- Query using the index
SELECT * FROM experience_progress
WHERE state->'inventory' @> '["brass_key"]';
```

### Partitioning (Future Optimization)

For very large event tables (millions of events), consider time-based partitioning:

```sql
-- Partition by month
CREATE TABLE player_progress_events_2025_10
  PARTITION OF player_progress_events
  FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

---

## Summary

**Three core tables:**
1. **PlayerProfile** - Global player data (1 per user)
2. **ExperienceProgress** - Per-experience state (1 per player per experience)
3. **PlayerProgressEvent** - Event log (append-only, many per progress)

**Key features:**
- ✅ JSONB for flexible game mechanics
- ✅ Proper indexing for fast queries
- ✅ CASCADE deletes (GDPR compliance)
- ✅ Immutable event log (audit trail)
- ✅ GPS location tracking (AR experiences)

**Storage estimate:**
- 10K players: ~113 MB
- 100K players: ~1.1 GB
- 1M players: ~11 GB

**Next:** See [Player Progress Storage](./player-progress-storage.md) for Redis caching and data flow.
