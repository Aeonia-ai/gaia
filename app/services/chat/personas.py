from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Dict, Any, Optional

from app.shared.security import get_current_auth
from .persona_service_postgres import PostgresPersonaService
from app.shared.models.persona import (
    Persona, PersonaCreate, PersonaUpdate, PersonaResponse, 
    PersonaListResponse, SetPersonaRequest, UserPersonaPreference
)
from app.shared.logging import logger

router = APIRouter()

async def get_persona_auth_and_body(request: Request) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Get authentication data and request body from request for persona operations"""
    try:
        body = await request.json()
        auth_data = body.get("_auth")
        if not auth_data:
            raise HTTPException(status_code=401, detail="No authentication data provided")
        return auth_data, body
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")

def get_persona_service() -> PostgresPersonaService:
    """Dependency to get PostgreSQL PersonaService instance"""
    return PostgresPersonaService()

@router.get("/", response_model=PersonaListResponse)
async def list_personas(
    active_only: bool = Query(True, description="Only return active personas"),
    persona_service: PostgresPersonaService = Depends(get_persona_service)
):
    """List all available personas"""
    try:
        personas = await persona_service.list_personas(active_only=active_only)
        return PersonaListResponse(
            personas=personas,
            total=len(personas),
            message="Personas retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error listing personas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current", response_model=PersonaResponse)
async def get_current_persona(
    persona_service: PostgresPersonaService = Depends(get_persona_service)
):
    """Get the default persona (since we don't have user context in GET requests)"""
    try:
        # Get default persona since we can't determine user from GET request
        persona = await persona_service.get_default_persona()
        if not persona:
            raise ValueError("No personas available")
        
        return PersonaResponse(
            persona=persona,
            message="Default persona retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting current persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set", response_model=Dict[str, Any])
async def set_user_persona(
    request: Request,
    persona_service: PostgresPersonaService = Depends(get_persona_service)
):
    """Set the current user's active persona"""
    try:
        auth_data, body = await get_persona_auth_and_body(request)
        
        # Extract persona_id from body
        persona_id = body.get("persona_id")
        if not persona_id:
            raise ValueError("persona_id is required")
        
        user_id = auth_data.get("user_id") or auth_data.get("key")
        if not user_id:
            raise ValueError("Could not determine user ID")
        
        preference = await persona_service.set_user_persona(user_id, persona_id)
        
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
    persona_service: PostgresPersonaService = Depends(get_persona_service)
):
    """Get a specific persona by ID"""
    try:
        persona = await persona_service.get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        return PersonaResponse(
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
    request: Request,
    persona_service: PostgresPersonaService = Depends(get_persona_service)
):
    """Create a new persona"""
    try:
        auth_data, body = await get_persona_auth_and_body(request)
        
        # Create PersonaCreate object from body data
        persona_data = PersonaCreate(**body)
        
        user_id = auth_data.get("user_id") or auth_data.get("key")
        persona = await persona_service.create_persona(persona_data, created_by=user_id)
        
        return PersonaResponse(
            persona=persona,
            message="Persona created successfully"
        )
    except Exception as e:
        logger.error(f"Error creating persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    request: Request,
    persona_service: PostgresPersonaService = Depends(get_persona_service)
):
    """Update an existing persona"""
    try:
        auth_data, body = await get_persona_auth_and_body(request)
        
        # Check if persona exists
        existing_persona = await persona_service.get_persona(persona_id)
        if not existing_persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        # Create PersonaUpdate object from body data
        persona_data = PersonaUpdate(**body)
        
        # Update persona
        updated_persona = await persona_service.update_persona(persona_id, persona_data)
        if not updated_persona:
            raise HTTPException(status_code=404, detail="Persona not found after update")
        
        return PersonaResponse(
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
    persona_service: PostgresPersonaService = Depends(get_persona_service)
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
    persona_service: PostgresPersonaService = Depends(get_persona_service)
):
    """Initialize the default Mu persona if no personas exist"""
    try:
        persona = await persona_service.get_default_persona()
        return PersonaResponse(
            persona=persona,
            message="Default persona initialized successfully"
        )
    except Exception as e:
        logger.error(f"Error initializing default persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))
