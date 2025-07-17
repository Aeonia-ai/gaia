"""
Persona models for Gaia Platform.
Defines data structures for AI personas and user preferences.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class PersonaBase(BaseModel):
    """Base persona properties"""
    name: str = Field(..., description="Unique name of the persona")
    description: str = Field(..., description="Brief description of the persona")
    system_prompt: str = Field(..., description="System prompt for the persona")
    personality_traits: Dict[str, Any] = Field(default_factory=dict, description="Personality traits as key-value pairs")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Capabilities as key-value pairs")
    is_active: bool = Field(default=True, description="Whether the persona is active")


class PersonaCreate(PersonaBase):
    """Properties required to create a persona"""
    pass


class PersonaUpdate(BaseModel):
    """Properties that can be updated on a persona"""
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    personality_traits: Optional[Dict[str, Any]] = None
    capabilities: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class Persona(PersonaBase):
    """Complete persona model with all fields"""
    id: str = Field(..., description="Unique identifier")
    created_by: Optional[str] = Field(None, description="User ID who created the persona")
    created_at: datetime = Field(..., description="When the persona was created")
    updated_at: datetime = Field(..., description="When the persona was last updated")

    class Config:
        from_attributes = True


class UserPersonaPreference(BaseModel):
    """User's persona selection preference"""
    user_id: str = Field(..., description="User ID")
    persona_id: str = Field(..., description="Selected persona ID")
    updated_at: datetime = Field(..., description="When the preference was last updated")

    class Config:
        from_attributes = True


class PersonaResponse(BaseModel):
    """API response for a single persona"""
    persona: Persona
    message: str = "Persona retrieved successfully"


class PersonaListResponse(BaseModel):
    """API response for a list of personas"""
    personas: list[Persona]
    total: int
    message: str = "Personas retrieved successfully"


class SetPersonaRequest(BaseModel):
    """Request to set user's active persona"""
    persona_id: str = Field(..., description="ID of the persona to set as active")