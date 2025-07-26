# KB Wiki Interface Design

## Why Wiki + KB = Perfect Match

### Natural Features Alignment
- **Wiki-style links**: `[[gaia/architecture]]` → Already have paths!
- **Revision history**: Already tracking versions
- **Collaborative editing**: Already multi-user capable
- **Search**: Already implemented
- **Categories/Tags**: Already in metadata

## Core Wiki Features

### 1. **Wiki-Link Navigation**
```markdown
# In your markdown files
Check out the [[gaia/architecture/overview]] for details.
See also [[influences/consciousness]] and [[mmoirl/embodiment]].

# Renders as clickable links
# Click takes you to that KB document
```

### 2. **Automatic Backlinks**
```python
# When viewing gaia/architecture/overview.md
# Automatically shows at bottom:

## Referenced By
- [[gaia/specs/api-design]] - "follows the architecture outlined in..."
- [[gaia/implementation/services]] - "based on the overview architecture..."
- [[meeting-notes/2024-01-15]] - "discussed architecture changes..."
```

### 3. **Wiki-Style URLs**
```
# Instead of filesystem paths:
/kb/fs/gaia/specs/api-design.md

# Wiki-friendly URLs:
/wiki/gaia/specs/api-design
/wiki/influences/consciousness
/w/gaia  # Short form
```

## Implementation Design

### 1. **Enhanced KB Schema**
```sql
-- Add wiki-specific features to documents
ALTER TABLE kb_documents ADD COLUMN wiki_data JSONB DEFAULT '{}';

-- Example wiki_data:
{
  "aliases": ["API Spec", "API Design"],
  "redirects_to": null,
  "categories": ["Architecture", "Documentation"],
  "wiki_links": ["gaia/architecture", "guides/api-development"],
  "backlinks": ["gaia/overview", "tutorials/getting-started"]
}

-- Fast link lookups
CREATE INDEX idx_wiki_links ON kb_documents USING GIN ((wiki_data->'wiki_links'));
CREATE INDEX idx_backlinks ON kb_documents USING GIN ((wiki_data->'backlinks'));
```

### 2. **Wiki Parser Service**
```python
import re
from typing import List, Tuple

class WikiParser:
    """Parse and render wiki-style content"""
    
    # Match [[wiki links]]
    WIKI_LINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')
    
    async def parse_content(self, content: str, current_path: str) -> dict:
        """Parse markdown with wiki enhancements"""
        
        # Extract wiki links
        wiki_links = self.extract_wiki_links(content)
        
        # Convert to HTML with working links
        html = self.render_wiki_content(content, current_path)
        
        # Extract metadata
        categories = self.extract_categories(content)
        
        return {
            "html": html,
            "wiki_links": wiki_links,
            "categories": categories
        }
    
    def extract_wiki_links(self, content: str) -> List[str]:
        """Find all [[wiki links]] in content"""
        links = []
        for match in self.WIKI_LINK_PATTERN.finditer(content):
            link_path = match.group(1)
            links.append(link_path)
        return links
    
    def render_wiki_content(self, content: str, current_path: str) -> str:
        """Convert wiki syntax to HTML"""
        
        def replace_wiki_link(match):
            path = match.group(1)
            label = match.group(2) or path.split('/')[-1]
            
            # Make relative links absolute
            if not path.startswith('/'):
                base = '/'.join(current_path.split('/')[:-1])
                path = f"{base}/{path}"
            
            return f'<a href="/wiki/{path}" class="wiki-link">{label}</a>'
        
        # Replace wiki links
        content = self.WIKI_LINK_PATTERN.sub(replace_wiki_link, content)
        
        # Render markdown to HTML
        return markdown.render(content)
```

### 3. **Wiki UI Components**

#### **A. Wiki Page View**
```html
<!-- FastHTML Template -->
<div class="wiki-page">
  <!-- Breadcrumb navigation -->
  <nav class="breadcrumb">
    <a href="/wiki">KB</a> /
    <a href="/wiki/gaia">gaia</a> /
    <a href="/wiki/gaia/specs">specs</a> /
    <span>api-design</span>
  </nav>
  
  <!-- Page actions -->
  <div class="page-actions">
    <button onclick="editPage()">Edit</button>
    <button onclick="showHistory()">History</button>
    <button onclick="showBacklinks()">Links Here</button>
  </div>
  
  <!-- Main content -->
  <article class="wiki-content">
    <!-- Rendered markdown with wiki links -->
  </article>
  
  <!-- Sidebar -->
  <aside class="wiki-sidebar">
    <h3>Page Info</h3>
    <ul>
      <li>Last edited: 2 hours ago</li>
      <li>Categories: Architecture, API</li>
      <li>Linked pages: 5</li>
    </ul>
    
    <h3>Related Pages</h3>
    <ul>
      <li><a href="/wiki/gaia/architecture">Architecture Overview</a></li>
      <li><a href="/wiki/guides/api">API Guide</a></li>
    </ul>
  </aside>
</div>
```

#### **B. Wiki Edit Mode**
```javascript
// Live preview while editing
const WikiEditor = {
  content: '',
  preview: null,
  
  init() {
    // Setup split view: editor | preview
    this.editor = CodeMirror.fromTextArea(document.getElementById('editor'), {
      mode: 'markdown',
      lineNumbers: true,
      extraKeys: {
        'Ctrl-Space': 'autocomplete'  // Autocomplete wiki links!
      }
    });
    
    // Live preview updates
    this.editor.on('change', () => this.updatePreview());
    
    // Wiki link autocomplete
    this.setupAutocomplete();
  },
  
  setupAutocomplete() {
    // When user types [[, show suggestions
    CodeMirror.registerHelper('hint', 'markdown', (editor) => {
      const cur = editor.getCursor();
      const token = editor.getTokenAt(cur);
      
      if (token.string.startsWith('[[')) {
        const search = token.string.slice(2);
        return this.searchPages(search).then(pages => ({
          list: pages.map(p => ({
            text: `[[${p.path}]]`,
            displayText: p.title
          })),
          from: CodeMirror.Pos(cur.line, token.start),
          to: CodeMirror.Pos(cur.line, token.end)
        }));
      }
    });
  }
};
```

### 4. **Special Wiki Pages**

#### **Recent Changes**
```python
@app.get("/wiki/Special:RecentChanges")
async def recent_changes(limit: int = 50):
    changes = await db.fetch("""
        SELECT path, 
               document->>'modified' as modified,
               document->'metadata'->>'modified_by' as author,
               document->'metadata'->>'summary' as summary
        FROM kb_documents
        ORDER BY document->>'modified' DESC
        LIMIT $1
    """, limit)
    
    return render_template("wiki/recent_changes.html", changes=changes)
```

#### **Search with Wiki Features**
```python
@app.get("/wiki/Special:Search")
async def wiki_search(q: str, type: str = "all"):
    if type == "title":
        # Search in paths/titles only
        results = await search_titles(q)
    elif type == "content": 
        # Full text search
        results = await search_content(q)
    else:
        # Search everything
        results = await search_all(q)
    
    return render_template("wiki/search_results.html", 
                         query=q, results=results)
```

### 5. **Wiki-Style Categories**
```python
# Auto-generate category pages
@app.get("/wiki/Category:{category}")
async def category_page(category: str):
    pages = await db.fetch("""
        SELECT path, document->>'title' as title
        FROM kb_documents
        WHERE document->'metadata'->'categories' ? $1
        ORDER BY document->>'title'
    """, category)
    
    return render_template("wiki/category.html", 
                         category=category, pages=pages)
```

## Advanced Features

### 1. **Transclusion**
```markdown
# Include content from another page
{{include:gaia/templates/header}}

# Include a specific section
{{include:gaia/api-design#authentication}}
```

### 2. **Templates**
```markdown
# Define template
<!-- In: templates/component -->
**Component**: {{{name}}}
**Type**: {{{type}}}
**Description**: {{{description}}}

# Use template
{{template:component|name=AuthService|type=Microservice|description=Handles authentication}}
```

### 3. **Smart Tables of Contents**
```markdown
# Auto-generated from KB structure
{{toc:gaia/specs/*}}

Renders as:
- API Design
  - Overview
  - Endpoints
  - Authentication
- Database Schema
  - Tables
  - Migrations
```

### 4. **Wiki Graphs**
```mermaid
# Visualize link relationships
graph TD
    A[gaia/overview] --> B[gaia/architecture]
    A --> C[gaia/specs]
    B --> D[gaia/implementation]
    C --> D
```

## Benefits of Wiki Interface

### For Users
- ✅ Familiar navigation (like Wikipedia)
- ✅ Easy linking between documents
- ✅ Visual editing with preview
- ✅ Discover related content
- ✅ See what links where

### For Knowledge Management  
- ✅ Organic growth of connections
- ✅ Find orphaned pages
- ✅ Track popular pages
- ✅ Category organization
- ✅ Automatic cross-references

### Technical Benefits
- ✅ Same backend (PostgreSQL/MongoDB)
- ✅ Progressive enhancement
- ✅ SEO-friendly URLs
- ✅ Cache-friendly
- ✅ Mobile responsive

## Implementation Phases

### Phase 1: Basic Wiki View
- Wiki-style URLs
- Parse [[wiki links]]
- Basic page rendering
- Edit functionality

### Phase 2: Wiki Navigation
- Backlinks
- Categories
- Recent changes
- Search

### Phase 3: Advanced Features
- Templates
- Transclusion
- Visual link graph
- WYSIWYG editor

## The Beauty: Multiple Views, Same Data

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Filesystem  │     │    Wiki     │     │    Chat     │
│    View     │     │   View      │     │    View     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL │
                    │   Storage   │
                    └─────────────┘
```

Users can choose their preferred interface:
- Developers might prefer filesystem
- Writers might prefer wiki
- Casual users might prefer chat

All working with the same knowledge base!