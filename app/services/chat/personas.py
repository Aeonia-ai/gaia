from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging

from app.shared.security import get_current_auth_legacy as get_current_auth
from .persona_service_postgres import PostgresPersonaService as PersonaService
from app.models.persona import (
    Persona, PersonaCreate, PersonaUpdate, PersonaResponse,
    PersonaListResponse, SetPersonaRequest, UserPersonaPreference
)

router = APIRouter()
logger = logging.getLogger(__name__)

def get_persona_service() -> PersonaService:
    """Dependency to get PersonaService instance"""
    return PersonaService()

@router.get("/", response_model=PersonaListResponse)
async def list_personas(
    active_only: bool = Query(True, description="Only return active personas"),
    auth_principal: Dict[str, Any] = Depends(get_current_auth),
    persona_service: PersonaService = Depends(get_persona_service)
):
    """List all available personas"""
    try:
        personas = await persona_service.list_personas(active_only=active_only)
        return PersonaListResponse(
            success=True,
            personas=personas,
            total=len(personas),
            message="Personas retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error listing personas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current", response_model=PersonaResponse)
async def get_current_persona(
    auth_principal: Dict[str, Any] = Depends(get_current_auth),
    persona_service: PersonaService = Depends(get_persona_service)
):
    """Get the current user's active persona"""
    try:
        user_id = auth_principal.get("sub") or auth_principal.get("user_id")
        if not user_id:
            raise ValueError("Could not determine user ID")
        
        # Try to get user's selected persona
        persona = await persona_service.get_user_persona(user_id)
        
        # If no persona selected, get default
        if not persona:
            persona = await persona_service.get_default_persona()
            if not persona:
                raise ValueError("No personas available")
        
        return PersonaResponse(
            success=True,
            persona=persona,
            message="Current persona retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting current persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set", response_model=Dict[str, Any])
async def set_user_persona(
    request: SetPersonaRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth),
    persona_service: PersonaService = Depends(get_persona_service)
):
    """Set the current user's active persona"""
    try:
        user_id = auth_principal.get("sub") or auth_principal.get("user_id")
        if not user_id:
            raise ValueError("Could not determine user ID")
        
        preference = await persona_service.set_user_persona(user_id, request.persona_id)
        
        return {
            "message": "Persona set successfully",
            "user_id": preference.user_id,
            "persona_id": preference.persona_id,
            "updated_at": preference.updated_at
        }
    except ValueError as e:
        logger.error(f"Validation error setting persona: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting user persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: str,
    auth_principal: Dict[str, Any] = Depends(get_current_auth),
    persona_service: PersonaService = Depends(get_persona_service)
):
    """Get a specific persona by ID"""
    try:
        persona = await persona_service.get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        return PersonaResponse(
            success=True,
            persona=persona,
            message="Persona retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persona {persona_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=PersonaResponse)
async def create_persona(
    persona_data: PersonaCreate,
    auth_principal: Dict[str, Any] = Depends(get_current_auth),
    persona_service: PersonaService = Depends(get_persona_service)
):
    """Create a new persona"""
    try:
        user_id = auth_principal.get("sub") or auth_principal.get("user_id")
        persona = await persona_service.create_persona(persona_data, created_by=user_id)

        return PersonaResponse(
            success=True,
            persona=persona,
            message="Persona created successfully"
        )
    except Exception as e:
        logger.error(f"Error creating persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    persona_data: PersonaUpdate,
    auth_principal: Dict[str, Any] = Depends(get_current_auth),
    persona_service: PersonaService = Depends(get_persona_service)
):
    """Update an existing persona"""
    try:
        # Check if persona exists
        existing_persona = await persona_service.get_persona(persona_id)
        if not existing_persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        # Update persona
        updated_persona = await persona_service.update_persona(persona_id, persona_data)
        if not updated_persona:
            raise HTTPException(status_code=404, detail="Persona not found after update")

        return PersonaResponse(
            success=True,
            persona=updated_persona,
            message="Persona updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating persona {persona_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{persona_id}")
async def delete_persona(
    persona_id: str,
    auth_principal: Dict[str, Any] = Depends(get_current_auth),
    persona_service: PersonaService = Depends(get_persona_service)
):
    """Delete a persona (soft delete - sets is_active=False)"""
    try:
        success = await persona_service.delete_persona(persona_id)
        if not success:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        return {"message": "Persona deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting persona {persona_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize-default")
async def initialize_default_persona(
    auth_principal: Dict[str, Any] = Depends(get_current_auth),
    persona_service: PersonaService = Depends(get_persona_service)
):
    """Initialize the default Mu persona if no personas exist"""
    try:
        persona = await persona_service.get_default_persona()
        return PersonaResponse(
            success=True,
            persona=persona,
            message="Default persona initialized successfully"
        )
    except Exception as e:
        logger.error(f"Error initializing default persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))
