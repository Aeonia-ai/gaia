# Missing Gateway Endpoints

## Issue
Several useful endpoints exist in the chat service but are not exposed through the gateway.

## Missing Endpoints

### 1. Conversations Management
- **Path in Chat Service**: `/chat/conversations`
- **Method**: GET
- **Purpose**: List all conversations for a user
- **Why Needed**: Essential for conversation history management

### 2. Conversations Search  
- **Path in Chat Service**: `/chat/conversations/search`
- **Method**: GET
- **Query Params**: `query` (search term)
- **Purpose**: Search through conversation history
- **Why Needed**: Users need to find past conversations

### 3. Orchestration Metrics
- **Path in Chat Service**: `/chat/orchestrated/metrics`
- **Method**: GET  
- **Purpose**: Performance metrics for orchestrated chat
- **Why Needed**: Monitoring and optimization

## Gateway Routes to Add

```python
# In gateway/main.py

@app.get("/api/v1/chat/conversations", tags=["Chat"])
async def v1_get_conversations(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """List all conversations for the authenticated user"""
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/conversations",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )

@app.get("/api/v1/chat/conversations/search", tags=["Chat"])
async def v1_search_conversations(
    request: Request,
    query: str,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Search conversations"""
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/conversations/search",
        method="GET",
        headers=dict(request.headers),
        params={"query": query}
    )

@app.get("/api/v1/chat/orchestrated/metrics", tags=["Chat"])
async def v1_get_orchestrated_metrics(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get orchestration performance metrics"""
    return await forward_request_to_service(
        service_name="chat",
        path="/chat/orchestrated/metrics",
        method="GET",
        headers=dict(request.headers)
    )
```

## Benefits of Adding These
1. **Complete API Surface**: All chat features accessible through gateway
2. **Proper Authentication**: Gateway handles auth consistently
3. **API Documentation**: Endpoints appear in OpenAPI/Swagger docs
4. **Security**: No direct service access needed
5. **Monitoring**: All requests go through central gateway