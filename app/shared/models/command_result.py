# app/shared/models/command_result.py

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class CommandResult(BaseModel):
    """ 
    Standardized result object for all command handlers.
    Ensures a uniform contract between the ExperienceCommandProcessor and its handlers.
    """
    success: bool = Field(..., description="Indicates if the command was successful.")
    state_changes: Optional[Dict[str, Any]] = Field(None, description="Structured JSON describing state modifications.")
    message_to_player: Optional[str] = Field(None, description="Simple, direct feedback message for the player.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional dictionary for any other structured data for the client.")
