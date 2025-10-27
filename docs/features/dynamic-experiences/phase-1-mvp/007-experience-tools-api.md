# Experience Tools API

> **Purpose**: LLM tools for conversational experience design
> **Status**: DESIGN PHASE
> **Created**: 2025-10-24
> **Related**:
> - [Experience Platform Architecture](./+experiences.md) - Overall platform
> - [Player Progress Storage](./player-progress-storage.md) - Progress tracking
> - [KB LLM Content Creation](../../kb/developer/kb-llm-content-creation.md) - Content creation workflow

## Overview

**20 LLM-callable tools** enabling designers to create and manage interactive experiences through natural conversation.

**Key Innovation:** Designers interact with game content conversationally instead of:
- ❌ Filling out web forms
- ❌ Editing YAML files manually
- ❌ Using complex CMSes

**Design Philosophy:**
1. **Hierarchical discovery** - Start broad (list experiences) → narrow (specific waypoints)
2. **Context preservation** - Remember which experience you're working on
3. **Template-driven learning** - LLM learns structure from existing content, not hardcoded schemas

## Tool Organization

```
Experience Tools (20 tools)
│
├─ Discovery (3 tools)
│  ├─ list_experiences
│  ├─ describe_experience
│  └─ set_current_experience
│
├─ Content Discovery (3 tools)
│  ├─ list_experience_content
│  ├─ describe_content_item
│  └─ search_experience_content
│
├─ Content Management (4 tools)
│  ├─ get_content_template
│  ├─ create_experience_content
│  ├─ edit_experience_content
│  └─ clone_experience_content
│
├─ Lifecycle Management (2 tools)
│  ├─ schedule_experience_content
│  └─ version_experience_content
│
├─ Player Progress (2 tools)
│  ├─ track_content_engagement
│  └─ define_content_prerequisites
│
├─ Quality Assurance (3 tools)
│  ├─ test_experience_flow
│  ├─ flag_content_for_review
│  └─ validate_experience_content
│
└─ Live Operations (3 tools)
   ├─ patch_experience_content
   ├─ rollback_experience_content
   └─ analyze_experience
```

---

## Tier 1: Discovery Tools

### 1. list_experiences

**Purpose:** List all interactive experiences in the KB.

**Use When:**
- "What games do we have?"
- "Show me all experiences"
- "List AR games"

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "list_experiences",
        "description": "List all interactive experiences in the KB (AR games, text adventures, simulations). Returns experience metadata and content stats.",
        "parameters": {
            "type": "object",
            "properties": {
                "include_stats": {
                    "type": "boolean",
                    "description": "Include content counts and metadata",
                    "default": True
                },
                "filter_type": {
                    "type": "string",
                    "enum": ["ar-location", "text-adventure", "turn-based", "all"],
                    "description": "Filter by experience type",
                    "default": "all"
                }
            }
        }
    }
}
```

**Example Response:**
```json
{
    "success": true,
    "experiences": [
        {
            "id": "wylding-woods",
            "name": "Wylding Woods",
            "type": "ar-location",
            "description": "AR adventure through Mill Valley",
            "stats": {
                "waypoints": 37,
                "items": 15,
                "npcs": 3,
                "last_updated": "2025-10-24"
            }
        },
        {
            "id": "west-of-house",
            "name": "West of House",
            "type": "text-adventure",
            "stats": {
                "rooms": 8,
                "items": 12,
                "last_updated": "2025-10-20"
            }
        }
    ],
    "total": 2
}
```

---

### 2. describe_experience

**Purpose:** Get detailed overview of a specific experience.

**Use When:**
- "Tell me about Wylding Woods"
- "What's in this experience?"
- "Describe West of House"

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "describe_experience",
        "description": "Get detailed overview of an interactive experience including content types, narrative structure, and sample content.",
        "parameters": {
            "type": "object",
            "properties": {
                "experience": {
                    "type": "string",
                    "description": "Experience ID (e.g., 'wylding-woods', 'west-of-house')"
                },
                "detail_level": {
                    "type": "string",
                    "enum": ["summary", "detailed", "full"],
                    "description": "How much detail to include",
                    "default": "detailed"
                }
            },
            "required": ["experience"]
        }
    }
}
```

**Example Response:**
```json
{
    "success": true,
    "experience": {
        "id": "wylding-woods",
        "name": "Wylding Woods",
        "type": "ar-location",
        "description": "AR adventure through Mill Valley featuring waypoints, collectibles, and quests",
        "content_types": ["waypoints", "items", "npcs"],
        "waypoint_types": ["interactive", "narrative", "fx", "caution", "gps", "vps"],
        "narrative_arc": "Journey from Woander Store → downtown → El Paseo → bridge → finale",
        "sample_content": [
            {
                "type": "waypoint",
                "id": "1_inter_woander_storefront",
                "name": "Woander Storefront",
                "summary": "Starting point - scan marker to begin"
            },
            {
                "type": "waypoint",
                "id": "8_inter_gravity_car",
                "name": "Gravity Car",
                "summary": "Interactive - rotate wheel to activate"
            }
        ],
        "total_waypoints": 37,
        "geographic_bounds": {
            "center": {"lat": 37.9058, "lng": -122.5477},
            "radius_km": 0.8
        }
    }
}
```

---

### 3. set_current_experience

**Purpose:** Set conversation context to a specific experience (avoids repeating experience name).

**Use When:**
- "I want to work on Wylding Woods"
- "Switch to West of House"
- "Focus on this game"

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "set_current_experience",
        "description": "Set which experience the designer is working on. Stores in conversation context so they don't need to repeat the experience name in subsequent commands.",
        "parameters": {
            "type": "object",
            "properties": {
                "experience": {
                    "type": "string",
                    "description": "Experience ID to set as current context"
                }
            },
            "required": ["experience"]
        }
    }
}
```

**Example Response:**
```json
{
    "success": true,
    "message": "Now working on 'Wylding Woods'. Other experience tools will use this as default.",
    "current_experience": "wylding-woods"
}
```

**Conversation Metadata Updated:**
```json
{
    "current_experience": "wylding-woods"
}
```

---

## Tier 2: Content Discovery Tools

### 4. list_experience_content

**Purpose:** List content within an experience with optional filtering.

**Use When:**
- "Show me all waypoints"
- "List interactive waypoints"
- "What items exist in this game?"

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "list_experience_content",
        "description": "List content in an experience with optional filtering. If current_experience is set, experience parameter is optional.",
        "parameters": {
            "type": "object",
            "properties": {
                "experience": {
                    "type": "string",
                    "description": "Experience ID (optional if set_current_experience was called)"
                },
                "content_type": {
                    "type": "string",
                    "enum": ["waypoint", "room", "item", "npc", "all"],
                    "description": "Type of content to list"
                },
                "filters": {
                    "type": "object",
                    "description": "Optional filters",
                    "properties": {
                        "waypoint_type": {
                            "type": "string",
                            "enum": ["interactive", "narrative", "fx", "caution", "gps", "vps"]
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["content_type"]
        }
    }
}
```

**Example Response:**
```json
{
    "success": true,
    "content_type": "waypoint",
    "filters_applied": {"waypoint_type": "interactive"},
    "count": 12,
    "items": [
        {
            "id": "1_inter_woander_storefront",
            "name": "Woander Storefront",
            "waypoint_type": "interactive",
            "location": {"lat": 37.906233, "lng": -122.547721},
            "summary": "Scan marker to begin journey",
            "interaction": "scan_marker"
        },
        {
            "id": "8_inter_gravity_car",
            "name": "Gravity Car",
            "waypoint_type": "interactive",
            "location": {"lat": 37.905696, "lng": -122.547701},
            "summary": "Rotate wheel to activate",
            "interaction": "wheel_rotation"
        }
    ]
}
```

---

### 5. describe_content_item

**Purpose:** Get full details of a specific content item.

**Use When:**
- "Tell me about the Gravity Car"
- "Show me waypoint 8"
- "What's in this item?"

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "describe_content_item",
        "description": "Get full details of a specific content item (waypoint, room, item, NPC).",
        "parameters": {
            "type": "object",
            "properties": {
                "experience": {
                    "type": "string",
                    "description": "Experience ID (optional if current_experience set)"
                },
                "content_type": {
                    "type": "string",
                    "enum": ["waypoint", "room", "item", "npc"]
                },
                "content_id": {
                    "type": "string",
                    "description": "Content ID (e.g., '8_inter_gravity_car')"
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "Include raw YAML/markdown",
                    "default": False
                }
            },
            "required": ["content_type", "content_id"]
        }
    }
}
```

**Example Response:**
```json
{
    "success": true,
    "content": {
        "id": "8_inter_gravity_car",
        "name": "Gravity Car",
        "waypoint_type": "vps",
        "location": {
            "lat": 37.905696,
            "lng": -122.547700999999
        },
        "media": {
            "audio": "8-gravity-car-sounds.wav",
            "visual_fx": "spark_jump",
            "interaction": "wheel_rotation",
            "image_ref": "6-gravity-car.jpg",
            "display_text": "The historic Gravity Car awaits your touch..."
        }
    }
}
```

---

### 6. search_experience_content

**Purpose:** Semantic search within an experience.

**Use When:**
- "Find all car-related waypoints"
- "Search for music content"
- "What mentions the library?"

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "search_experience_content",
        "description": "Semantic search within an experience. Searches names, descriptions, and content.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "experience": {
                    "type": "string",
                    "description": "Experience ID (optional if current_experience set)"
                },
                "content_type": {
                    "type": "string",
                    "enum": ["waypoint", "room", "item", "npc", "all"],
                    "description": "Filter by content type",
                    "default": "all"
                }
            },
            "required": ["query"]
        }
    }
}
```

---

## Tier 3: Content Management Tools

### 7. get_content_template

**Purpose:** Learn content structure by reading existing examples (template-driven creation).

**Use When:** Before creating new content - the LLM needs to learn the structure.

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "get_content_template",
        "description": "Learn content structure by reading existing examples. Use this BEFORE creating new content. Returns examples that teach you what fields are needed and their formats.",
        "parameters": {
            "type": "object",
            "properties": {
                "experience": {"type": "string"},
                "content_type": {
                    "type": "string",
                    "enum": ["waypoint", "room", "item", "npc"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of examples to return",
                    "default": 3
                },
                "similar_to": {
                    "type": "string",
                    "description": "Optional: Get examples similar to this content_id"
                }
            },
            "required": ["content_type"]
        }
    }
}
```

**Example Response:**
```json
{
    "success": true,
    "content_type": "waypoint",
    "examples": [
        {
            "file_name": "1_inter_woander_storefront.md",
            "data": {
                "id": "1_inter_woander_storefront",
                "name": "Woander Storefront",
                "location": {"lat": 37.906233, "lng": -122.547721},
                "waypoint_type": "gps",
                "media": {...}
            }
        },
        {
            "file_name": "8_inter_gravity_car.md",
            "data": {...}
        }
    ],
    "learning_hints": {
        "required_fields": ["id", "name", "location", "waypoint_type", "media"],
        "optional_fields": ["tags", "prerequisites"],
        "field_types": {
            "id": "string (snake_case)",
            "name": "string",
            "location": "object with lat/lng floats",
            "waypoint_type": "enum: gps|vps"
        },
        "naming_pattern": "{number}_{type}_{name_slug}"
    }
}
```

---

### 8. create_experience_content

**Purpose:** Create new content after gathering all required fields through conversation.

**Use When:** After reading templates and collecting data from user.

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "create_experience_content",
        "description": "Create new content after: (1) Reading template examples, (2) Collecting data from user, (3) Getting confirmation. Validates, generates markdown, commits to Git.",
        "parameters": {
            "type": "object",
            "properties": {
                "experience": {"type": "string"},
                "content_type": {"type": "string"},
                "data": {
                    "type": "object",
                    "description": "Content data matching template structure"
                },
                "commit_message": {
                    "type": "string",
                    "description": "Git commit message (auto-generated if not provided)"
                }
            },
            "required": ["content_type", "data"]
        }
    }
}
```

**Example Request:**
```json
{
    "experience": "wylding-woods",
    "content_type": "waypoint",
    "data": {
        "id": "30_inter_secret_garden",
        "name": "Secret Garden",
        "location": {"lat": 37.9055, "lng": -122.5483},
        "waypoint_type": "gps",
        "media": {
            "audio": "30-garden-chimes.wav",
            "visual_fx": "flower_petals",
            "interaction": "tap",
            "display_text": "You discover a hidden garden..."
        }
    }
}
```

**Example Response:**
```json
{
    "success": true,
    "message": "Created waypoint 'Secret Garden'",
    "file_path": "/kb/experiences/wylding-woods/waypoints/30_inter_secret_garden.md",
    "commit_hash": "abc1234def5678",
    "git_message": "Add waypoint: Secret Garden",
    "sync_status": "Queued for next KB sync (within 15 minutes)"
}
```

---

### 9. edit_experience_content

**Purpose:** Edit existing content.

**Use When:**
- "Change the Gravity Car audio"
- "Update waypoint 8"
- "Fix the typo in this item"

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "edit_experience_content",
        "description": "Edit existing content. Supports partial updates (only change specified fields).",
        "parameters": {
            "type": "object",
            "properties": {
                "experience": {"type": "string"},
                "content_type": {"type": "string"},
                "content_id": {"type": "string"},
                "updates": {
                    "type": "object",
                    "description": "Fields to update (partial updates supported)"
                },
                "commit_message": {"type": "string"}
            },
            "required": ["content_type", "content_id", "updates"]
        }
    }
}
```

---

### 10. clone_experience_content

**Purpose:** Copy existing content as starting point for new content.

**Use When:**
- "Create something like the Gravity Car"
- "Copy this waypoint"
- "Make a similar item"

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "clone_experience_content",
        "description": "Copy existing content as starting point. Creates new ID and applies modifications.",
        "parameters": {
            "type": "object",
            "properties": {
                "source_id": {"type": "string"},
                "new_id": {"type": "string"},
                "modifications": {
                    "type": "object",
                    "description": "Fields to change in the clone"
                }
            },
            "required": ["source_id", "new_id"]
        }
    }
}
```

---

## Implementation Phases

### Phase 1: Core Content Tools (Priority 1)
**Timeline:** 4-6 hours

Tools 1-10 (Discovery + Content Management)
- Enables conversational content creation
- Demo-ready: Create waypoint through conversation

### Phase 2: Lifecycle & Progress (Priority 2)
**Timeline:** 2-3 days

Tools 11-16 (Lifecycle + Player Progress)
- Content scheduling, versioning
- Progress tracking, prerequisites

### Phase 3: Quality & Live Ops (Priority 3)
**Timeline:** 1-2 weeks

Tools 17-20 (Quality + Live Operations)
- Testing, review workflows
- Hot-patching, rollbacks, analytics

---

## Conversation Examples

### Example 1: Create Waypoint

```
Designer: "I want to work on Wylding Woods"

AI: [Calls set_current_experience("wylding-woods")]
    "Now working on Wylding Woods. What would you like to do?"

Designer: "Create a new waypoint"

AI: [Calls get_content_template(content_type="waypoint", limit=2)]
    [Reads examples: 1_inter_woander_storefront.md, 8_inter_gravity_car.md]

    "I'll help create a waypoint. Based on existing waypoints, I need:
    - Name and ID
    - Location (GPS or VPS positioning)
    - Media (audio, visuals, interactions)

    What should we call this waypoint?"

Designer: "Secret Garden"

AI: "Great! For the ID, I see the pattern is {number}_{type}_{name}.
    Since this will be waypoint #30, should the ID be:
    '30_inter_secret_garden' (interactive) or
    '30_narr_secret_garden' (narrative)?"

Designer: "30_inter_secret_garden"

AI: "Perfect. Where is this waypoint located?
    (Format: latitude, longitude. Example: 37.906233, -122.547721)"

[... conversation continues ...]

AI: "Here's what I'll create:

    📍 Waypoint: Secret Garden
    🆔 ID: 30_inter_secret_garden
    📍 Location: 37.9055, -122.5483
    🎮 Type: GPS
    🎵 Audio: 30-garden-chimes.wav
    ✨ Visual FX: flower_petals

    Does this look correct? (yes/edit/cancel)"

Designer: "yes"

AI: [Calls create_experience_content(...)]

    "✅ Created waypoint at /kb/experiences/wylding-woods/waypoints/30_inter_secret_garden.md
    🔄 Committed to Git: 'Add waypoint: Secret Garden' (abc1234)
    ⏰ Will be live within 15 minutes"
```

---

## Summary

**20 Experience Tools organized by purpose:**

| Purpose | Tool Count | Phase |
|---------|-----------|-------|
| **Discovery** | 3 | Phase 1 |
| **Content Discovery** | 3 | Phase 1 |
| **Content Management** | 4 | Phase 1 |
| **Lifecycle Management** | 2 | Phase 2 |
| **Player Progress** | 2 | Phase 2 |
| **Quality Assurance** | 3 | Phase 3 |
| **Live Operations** | 3 | Phase 3 |
| **Total** | **20** | |

**Key Benefits:**
- ✅ Natural conversation replaces forms and file editing
- ✅ Template-driven learning (LLM learns from existing content)
- ✅ Context preservation (set experience once)
- ✅ Git-backed version control
- ✅ Industry-standard features (A/B testing, analytics, hot-patching)

**Next:** See [Experience Data Models](./experience-data-models.md) for database schemas.
