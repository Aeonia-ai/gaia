# KB Document Database Design

## Why Document DB Makes Sense

### Natural Fit for KB
```javascript
// A KB document maps perfectly to NoSQL
{
  "_id": "gaia/architecture/overview.md",
  "content": "# Architecture Overview\n\nGaia platform uses...",
  "metadata": {
    "title": "Architecture Overview",
    "tags": ["architecture", "backend", "microservices"],
    "author": "user-123",
    "created": "2024-01-15T10:30:00Z",
    "modified": "2024-01-16T14:20:00Z"
  },
  "version": 3,
  "locked_by": null  // or {"user": "user-456", "expires": "2024-01-16T15:00:00Z"}
}
```

## MongoDB Advantages

### 1. **Path as ID**
```javascript
// Natural file paths as document IDs
db.kb.findOne({_id: "gaia/specs/kb-integration.md"})

// List directory
db.kb.find({_id: {$regex: "^gaia/specs/"}})
```

### 2. **Simple Updates**
```javascript
// No SQL, no joins, just update
db.kb.updateOne(
  {_id: "gaia/architecture.md", version: 3},
  {
    $set: {
      content: "# Updated Architecture...",
      "metadata.modified": new Date(),
      "metadata.modified_by": userId
    },
    $inc: {version: 1}
  }
)
```

### 3. **Built-in Versioning**
```javascript
{
  "_id": "gaia/api.md",
  "content": "Current content...",
  "version": 5,
  "history": [
    {
      "version": 4,
      "content": "Previous content...",
      "modified": "2024-01-15T10:00:00Z",
      "modified_by": "user-123"
    }
    // Keep last N versions inline
  ]
}
```

### 4. **Full-Text Search**
```javascript
// MongoDB Atlas Search (Lucene-based)
db.kb.aggregate([
  {
    $search: {
      text: {
        query: "consciousness embodiment",
        path: ["content", "metadata.tags"]
      }
    }
  }
])
```

## Comparison: PostgreSQL vs MongoDB for KB

| Feature | PostgreSQL | MongoDB |
|---------|------------|---------|
| Schema | Define tables/columns | Just store documents |
| File paths | VARCHAR with indexes | Natural document IDs |
| Metadata | JSONB column | Native JSON |
| Search | Full-text (good) | Atlas Search (excellent) |
| Versioning | Separate table | Embedded or GridFS |
| Setup complexity | Medium | Simple |
| Scalability | Vertical mainly | Horizontal sharding |

## Simple Implementation

### Models
```python
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict

class KBDocument(BaseModel):
    _id: str  # Path like "gaia/architecture.md"
    content: str
    metadata: Dict = {}
    version: int = 1
    locked_by: Optional[Dict] = None
    created: datetime = datetime.utcnow()
    modified: datetime = datetime.utcnow()

class KBService:
    def __init__(self):
        self.client = AsyncIOMotorClient("mongodb://localhost:27017")
        self.db = self.client.kb_database
        self.collection = self.db.documents
    
    async def read_file(self, path: str) -> Optional[KBDocument]:
        doc = await self.collection.find_one({"_id": path})
        return KBDocument(**doc) if doc else None
    
    async def write_file(self, path: str, content: str, user_id: str) -> bool:
        # Simple optimistic locking
        result = await self.collection.update_one(
            {"_id": path},
            {
                "$set": {
                    "content": content,
                    "metadata.modified_by": user_id,
                    "modified": datetime.utcnow()
                },
                "$inc": {"version": 1}
            },
            upsert=True
        )
        return result.modified_count > 0
    
    async def search(self, query: str) -> List[KBDocument]:
        # Simple regex search (Atlas Search is better)
        cursor = self.collection.find({
            "content": {"$regex": query, "$options": "i"}
        }).limit(20)
        return [KBDocument(**doc) async for doc in cursor]
```

### Docker Compose Addition
```yaml
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: gaia
      MONGO_INITDB_ROOT_PASSWORD: gaia_password
```

## Migration Path

### Option 1: Side-by-Side
```python
# Keep Git for reading, MongoDB for writing
class HybridKBService:
    async def read_file(self, path: str):
        # Try MongoDB first
        doc = await self.mongo.find_one({"_id": path})
        if doc:
            return doc['content']
        
        # Fall back to Git
        return self.read_from_git(path)
```

### Option 2: Bulk Import
```python
# One-time import script
async def import_kb_to_mongo():
    for file_path in Path("/kb").rglob("*.md"):
        content = file_path.read_text()
        relative_path = str(file_path.relative_to("/kb"))
        
        await db.documents.insert_one({
            "_id": relative_path,
            "content": content,
            "metadata": extract_frontmatter(content),
            "version": 1,
            "created": datetime.utcnow()
        })
```

## Bonus: Real-Time Updates

```python
# MongoDB Change Streams
async def watch_changes():
    async with db.documents.watch() as stream:
        async for change in stream:
            # Notify connected clients via WebSocket
            await broadcast_change(change)
```

## The Simplicity Win

### Before (PostgreSQL + Git)
- Define schema
- Create migrations  
- Handle Git operations
- Manage sync conflicts
- Complex queries with JOINs

### After (MongoDB)
- Store documents
- Natural file paths
- Built-in versioning
- No schema migrations
- Simple queries

## Trade-offs

### MongoDB Pros
- ✅ Perfect fit for documents
- ✅ Simple to implement
- ✅ Flexible schema
- ✅ Great search (Atlas)
- ✅ Real-time change streams

### MongoDB Cons
- ❌ Another database to manage
- ❌ No ACID across documents
- ❌ Less familiar to team?

### PostgreSQL Pros
- ✅ Already in our stack
- ✅ ACID guarantees
- ✅ Can use same DB

### PostgreSQL Cons  
- ❌ Documents don't fit naturally
- ❌ More complex schema
- ❌ Requires more code

## Recommendation

If starting fresh, MongoDB would be simpler for KB storage. But since we already have PostgreSQL, we could:

1. Use PostgreSQL's document features (JSONB)
2. Add MongoDB just for KB
3. Use a document DB like FerretDB (MongoDB protocol on PostgreSQL)

What do you think? Should we explore MongoDB further or stick with PostgreSQL but use it more like a document store?