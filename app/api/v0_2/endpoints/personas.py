"""
Persona management endpoints for user experience personalization
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import logging

from app.shared.security import get_current_auth_legacy as get_current_auth
from app.models.persona import (
    Persona, PersonaCreate, PersonaUpdate, PersonaResponse, PersonaListResponse,
    SetPersonaRequest, SetPersonaResponse, InitializeDefaultResponse
)
from app.services.persona_service import persona_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=PersonaListResponse)
async def list_personas(
    active_only: bool = Query(True, description="Filter to active personas only"),
    auth_data: dict = Depends(get_current_auth)
):
    """
    List all available personas
    """
    try:
        personas = await persona_service.list_personas(active_only=active_only)
        
        return PersonaListResponse(
            success=True,
            personas=personas,
            total=len(personas),
            message=f"Found {len(personas)} personas"
        )
    except Exception as e:
        logger.error(f"Error listing personas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current", response_model=PersonaResponse)
async def get_current_persona(auth_data: dict = Depends(get_current_auth)):
    """
    Get user's current active persona
    """
    try:
        user_id = auth_data.get("user_id")
        if not user_id:
            # If no user_id, return default persona
            persona = await persona_service.get_default_persona()
        else:
            # Try to get user's selected persona
            persona = await persona_service.get_user_persona(user_id)
            if not persona:
                # Fall back to default if user has no preference
                persona = await persona_service.get_default_persona()
        
        return PersonaResponse(
            success=True,
            message="Current persona retrieved successfully",
            persona=persona
        )
    except Exception as e:
        logger.error(f"Error getting current persona: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: str,
    auth_data: dict = Depends(get_current_auth)
):
    """
    Get specific persona by ID
    """
    try:
        persona = await persona_service.get_persona(persona_id)
        
        if not persona:
            raise HTTPException(status_code=404, detail=f"Persona not found: {persona_id}")
        
        return PersonaResponse(
            success=True,
            message="Persona retrieved successfully",
            persona=persona
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persona {persona_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=PersonaResponse)
async def create_persona(
    persona_data: PersonaCreate,
    auth_data: dict = Depends(get_current_auth)
):
    """
    Create new persona
    """
    try:
        created_by = auth_data.get("user_id", "unknown")
        persona = await persona_service.create_persona(persona_data, created_by=created_by)
        
        return PersonaResponse(
            success=True,
            message="Persona created successfully",
            persona=persona
        )
    except Exception as e:
        logger.error(f"Error creating persona: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    persona_data: PersonaUpdate,
    auth_data: dict = Depends(get_current_auth)
):
    """
    Update existing persona
    """
    try:
        updated_by = auth_data.get("user_id", "unknown")
        persona = await persona_service.update_persona(persona_id, persona_data, updated_by=updated_by)
        
        if not persona:
            raise HTTPException(status_code=404, detail=f"Persona not found: {persona_id}")
        
        return PersonaResponse(
            success=True,
            message="Persona updated successfully",
            persona=persona
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating persona {persona_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{persona_id}")
async def delete_persona(
    persona_id: str,
    auth_data: dict = Depends(get_current_auth)
):
    """
    Soft delete persona (sets is_active=false)
    """
    try:
        success = await persona_service.delete_persona(persona_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Persona not found: {persona_id}")
        
        return {
            "success": True,
            "message": "Persona deleted successfully",
            "persona_id": persona_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting persona {persona_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set", response_model=SetPersonaResponse)
async def set_user_persona(
    request: SetPersonaRequest,
    auth_data: dict = Depends(get_current_auth)
):
    """
    Set user's active persona
    """
    try:
        user_id = auth_data.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID required")
        
        # Verify persona exists
        persona = await persona_service.get_persona(request.persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail=f"Persona not found: {request.persona_id}")
        
        # Set user preference
        success = await persona_service.set_user_persona(user_id, request.persona_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set persona preference")
        
        return SetPersonaResponse(
            success=True,
            message=f"Active persona set to {persona.name}",
            persona_id=request.persona_id,
            persona_name=persona.name
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting user persona: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize-default", response_model=InitializeDefaultResponse)
async def initialize_default_persona(auth_data: dict = Depends(get_current_auth)):
    """
    Initialize default "Mu" persona if it doesn't exist
    """
    try:
        persona, was_created = await persona_service.initialize_default_persona()
        
        message = "Default persona created successfully" if was_created else "Default persona already exists"
        
        return InitializeDefaultResponse(
            success=True,
            message=message,
            persona=persona,
            was_created=was_created
        )
    except Exception as e:
        logger.error(f"Error initializing default persona: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))