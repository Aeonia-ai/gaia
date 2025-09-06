# Instrumentation Module

## Overview

The Instrumentation module (`app/shared/instrumentation.py`) provides comprehensive performance monitoring and timing infrastructure for tracking request processing stages throughout the platform.

## Core Components

### TimingContext Class

A dataclass that tracks timing across request lifecycle:

```python
@dataclass
class TimingContext:
    request_id: str
    start_time: float
    stages: Dict[str, float]
    stage_durations: Dict[str, float]
    metadata: Dict[str, Any]
```

### Key Methods

#### `record_stage(stage_name: str, duration_ms: Optional[float] = None)`
- Records completion of a processing stage
- Calculates duration automatically if not provided
- Logs stage timing with request ID

#### `get_total_duration() -> float`
- Returns total request duration in milliseconds

#### `get_summary() -> Dict[str, Any]`
- Returns comprehensive timing summary with all stages

## Global Instrumentation System

The module provides a singleton `InstrumentationSystem` class that:
- Manages timing contexts across requests
- Tracks concurrent request processing
- Provides decorators for automatic instrumentation
- Generates performance reports

### Key Functions

#### `record_stage(request_id: str, stage: str, duration_ms: float = None)`
Global function to record stage timing for any request.

#### `instrument_async_operation(operation_name: str)`
Decorator for automatically timing async functions.

#### `@contextmanager timing_scope(request_id: str, scope_name: str)`
Context manager for timing code blocks.

## Usage Examples

### Basic Stage Recording
```python
from app.shared.instrumentation import instrumentation, record_stage

# Record a stage
record_stage(request_id, "auth_check", 15.3)

# Auto-calculate duration
record_stage(request_id, "llm_call")
```

### Using Decorators
```python
@instrument_async_operation("database_query")
async def get_user(user_id: str):
    # Automatically timed
    return await db.fetch_user(user_id)
```

### Context Manager
```python
with timing_scope(request_id, "redis_operations"):
    # All operations in this block are timed
    cache_result = await redis.get(key)
```

## Typical Stages Tracked

- `routing_analysis` - Chat routing decisions
- `auth_check` - Authentication validation
- `kb_access` - Knowledge base queries
- `llm_request` - LLM API calls
- `response_formatting` - Output preparation
- `redis_cache` - Cache operations
- `database_query` - DB operations

## Integration Points

Used extensively by:
- Gateway service (request routing)
- Chat service (LLM operations)
- Auth service (validation timing)
- Intelligent router (decision timing)

## Performance Impact

- Minimal overhead (<0.1ms per stage)
- Async-safe implementation
- Thread-safe for concurrent requests

## Status

- **Status**: ✅ Active
- **Priority**: High (performance monitoring)
- **Used by**: All services for APM