# KB Architecture Guide

**Created**: January 2025  
**Purpose**: Comprehensive guide to KB storage architecture, from current Git implementation to future multi-user database design

## Current Architecture: Git-Based Storage

The KB currently uses Git for storage, which works well for single-user scenarios:
- Version control built-in
- Easy local development
- Portable and human-readable
- Works with existing tools (VS Code, Obsidian)

### Git Limitations for Multi-User

1. **Conflict Resolution Complexity**
   - Git merge conflicts require technical knowledge
   - Non-technical users can't resolve conflicts
   - Automatic resolution risks data loss

2. **Synchronization Delays**
   - Push/pull model isn't real-time
   - Users may work on outdated content
   - "Lost update" problem when users overwrite each other's changes

3. **Concurrency Issues**
   ```
   User A: Reads file → Edits → Commits → Pushes ✓
   User B: Reads file → Edits → Commits → Push fails ✗
           Must pull, merge, resolve conflicts, push again
   ```

4. **Binary Files**
   - Images, PDFs don't merge
   - Large files bloat repository
   - Git LFS adds complexity

## Future Architecture Options

### Option 1: PostgreSQL + JSONB (Recommended)

**Why PostgreSQL?**
- Already in our stack - no new dependencies
- ACID guarantees prevent data corruption
- Proven scalability for millions of documents
- Rich features: full-text search, JSONB queries, triggers
- Optimistic locking for simple conflict prevention

**Schema Design:**
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

-- Smart indexing for path operations
CREATE INDEX idx_path_prefix ON kb_documents(path text_pattern_ops);
CREATE INDEX idx_metadata ON kb_documents USING GIN (metadata);
```

**Implementation:**
```python
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

### Option 2: MongoDB Document Store

**Natural Fit for KB:**
```javascript
{
  "_id": "gaia/architecture/overview.md",
  "content": "# Architecture Overview\n...",
  "metadata": {
    "title": "Architecture Overview",
    "tags": ["backend", "microservices"],
    "lastModified": "2024-01-15T10:30:00Z"
  },
  "versions": [
    { v: 1, content: "...", author: "user123", date: "..." }
  ],
  "locks": {
    "current": null,  // or { user: "user456", expires: "..." }
  }
}
```

**Advantages:**
- Path as natural document ID
- No schema migrations
- Flexible metadata
- Built-in GridFS for large files

**Trade-offs:**
- New dependency to manage
- Less mature query capabilities
- No ACID across documents

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

**Benefits:**
- Active documents in PostgreSQL for speed
- Git archive for history and portability
- Best of both worlds

## Virtual Filesystem Abstraction

Regardless of storage backend, we maintain a filesystem-like interface:

### API Design
```python
class VirtualKBFilesystem:
    """Makes database look like a filesystem"""
    
    async def ls(self, path: str = "/") -> List[str]:
        """List directory contents"""
        results = await db.fetch("""
            SELECT path FROM kb_documents 
            WHERE path LIKE $1 || '%'
            AND path NOT LIKE $1 || '%/%/%'
            ORDER BY path
        """, path.rstrip('/') + '/')
        return [Path(r['path']).name for r in results]
    
    async def cat(self, path: str) -> str:
        """Read file content"""
        doc = await db.fetchone(
            "SELECT content FROM kb_documents WHERE path = $1",
            path
        )
        if not doc:
            raise FileNotFoundError(f"No such file: {path}")
        return doc['content']
    
    async def write(self, path: str, content: str):
        """Write file content with optimistic locking"""
        # Implementation with version checking
```

### CLI Tools
```bash
# Filesystem-like commands
$ kb ls /gaia/specs
kb-integration.md
api-design.md

$ kb cat gaia/specs/api-design.md
# API Design Specification
...

$ kb tree gaia/
gaia/
├── architecture/
│   ├── overview.md
│   └── microservices.md
└── specs/
    ├── api-design.md
    └── kb-integration.md
```

### Web UI Integration
```javascript
// React file explorer component
<FileExplorer 
  onNavigate={path => api.listDirectory(path)}
  onOpen={file => api.readFile(file.path)}
  onEdit={file => api.updateFile(file.path, content)}
/>
```

## Multi-User Features

### User Namespaces
```
/shared/          # Shared across all users
/team/{team-id}/  # Team workspaces
/user/{user-id}/  # Personal workspace
```

### Permissions Model
```python
class KBPermission(Base):
    __tablename__ = "kb_permissions"
    
    path_pattern = Column(String)  # e.g., "/team/engineering/*"
    principal_type = Column(Enum("user", "team", "role"))
    principal_id = Column(UUID)
    permissions = Column(ARRAY(String))  # ["read", "write", "delete"]
```

### Conflict Prevention
1. **Optimistic Locking** - Version checking on updates
2. **Pessimistic Locking** - Optional exclusive locks for critical documents
3. **Real-time Collaboration** - WebSocket notifications of changes
4. **Merge Strategies** - Automatic merging for non-conflicting changes

## Migration Path

### Phase 1: Current State (Git-Only)
- ✅ Single Git repository
- ✅ Local development friendly
- ✅ Basic CRUD operations

### Phase 2: Database Cache (In Progress)
- Add PostgreSQL for active documents
- Keep Git as source of truth
- Cache frequently accessed content

### Phase 3: Database Primary
- PostgreSQL becomes primary storage
- Git becomes optional archive
- Full multi-user support

### Phase 4: Advanced Features
- Real-time collaboration
- CRDT-based conflict resolution
- Cross-device sync
- Offline support

## Implementation Decisions

### Why PostgreSQL Over MongoDB?
1. **Already in stack** - No new operational burden
2. **ACID transactions** - Critical for data integrity
3. **Mature ecosystem** - Better tooling and support
4. **SQL familiarity** - Team already knows it
5. **JSONB flexibility** - Document-like features when needed

### Why Not Pure CRDTs?
1. **Complexity** - Hard to implement correctly
2. **Storage overhead** - CRDTs are space-intensive
3. **Limited queries** - Difficult to search/filter
4. **Overkill** - Our conflict rate is low

## Performance Considerations

### Database Optimizations
```sql
-- Path-based queries
CREATE INDEX idx_path_prefix ON kb_documents(path text_pattern_ops);

-- Full-text search
CREATE INDEX idx_search ON kb_documents USING GIN(to_tsvector('english', content));

-- Metadata queries
CREATE INDEX idx_metadata ON kb_documents USING GIN (metadata);

-- Parent path for directory listings (computed column)
ALTER TABLE kb_documents ADD COLUMN parent_path TEXT 
GENERATED ALWAYS AS (regexp_replace(path, '/[^/]+$', '')) STORED;
CREATE INDEX idx_parent ON kb_documents(parent_path);
```

### Caching Strategy
1. **Redis** - Hot documents and directory listings
2. **Local cache** - Recently accessed documents
3. **CDN** - Public/shared documents
4. **Lazy loading** - Load content only when needed

## Security Considerations

1. **Path traversal protection** - Validate all paths
2. **SQL injection prevention** - Use parameterized queries
3. **Access control** - Check permissions on every operation
4. **Audit logging** - Track all modifications
5. **Encryption** - Sensitive documents encrypted at rest

## Testing Strategy

1. **Unit tests** - Virtual filesystem operations
2. **Integration tests** - Database operations
3. **Load tests** - Multi-user scenarios
4. **Migration tests** - Git to database migration
5. **Recovery tests** - Backup and restore

## Related Documentation

- [KB Git Sync Guide](../guides/kb-git-sync-guide.md) - Current Git implementation
- [Multi-User KB Guide](../guides/multi-user-kb-guide.md) - Multi-user features
- [KB Deployment Checklist](../deployment/kb-deployment-checklist.md) - Production deployment