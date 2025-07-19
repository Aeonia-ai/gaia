# KB Wiki Interface Design for FastHTML Web UI

## Overview

The KB wiki interface will be integrated into the existing FastHTML web service as a new section alongside the chat interface. Users can seamlessly switch between chat and wiki modes.

## Navigation Integration

### Main Navigation Bar
```python
# In web service templates/base.py
def main_nav():
    return Nav(
        A("💬 Chat", href="/chat", cls="nav-link"),
        A("📚 Wiki", href="/wiki", cls="nav-link"),
        A("⚙️ Settings", href="/settings", cls="nav-link"),
        cls="main-nav"
    )
```

### URL Structure
```
/chat                    # Existing chat interface
/wiki                    # Wiki home page
/wiki/browse             # File browser view
/wiki/browse/gaia        # Directory view
/wiki/page/gaia/specs/api-design    # Wiki page view
/wiki/edit/gaia/specs/api-design    # Edit mode
/wiki/search?q=consciousness         # Search results
/wiki/recent             # Recent changes
/wiki/graph              # Link graph visualization
```

## Page Layouts

### 1. Wiki Home Page (`/wiki`)

```python
@app.get("/wiki")
def wiki_home():
    return Container(
        H1("📚 Knowledge Base"),
        
        # Quick stats
        Div(
            Card("📄", "1,247 Pages", href="/wiki/browse"),
            Card("🔗", "3,892 Links", href="/wiki/graph"),
            Card("✏️", "23 Recent Edits", href="/wiki/recent"),
            cls="stats-grid"
        ),
        
        # Search bar
        Form(
            Input(placeholder="Search knowledge base...", name="q", cls="search-input"),
            Button("🔍", type="submit"),
            action="/wiki/search",
            cls="search-form"
        ),
        
        # Featured sections
        Section(
            H2("📁 Browse by Category"),
            Div(
                A("🏗️ Gaia Architecture", href="/wiki/browse/gaia"),
                A("💭 Consciousness Research", href="/wiki/browse/influences"),
                A("🎮 MMOIRL Design", href="/wiki/browse/mmoirl"),
                A("📊 Project Status", href="/wiki/browse/status"),
                cls="category-grid"
            )
        ),
        
        # Recent activity
        Section(
            H2("📝 Recent Changes"),
            recent_changes_list()
        )
    )
```

### 2. File Browser View (`/wiki/browse`)

```python
@app.get("/wiki/browse/{path:path}")
def wiki_browse(path: str = ""):
    kb_path = path or "/"
    items = kb_service.list_directory(kb_path)
    
    return Container(
        # Breadcrumb navigation
        Nav(
            *breadcrumb_links(kb_path),
            cls="breadcrumb"
        ),
        
        # Toolbar
        Div(
            Button("📄 New Page", onclick=f"createPage('{kb_path}')"),
            Button("📁 New Folder", onclick=f"createFolder('{kb_path}')"),
            Input(placeholder="Filter files...", cls="filter-input"),
            cls="toolbar"
        ),
        
        # File/folder listing
        Div(
            *[file_item(item) for item in items],
            cls="file-list"
        ),
        
        # Side panel with metadata
        Aside(
            directory_info(kb_path),
            related_pages(kb_path),
            cls="side-panel"
        )
    )

def file_item(item):
    icon = "📁" if item.is_dir else "📄"
    return Div(
        A(
            icon, " ", item.name,
            href=f"/wiki/browse/{item.path}" if item.is_dir else f"/wiki/page/{item.path}"
        ),
        Span(item.modified.strftime("%Y-%m-%d"), cls="date"),
        Span(item.size_str, cls="size"),
        cls="file-item"
    )
```

### 3. Wiki Page View (`/wiki/page/{path}`)

```python
@app.get("/wiki/page/{path:path}")
async def wiki_page(path: str):
    doc = await kb_service.read_document(path)
    if not doc:
        return page_not_found(path)
    
    # Render wiki content with link parsing
    rendered_content = await wiki_renderer.render(doc.content)
    backlinks = await kb_service.get_backlinks(path)
    
    return Container(
        # Page header
        Header(
            H1(doc.title or path_to_title(path)),
            Div(
                Button("✏️ Edit", onclick=f"editPage('{path}')"),
                Button("📋 History", onclick=f"showHistory('{path}')"),
                Button("🔗 Links", onclick=f"showBacklinks('{path}')"),
                cls="page-actions"
            ),
            cls="page-header"
        ),
        
        # Main content area
        Main(
            # Wiki content
            Article(
                rendered_content,
                cls="wiki-content"
            ),
            
            # Table of contents (if page is long)
            generate_toc(doc.content) if len(doc.content) > 2000 else None,
            
            cls="main-content"
        ),
        
        # Sidebar
        Aside(
            # Page metadata
            Section(
                H3("📊 Page Info"),
                P(f"Last modified: {doc.modified}"),
                P(f"Author: {doc.author}"),
                P(f"Size: {len(doc.content)} chars"),
                cls="page-info"
            ),
            
            # Backlinks
            Section(
                H3("🔗 Referenced By"),
                Ul(*[
                    Li(A(link.title, href=f"/wiki/page/{link.path}"))
                    for link in backlinks[:10]
                ]) if backlinks else P("No backlinks found"),
                cls="backlinks"
            ),
            
            # Related pages
            Section(
                H3("🎯 Related"),
                related_pages_widget(path),
                cls="related"
            ),
            
            cls="sidebar"
        )
    )
```

### 4. Edit Mode (`/wiki/edit/{path}`)

```python
@app.get("/wiki/edit/{path:path}")
async def wiki_edit_page(path: str):
    doc = await kb_service.read_document(path)
    
    return Container(
        # Edit header
        Header(
            H1(f"✏️ Editing: {path_to_title(path)}"),
            Div(
                Button("💾 Save", onclick="savePage()", cls="btn-primary"),
                Button("👁️ Preview", onclick="togglePreview()"),
                Button("❌ Cancel", onclick=f"location.href='/wiki/page/{path}'"),
                cls="edit-actions"
            )
        ),
        
        # Split view: editor + preview
        Div(
            # Markdown editor
            Div(
                Textarea(
                    doc.content if doc else "",
                    id="editor",
                    placeholder="Enter markdown content...",
                    rows="30",
                    cls="markdown-editor"
                ),
                cls="editor-pane"
            ),
            
            # Live preview pane
            Div(
                id="preview-pane",
                cls="preview-pane hidden"
            ),
            
            cls="split-view"
        ),
        
        # Editor toolbar
        Div(
            # Formatting buttons
            Button("B", onclick="insertMarkdown('**', '**')", title="Bold"),
            Button("I", onclick="insertMarkdown('*', '*')", title="Italic"),
            Button("🔗", onclick="insertLink()", title="Insert Link"),
            Button("📷", onclick="insertImage()", title="Insert Image"),
            Button("📝", onclick="insertWikiLink()", title="Wiki Link"),
            
            # Template shortcuts
            Select(
                Option("Insert Template...", value=""),
                Option("Meeting Notes", value="meeting"),
                Option("Project Spec", value="spec"),
                Option("Architecture Doc", value="arch"),
                onchange="insertTemplate(this.value)"
            ),
            
            cls="editor-toolbar"
        ),
        
        # JavaScript for editor functionality
        Script("""
            function savePage() {
                const content = document.getElementById('editor').value;
                fetch(`/api/kb/save/${path}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({content: content})
                }).then(() => {
                    location.href = `/wiki/page/${path}`;
                });
            }
            
            function togglePreview() {
                const editor = document.querySelector('.editor-pane');
                const preview = document.querySelector('.preview-pane');
                preview.classList.toggle('hidden');
                
                if (!preview.classList.contains('hidden')) {
                    // Update preview
                    const content = document.getElementById('editor').value;
                    fetch('/api/kb/preview', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({content: content})
                    }).then(r => r.text()).then(html => {
                        preview.innerHTML = html;
                    });
                }
            }
            
            function insertWikiLink() {
                const link = prompt('Page to link to:');
                if (link) {
                    insertMarkdown(`[[${link}]]`, '');
                }
            }
        """)
    )
```

### 5. Search Results (`/wiki/search`)

```python
@app.get("/wiki/search")
async def wiki_search(q: str = "", tags: str = "", author: str = ""):
    results = await kb_service.search(
        query=q,
        tags=tags.split(",") if tags else None,
        author=author or None
    )
    
    return Container(
        # Search header
        Header(
            H1(f"🔍 Search Results for '{q}'"),
            P(f"Found {len(results)} results"),
        ),
        
        # Search filters
        Form(
            Input(value=q, name="q", placeholder="Search...", cls="search-input"),
            Input(value=tags, name="tags", placeholder="Tags (comma-separated)"),
            Input(value=author, name="author", placeholder="Author"),
            Button("Search", type="submit"),
            action="/wiki/search",
            cls="search-form"
        ),
        
        # Results
        Div(
            *[search_result_item(result) for result in results],
            cls="search-results"
        ) if results else Div(
            P("No results found. Try:"),
            Ul(
                Li("Checking your spelling"),
                Li("Using different keywords"),
                Li("Browsing by category instead")
            )
        )
    )

def search_result_item(result):
    return Article(
        H3(A(result.title, href=f"/wiki/page/{result.path}")),
        P(result.excerpt, cls="excerpt"),
        Div(
            Span(f"📁 {result.path}", cls="path"),
            Span(f"📅 {result.modified}", cls="date"),
            *[Span(f"#{tag}", cls="tag") for tag in result.tags],
            cls="result-meta"
        ),
        cls="search-result"
    )
```

### 6. Link Graph Visualization (`/wiki/graph`)

```python
@app.get("/wiki/graph")
async def wiki_graph():
    # Get link data for visualization
    links = await kb_service.get_all_links()
    
    return Container(
        Header(
            H1("🕸️ Knowledge Graph"),
            Div(
                Select(
                    Option("All Pages", value="all"),
                    Option("Gaia", value="gaia"),
                    Option("Influences", value="influences"),
                    Option("MMOIRL", value="mmoirl"),
                    id="filter-select"
                ),
                Button("🔍 Focus", onclick="focusGraph()"),
                Button("📸 Export", onclick="exportGraph()"),
                cls="graph-controls"
            )
        ),
        
        # Graph container
        Div(id="knowledge-graph", cls="graph-container"),
        
        # Graph sidebar with details
        Aside(
            Div(id="node-details", cls="node-details"),
            Div(id="graph-stats", cls="graph-stats"),
            cls="graph-sidebar"
        ),
        
        # D3.js or similar for graph visualization
        Script(src="/static/js/knowledge-graph.js"),
        Script(f"""
            renderKnowledgeGraph({json.dumps(links)});
        """)
    )
```

## CSS Styling

```css
/* Wiki-specific styles */
.wiki-content {
    max-width: 800px;
    line-height: 1.6;
    font-size: 16px;
}

.wiki-content h1, .wiki-content h2, .wiki-content h3 {
    margin-top: 2rem;
    margin-bottom: 1rem;
}

/* Wiki links */
.wiki-link {
    color: #0066cc;
    text-decoration: none;
    border-bottom: 1px dotted #0066cc;
}

.wiki-link:hover {
    background-color: #f0f8ff;
}

.wiki-link-missing {
    color: #cc0000;
    border-bottom: 1px dotted #cc0000;
}

/* File browser */
.file-list {
    display: grid;
    gap: 0.5rem;
}

.file-item {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 1rem;
    padding: 0.5rem;
    border-radius: 4px;
    transition: background-color 0.2s;
}

.file-item:hover {
    background-color: #f5f5f5;
}

/* Editor */
.split-view {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    height: 70vh;
}

.markdown-editor {
    width: 100%;
    font-family: 'Fira Code', monospace;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 1rem;
}

.preview-pane {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 1rem;
    overflow-y: auto;
    background-color: #fafafa;
}

/* Graph visualization */
.graph-container {
    width: 100%;
    height: 600px;
    border: 1px solid #ddd;
    border-radius: 4px;
}

.node-details {
    padding: 1rem;
    background-color: #f9f9f9;
    border-radius: 4px;
    margin-bottom: 1rem;
}
```

## JavaScript Enhancements

```javascript
// Real-time features
class WikiUI {
    constructor() {
        this.setupWebSocket();
        this.setupAutoSave();
        this.setupSearch();
    }
    
    setupWebSocket() {
        // Real-time notifications for page edits
        this.ws = new WebSocket('/ws/wiki');
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'page_edited') {
                this.showNotification(`Page ${data.path} was edited by ${data.author}`);
            }
        };
    }
    
    setupAutoSave() {
        // Auto-save drafts every 30 seconds
        setInterval(() => {
            const editor = document.getElementById('editor');
            if (editor && editor.value) {
                this.saveDraft(window.location.pathname, editor.value);
            }
        }, 30000);
    }
    
    setupSearch() {
        // Live search as you type
        const searchInput = document.querySelector('.search-input');
        if (searchInput) {
            searchInput.addEventListener('input', debounce((e) => {
                if (e.target.value.length > 2) {
                    this.liveSearch(e.target.value);
                }
            }, 300));
        }
    }
    
    showNotification(message) {
        // Toast notification
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new WikiUI();
});
```

## Integration with Chat

### Cross-References
```python
# In chat interface, detect KB references
def render_chat_message(message):
    # Parse [[wiki links]] in chat messages
    wiki_links = extract_wiki_links(message.content)
    
    return Div(
        render_markdown_with_wiki_links(message.content),
        
        # Show KB references as cards
        Div(*[
            kb_reference_card(link) for link in wiki_links
        ], cls="kb-references") if wiki_links else None,
        
        cls="chat-message"
    )

def kb_reference_card(path):
    doc = kb_service.get_document_summary(path)
    return Card(
        H4(A(doc.title, href=f"/wiki/page/{path}")),
        P(doc.excerpt),
        Small(f"📁 {path}"),
        cls="kb-reference"
    )
```

### Quick Actions
```python
# Add KB actions to chat interface
def chat_quick_actions():
    return Div(
        Button("📚 Browse KB", onclick="window.open('/wiki', '_blank')"),
        Button("🔍 Search KB", onclick="openKBSearch()"),
        Button("📝 Create Page", onclick="createKBPage()"),
        cls="quick-actions"
    )
```

## Mobile Responsive Design

```css
/* Mobile-first responsive design */
@media (max-width: 768px) {
    .split-view {
        grid-template-columns: 1fr;
    }
    
    .preview-pane {
        height: 300px;
    }
    
    .file-item {
        grid-template-columns: 1fr;
        gap: 0.5rem;
    }
    
    .sidebar {
        order: -1;
        margin-bottom: 2rem;
    }
    
    .graph-container {
        height: 400px;
    }
}
```

This design provides a comprehensive wiki interface that integrates seamlessly with the existing FastHTML web UI, offering both casual browsing and power-user features while maintaining the clean, modern aesthetic of the current interface.