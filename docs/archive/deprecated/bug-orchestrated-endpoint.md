# BUG: Orchestrated Endpoint Format Mismatch

## Issue
The `/api/v1/chat/orchestrated` endpoint has a format mismatch between the API contract and service implementation.

## Details
- **API Contract**: Expects `ChatRequest` with `message: str` field
- **Service Implementation**: Looks for `messages: List[Dict]` array
- **Result**: 400 error "No messages provided" when using the correct API format

## Current Behavior
```python
# In orchestrated_chat.py
messages = request.get("messages", [])  # Looking for array
if not messages:
    raise HTTPException(status_code=400, detail="No messages provided")
```

## Expected Behavior
The service should accept the standard `message` field like all other chat endpoints:
```python
# Should work with:
{"message": "What is 2+2?"}
```

## Fix Required
The orchestrated service needs to be updated to:
1. Accept the standard `message` field
2. Convert it internally to messages array if needed
3. Maintain consistency with other endpoints

## Example Fix
```python
# Extract message correctly
message = request.get("message")
if not message:
    raise HTTPException(status_code=400, detail="No message provided")

# Convert to messages array internally if needed
messages = [{"role": "user", "content": message}]
```

## Impact
- All chat endpoints should have consistent interface
- Current implementation breaks API contract
- Confuses API consumers