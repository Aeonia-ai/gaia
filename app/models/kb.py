"""
KB Request Models

Models for Knowledge Base API requests.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class WriteRequest(BaseModel):
    """Request model for writing/updating KB files"""
    path: str = Field(..., description="Relative path within KB")
    content: str = Field(..., description="File content to write")
    message: str = Field(..., description="Git commit message")
    validate_content: bool = Field(True, description="Whether to validate content before writing")


class DeleteRequest(BaseModel):
    """Request model for deleting KB files"""
    path: str = Field(..., description="Relative path within KB to delete")
    message: str = Field(..., description="Git commit message")


class MoveRequest(BaseModel):
    """Request model for moving/renaming KB files"""
    old_path: str = Field(..., description="Current path of the file")
    new_path: str = Field(..., description="New path for the file")
    message: str = Field(..., description="Git commit message")


class ShareRequest(BaseModel):
    """Request model for sharing KB artifacts (future feature)"""
    path: str = Field(..., description="Path to share")
    recipients: Optional[List[str]] = Field(None, description="User IDs to share with")
    workspace_id: Optional[str] = Field(None, description="Workspace to share to")
    permissions: List[str] = Field(["read"], description="Permissions to grant")
    message: Optional[str] = Field(None, description="Optional share message")
    expires_in_days: Optional[int] = Field(None, description="Optional expiration")