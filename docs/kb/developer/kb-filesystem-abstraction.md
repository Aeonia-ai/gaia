# KB Filesystem Abstraction Layer

## The Challenge
Users expect filesystem operations but data lives in a database. How do we bridge this gap?

## Solution: Virtual Filesystem API

### 1. **Path-Based Operations**
```python
class VirtualKBFilesystem:
    """Makes database look like a filesystem"""
    
    async def ls(self, path: str = "/") -> List[str]:
        """List directory contents"""
        # Query: Find all paths starting with 'path/'
        results = await db.fetch("""
            SELECT path FROM kb_documents 
            WHERE path LIKE $1 || '%'
            AND path NOT LIKE $1 || '%/%/%'
            ORDER BY path
        """, path.rstrip('/') + '/')
        
        # Return just filenames, like real ls
        return [Path(r['path']).name for r in results]
    
    async def tree(self, path: str = "/") -> dict:
        """Recursive directory structure"""
        # Returns:
        # {
        #   "gaia/": {
        #     "specs/": {
        #       "kb-integration.md": {},
        #       "api-design.md": {}
        #     },
        #     "README.md": {}
        #   }
        # }
    
    async def cat(self, path: str) -> str:
        """Read file content"""
        doc = await db.fetchone(
            "SELECT document->>'content' as content FROM kb_documents WHERE path = $1",
            path
        )
        if not doc:
            raise FileNotFoundError(f"No such file: {path}")
        return doc['content']
    
    async def mkdir(self, path: str):
        """Create directory (just a convention)"""
        # Directories don't really exist, but we can track them
        await db.execute(
            "INSERT INTO kb_documents (path, document) VALUES ($1, $2)",
            path.rstrip('/') + '/.directory',
            {"type": "directory", "created": datetime.utcnow()}
        )
```

### 2. **FUSE Mount (Advanced)**
```python
# Make database actually mountable as filesystem!
# pip install fusepy

import fuse
import json

class KBFS(fuse.Operations):
    """FUSE filesystem backed by database"""
    
    def readdir(self, path, fh):
        # Query database for directory listing
        entries = self.db.list_directory(path)
        return ['.', '..'] + entries
    
    def read(self, path, size, offset, fh):
        # Get from database
        content = self.db.get_content(path)
        return content[offset:offset + size].encode()
    
    def write(self, path, data, offset, fh):
        # Write to database
        self.db.update_content(path, data.decode(), offset)
        return len(data)

# Mount it!
# mkdir /mnt/kb
# python kb_fuse.py /mnt/kb
# Now you can: cat /mnt/kb/gaia/README.md
```

### 3. **CLI Tools That Feel Natural**
```bash
# kb-cli that mimics standard tools
$ kb ls /gaia/specs
kb-integration.md
api-design.md
database-schema.md

$ kb cat gaia/specs/api-design.md
# API Design Specification
...

$ kb find . -name "*.md" | kb grep "consciousness"
influences/consciousness.md:42: The nature of consciousness...
mmoirl/embodiment.md:17: ...consciousness requires embodiment

$ kb tree gaia/
gaia/
├── architecture/
│   ├── overview.md
│   └── microservices.md
├── specs/
│   ├── api-design.md
│   └── kb-integration.md
└── README.md
```

### 4. **Web UI File Browser**
```javascript
// React component that feels like file explorer
<FileExplorer 
  onNavigate={path => api.listDirectory(path)}
  onOpen={file => api.readFile(file.path)}
  onEdit={file => api.updateFile(file.path, content)}
/>

// Returns hierarchical data from flat database
GET /api/v0.2/kb/browse?path=/gaia
{
  "directories": ["architecture", "specs", "docs"],
  "files": ["README.md", "TODO.md"],
  "breadcrumbs": ["gaia"]
}
```

### 5. **Database Schema for Filesystem Ops**

#### PostgreSQL Approach
```sql
-- Smart indexing for path operations
CREATE TABLE kb_documents (
    path TEXT PRIMARY KEY,
    document JSONB,
    -- Computed columns for fast queries
    parent_path TEXT GENERATED ALWAYS AS (
        CASE 
            WHEN path LIKE '%/%' 
            THEN regexp_replace(path, '/[^/]+$', '')
            ELSE '/'
        END
    ) STORED,
    filename TEXT GENERATED ALWAYS AS (
        regexp_replace(path, '^.*/', '')
    ) STORED,
    depth INTEGER GENERATED ALWAYS AS (
        array_length(string_to_array(path, '/'), 1) - 1
    ) STORED
);

-- Indexes for fast filesystem operations
CREATE INDEX idx_parent_path ON kb_documents(parent_path);
CREATE INDEX idx_depth ON kb_documents(depth);

-- List directory is now super fast
SELECT filename FROM kb_documents 
WHERE parent_path = '/gaia/specs'
ORDER BY filename;
```

#### MongoDB Approach
```javascript
// Store path components for easy querying
{
  "_id": "gaia/specs/api-design.md",
  "path": {
    "full": "gaia/specs/api-design.md",
    "parts": ["gaia", "specs", "api-design.md"],
    "parent": "gaia/specs",
    "name": "api-design.md",
    "depth": 2
  },
  "content": "# API Design...",
  "metadata": {...}
}

// List directory is simple
db.kb.find({
  "path.parent": "gaia/specs"
}).sort({"path.name": 1})
```

## Implementation Examples

### 1. **FastAPI Filesystem Endpoints**
```python
@app.get("/api/v0.2/kb/fs/ls")
async def list_directory(path: str = "/"):
    """List directory contents with metadata"""
    entries = await kb_fs.ls(path)
    return {
        "path": path,
        "entries": [
            {
                "name": entry.name,
                "type": entry.type,  # "file" or "directory"
                "size": entry.size,
                "modified": entry.modified
            }
            for entry in entries
        ]
    }

@app.get("/api/v0.2/kb/fs/tree")
async def directory_tree(path: str = "/", max_depth: int = 3):
    """Get directory tree structure"""
    return await kb_fs.tree(path, max_depth)

@app.get("/api/v0.2/kb/fs/cat/{path:path}")
async def read_file(path: str):
    """Read file content (like cat command)"""
    content = await kb_fs.cat(path)
    return PlainTextResponse(content)
```

### 2. **Local Development Bridge**
```python
# Sync database to local filesystem for development
class KBLocalSync:
    async def export_to_filesystem(self, db_path: str, fs_path: str):
        """Export database KB to local filesystem"""
        docs = await db.fetch("SELECT path, document FROM kb_documents")
        for doc in docs:
            file_path = Path(fs_path) / doc['path']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(doc['document']['content'])
    
    async def watch_and_sync(self, fs_path: str):
        """Watch local filesystem and sync to database"""
        # Use watchdog to monitor changes
        # Update database when files change locally
```

## The Best Part: Progressive Enhancement

### Start Simple
1. Database storage with path-based API
2. Basic ls/cat/write operations
3. Web UI file browser

### Add As Needed
1. FUSE mount for true filesystem access
2. Local sync for development
3. Advanced file operations
4. Git export for backups

## Summary

Yes, we can absolutely maintain a filesystem-oriented view! The database becomes an implementation detail. Users still:
- Navigate directories
- Read/write files  
- Use familiar paths
- Get filesystem-like CLI tools

The difference is:
- No sync conflicts
- Better performance
- Rich queries
- Real-time updates
- Version history

Want me to implement the virtual filesystem layer? It would give us the best of both worlds!