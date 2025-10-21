# FastMCP MCP Client Configuration

## Quick Start: Add to Claude Code

FastMCP endpoints use the JSON-RPC protocol over HTTP, not REST endpoints. Configure Claude Code to communicate with the MCP server:

### Method 1: Manual Configuration

Edit your Claude Code config file (`~/.claude/mcp_settings.json` or via Claude Desktop):

```json
{
  "mcpServers": {
    "gaia-kb-docs": {
      "command": "node",
      "args": [
        "-e",
        "require('http').request({host:'localhost',port:8005,path:'/mcp',method:'POST',headers:{'Content-Type':'application/json'}}, res => { let data=''; res.on('data', chunk => data+=chunk); res.on('end', () => console.log(data)); }).end(process.argv[1])"
      ]
    }
  }
}
```

### Method 2: Using MCP HTTP Client (Recommended)

If you have an MCP HTTP client library:

```bash
# Install MCP client (example - adjust based on your setup)
npm install -g @modelcontextprotocol/client

# Add server configuration
mcp add gaia-kb-docs http://localhost:8005/mcp
```

## Verification

The MCP endpoint is working when you see JSON-RPC protocol responses:

```bash
# This response means the server is working:
$ curl http://localhost:8005/mcp/
{"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Bad Request: Missing session ID"}}

# NOT working would be:
- Timeout
- Connection refused  
- 500 Internal Server Error
```

## Testing Without REST Endpoints

FastMCP **does not expose** `/health`, `/tools`, or other REST endpoints. The entire API is JSON-RPC over the root path (`/mcp/`).

To test tools, you need an MCP-compliant client that:
1. Initiates a session handshake
2. Discovers available tools via JSON-RPC
3. Calls tools using JSON-RPC method invocation

## Available Tools

Once connected via MCP client, you'll have access to:

1. **search_kb** - Fast ripgrep-based full-text search
2. **read_file** - Read KB files with frontmatter parsing
3. **load_context** - Load KOS contexts with dependencies
4. **list_directory** - List files in KB directories
5. **navigate_index** - Navigate hierarchical index system
6. **synthesize_contexts** - Cross-domain insight generation
7. **delegate_tasks** - Parallel multi-task execution
8. **get_active_threads** - Get active KOS work threads

## Example MCP Session

```
Client → Server: Initialize session
Server → Client: Session ID + capabilities

Client → Server: List tools
Server → Client: 8 tools with schemas

Client → Server: Call search_kb(query="waypoint")
Server → Client: Search results
```

## Troubleshooting

### "Missing session ID" Error
**This is normal!** It means the server is responding correctly. MCP clients handle session initialization automatically.

### Timeouts or Connection Refused
- Check service: `docker compose ps kb-docs`
- Check logs: `docker logs gaia-kb-docs-1 --tail 50`
- Verify port: `curl http://localhost:8005/health` (this endpoint exists)

### "Not Acceptable: Client must accept text/event-stream"
- Using SSE transport instead of streamable-http
- Current config uses streamable-http (correct)

## Production Configuration

For remote deployments:

```json
{
  "mcpServers": {
    "gaia-kb-docs": {
      "url": "https://gaia-kb-docs-dev.fly.dev/mcp",
      "headers": {
        "X-API-Key": "${GAIA_API_KEY}"
      }
    }
  }
}
```

## References

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol Spec](https://modelcontextprotocol.io/docs)
- [KB FastMCP Integration Status](./kb-fastmcp-integration-status.md)
