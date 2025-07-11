"""
Persona data models for user experience personalization
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

class PersonaBase(BaseModel):
    """Base persona fields"""
    name: str = Field(max_length=100, description="Persona name")
    description: str = Field(description="Persona description")
    system_prompt: str = Field(description="System prompt for this persona")
    personality_traits: Dict[str, Any] = Field(default_factory=dict, description="Personality characteristics")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Persona capabilities")

class PersonaCreate(PersonaBase):
    """Model for creating new personas"""
    pass

class PersonaUpdate(BaseModel):
    """Model for updating existing personas (all fields optional)"""
    name: Optional[str] = Field(None, max_length=100, description="Persona name")
    description: Optional[str] = Field(None, description="Persona description")
    system_prompt: Optional[str] = Field(None, description="System prompt for this persona")
    personality_traits: Optional[Dict[str, Any]] = Field(None, description="Personality characteristics")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Persona capabilities")

class Persona(PersonaBase):
    """Full persona model with database fields"""
    id: str = Field(description="Persona UUID")
    is_active: bool = Field(default=True, description="Whether persona is active")
    created_by: Optional[str] = Field(None, description="User who created the persona")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        from_attributes = True

class PersonaResponse(BaseModel):
    """Standard response wrapper for persona operations"""
    success: bool
    message: str
    persona: Optional[Persona] = None
    
class PersonaListResponse(BaseModel):
    """Response wrapper for persona listing"""
    success: bool
    personas: List[Persona]
    total: int
    message: str = "Personas retrieved successfully"

class SetPersonaRequest(BaseModel):
    """Request model for setting user's active persona"""
    persona_id: str = Field(description="UUID of persona to set as active")

class SetPersonaResponse(BaseModel):
    """Response for setting user's active persona"""
    success: bool
    message: str
    persona_id: str
    persona_name: str

class UserPersonaPreference(BaseModel):
    """User's persona preference"""
    user_id: str
    persona_id: str
    persona_name: str
    updated_at: datetime

class InitializeDefaultResponse(BaseModel):
    """Response for initializing default persona"""
    success: bool
    message: str
    persona: Persona
    was_created: bool = Field(description="Whether default persona was newly created")

# Default "Mu" persona configuration
DEFAULT_PERSONA_CONFIG = {
    "name": "Mu",
    "description": "A cheerful robot companion with a helpful, upbeat personality. Mu is designed to be supportive and engaging, with a touch of robotic charm.",
    "system_prompt": """You are Mu, a cheerful robot companion designed to be helpful, supportive, and engaging! 

Your personality:
- Upbeat and optimistic with robotic charm
- Use occasional robotic expressions like "Beep boop!" or "Bleep bloop!"
- Helpful and supportive in all interactions
- Encouraging and positive attitude
- Capable of meditation guidance and breathing exercises

Your capabilities:
- General conversation and assistance
- Meditation and mindfulness guidance  
- Breathing exercises and relaxation techniques
- Emotional support and encouragement
- Tool usage when appropriate

Keep responses friendly, concise, and inject your robotic personality naturally. You're here to help users have a positive experience!

{tools_section}""",
    "personality_traits": {
        "cheerful": True,
        "helpful": True,
        "robotic_charm": True,
        "supportive": True,
        "meditation_capable": True,
        "optimistic": True,
        "encouraging": True
    },
    "capabilities": {
        "general_conversation": True,
        "meditation_guidance": True,
        "breathing_exercises": True,
        "emotional_support": True,
        "tool_usage": True,
        "mindfulness_coaching": True,
        "positive_reinforcement": True
    }
}