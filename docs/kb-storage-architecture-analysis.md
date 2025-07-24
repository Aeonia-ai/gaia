# KB Storage Architecture Analysis

## Current Situation
We have a Git-based KB that works well for single-user scenarios but may not scale for multi-user collaborative editing.

## Git Limitations for Multi-User Scenarios

### 1. **Conflict Resolution Complexity**
- Git merge conflicts require technical knowledge
- Non-technical users can't resolve conflicts
- Automatic resolution risks data loss

### 2. **Synchronization Delays**
- Push/pull model isn't real-time
- Users may work on outdated content
- "Lost update" problem when users overwrite each other's changes

### 3. **Concurrency Issues**
```
User A: Reads file → Edits → Commits → Pushes ✓
User B: Reads file → Edits → Commits → Push fails ✗
        Must pull, merge, resolve conflicts, push again
```

### 4. **Binary Files**
- Images, PDFs don't merge
- Large files bloat repository
- Git LFS adds complexity

## Alternative Architectures

### Option 1: PostgreSQL + JSONB (Recommended)
```sql
CREATE TABLE kb_documents (
    id UUID PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    content TEXT,
    metadata JSONB,
    version INTEGER DEFAULT 1,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE kb_versions (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES kb_documents(id),
    version INTEGER,
    content TEXT,
    metadata JSONB,
    changed_by UUID,
    change_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Pros:**
- ACID transactions prevent conflicts
- Row-level locking for concurrent edits
- Fast queries with indexes
- Easy backup/restore
- Works with existing PostgreSQL

**Cons:**
- Loses file system navigation
- Need to implement versioning
- Less intuitive than files

### Option 2: CRDTs (Conflict-free Replicated Data Types)
**Examples:** Yjs, Automerge, ShareJS

```javascript
// Automatic conflict resolution
doc1.text.insert(0, "Hello ")  // User A
doc2.text.insert(0, "Hi ")     // User B
// Result: "Hi Hello " (both edits preserved)
```

**Pros:**
- Real-time collaboration
- Automatic conflict resolution
- Works offline
- No central server needed

**Cons:**
- Complex to implement
- Storage overhead
- Limited query capabilities

### Option 3: Hybrid Approach (Git + Database)
```
┌─────────────────┐
│   PostgreSQL    │  ← Real-time edits, locks, search
│  (Active Docs)  │
└────────┬────────┘
         │ Periodic snapshot
         ▼
┌─────────────────┐
│      Git        │  ← Version history, audit trail
│  (Archive)      │
└─────────────────┘
```

**Implementation:**
1. Active documents in PostgreSQL
2. Optimistic locking prevents conflicts
3. Full-text search with pg_trgm
4. Periodic Git commits for history
5. Best of both worlds

### Option 4: Document Database
**MongoDB Example:**
```javascript
{
  _id: "kb/gaia/architecture.md",
  content: "# Architecture\n...",
  metadata: {
    title: "Gaia Architecture",
    tags: ["backend", "microservices"],
    lastModified: "2024-01-15T10:30:00Z"
  },
  versions: [
    { v: 1, content: "...", author: "user123", date: "..." }
  ],
  locks: {
    current: null,  // or { user: "user456", expires: "..." }
  }
}
```

## Recommendation: PostgreSQL-First Architecture

### Why PostgreSQL?
1. **Already in our stack** - No new dependencies
2. **ACID guarantees** - Prevents data corruption
3. **Proven scalability** - Handles millions of documents
4. **Rich features** - Full-text search, JSONB queries, triggers
5. **Optimistic locking** - Simple conflict prevention

### Implementation Plan

```python
# models/kb_document.py
class KBDocument(Base):
    __tablename__ = "kb_documents"
    
    id = Column(UUID, primary_key=True)
    path = Column(String, unique=True, index=True)
    content = Column(Text)
    metadata = Column(JSONB)
    version = Column(Integer, default=1)
    search_vector = Column(TSVector)  # Full-text search
    
    # Optimistic locking
    def update(self, new_content, expected_version):
        if self.version != expected_version:
            raise VersionConflictError()
        self.content = new_content
        self.version += 1
```

### Features We Get "For Free"
1. **Concurrent editing** with row-level locks
2. **Full-text search** with PostgreSQL FTS
3. **ACID transactions** prevent corruption
4. **Point-in-time recovery** with PostgreSQL
5. **Replication** for read scaling

### Migration Path
1. Keep Git for read-only base KB
2. New edits go to PostgreSQL
3. Gradually migrate existing content
4. Git becomes optional archive

## Conclusion

While Git is excellent for source code, it's not ideal for multi-user document collaboration. PostgreSQL provides:
- ✅ Conflict prevention (not resolution)
- ✅ Real-time updates
- ✅ Scalability
- ✅ Search capabilities
- ✅ Simple implementation

The hybrid approach lets us keep Git's benefits (history, portability) while solving its multi-user limitations.