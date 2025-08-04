"""
Format adapters for migrating between OpenAI and v0.3 response formats.
Allows the web UI to work with both formats during migration.
"""

from typing import Dict, Any, Optional


def detect_response_format(response: dict) -> str:
    """Detect if response is OpenAI or v0.3 format."""
    if isinstance(response, dict):
        if "choices" in response and "model" in response:
            return "openai"
        elif "response" in response:
            return "v0.3"
    return "unknown"


def extract_content(response: dict) -> str:
    """Extract content regardless of format."""
    format_type = detect_response_format(response)
    
    if format_type == "openai":
        choices = response.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
    elif format_type == "v0.3":
        return response.get("response", "")
    
    return ""


def extract_conversation_id(response: dict) -> Optional[str]:
    """Extract conversation_id if present in response."""
    # Check _metadata field (both formats might have it)
    if "_metadata" in response:
        return response["_metadata"].get("conversation_id")
        
    return None


def extract_metadata(response: dict) -> dict:
    """Extract all metadata from response."""
    return response.get("_metadata", {})


def adapt_streaming_chunk(chunk: dict, target_format: str = "v0.3") -> dict:
    """Adapt streaming chunks between formats."""
    if target_format == "v0.3":
        # Convert OpenAI to v0.3
        if chunk.get("object") == "chat.completion.chunk":
            choices = chunk.get("choices", [])
            if choices and "delta" in choices[0]:
                content = choices[0]["delta"].get("content", "")
                if content:
                    return {"type": "content", "content": content}
                
                # Check for finish reason
                finish_reason = choices[0].get("finish_reason")
                if finish_reason == "stop":
                    return {"type": "done"}
                    
        # Pass through if already v0.3 format
        if chunk.get("type") in ["content", "done", "error"]:
            return chunk
            
    elif target_format == "openai":
        # Convert v0.3 to OpenAI (for compatibility)
        if chunk.get("type") == "content":
            return {
                "object": "chat.completion.chunk",
                "choices": [{
                    "delta": {"content": chunk.get("content", "")},
                    "index": 0
                }]
            }
        elif chunk.get("type") == "done":
            return {
                "object": "chat.completion.chunk",
                "choices": [{
                    "delta": {},
                    "index": 0,
                    "finish_reason": "stop"
                }]
            }
    
    return chunk


def parse_sse_chunk(line: str) -> Optional[dict]:
    """Parse Server-Sent Event line to extract JSON data."""
    if line.startswith("data: "):
        data_str = line[6:].strip()
        
        if data_str == "[DONE]":
            return {"type": "done"}
            
        try:
            import json
            return json.loads(data_str)
        except json.JSONDecodeError:
            return None
    
    return None


def create_unified_response(content: str, conversation_id: Optional[str] = None, 
                          format_type: str = "v0.3", **kwargs) -> dict:
    """Create a response in the specified format."""
    if format_type == "v0.3":
        response = {"response": content}
        if conversation_id or kwargs:
            response["_metadata"] = {}
            if conversation_id:
                response["_metadata"]["conversation_id"] = conversation_id
            response["_metadata"].update(kwargs)
        return response
        
    elif format_type == "openai":
        response = {
            "id": f"chatcmpl-{kwargs.get('request_id', 'unknown')}",
            "object": "chat.completion",
            "created": kwargs.get('created', 0),
            "model": kwargs.get('model', 'unknown'),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }]
        }
        
        # Add metadata if provided
        if conversation_id or kwargs.get('route_type'):
            response["_metadata"] = {}
            if conversation_id:
                response["_metadata"]["conversation_id"] = conversation_id
            for key in ['route_type', 'routing_time_ms', 'total_time_ms']:
                if key in kwargs:
                    response["_metadata"][key] = kwargs[key]
                    
        return response
    
    else:
        raise ValueError(f"Unknown format type: {format_type}")