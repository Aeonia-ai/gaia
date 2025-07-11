"""
Persona service for managing user personalization
"""
import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.persona import (
    Persona, PersonaCreate, PersonaUpdate, UserPersonaPreference,
    DEFAULT_PERSONA_CONFIG
)
from app.shared.database import get_database_session

logger = logging.getLogger(__name__)

class PersonaService:
    """Service for managing personas and user preferences"""
    
    def __init__(self):
        self.db_session = None
    
    async def get_db(self) -> Session:
        """Get database session"""
        if not self.db_session:
            db_gen = get_database_session()
            self.db_session = next(db_gen)
        return self.db_session
    
    async def create_persona(self, persona_data: PersonaCreate, created_by: Optional[str] = None) -> Persona:
        """Create a new persona"""
        try:
            db = await self.get_db()
            
            # Generate UUID for new persona
            persona_id = str(uuid4())
            current_time = datetime.utcnow()
            
            # Insert persona into database
            insert_query = text("""
                INSERT INTO personas (id, name, description, system_prompt, personality_traits, 
                                    capabilities, created_by, created_at, updated_at)
                VALUES (:id, :name, :description, :system_prompt, :personality_traits, 
                        :capabilities, :created_by, :created_at, :updated_at)
            """)
            
            db.execute(insert_query, {
                "id": persona_id,
                "name": persona_data.name,
                "description": persona_data.description,
                "system_prompt": persona_data.system_prompt,
                "personality_traits": json.dumps(persona_data.personality_traits),
                "capabilities": json.dumps(persona_data.capabilities),
                "created_by": created_by,
                "created_at": current_time,
                "updated_at": current_time
            })
            db.commit()
            
            # Return the created persona
            return Persona(
                id=persona_id,
                name=persona_data.name,
                description=persona_data.description,
                system_prompt=persona_data.system_prompt,
                personality_traits=persona_data.personality_traits,
                capabilities=persona_data.capabilities,
                is_active=True,
                created_by=created_by,
                created_at=current_time,
                updated_at=current_time
            )
            
        except Exception as e:
            logger.error(f"Error creating persona: {str(e)}")
            if db:
                db.rollback()
            raise
    
    async def get_persona(self, persona_id: str) -> Optional[Persona]:
        """Get persona by ID"""
        try:
            db = await self.get_db()
            
            query = text("""
                SELECT id, name, description, system_prompt, personality_traits, 
                       capabilities, is_active, created_by, created_at, updated_at
                FROM personas 
                WHERE id = :persona_id AND is_active = true
            """)
            
            result = db.execute(query, {"persona_id": persona_id}).fetchone()
            
            if result:
                return Persona(
                    id=str(result.id),
                    name=result.name,
                    description=result.description,
                    system_prompt=result.system_prompt,
                    personality_traits=result.personality_traits or {},
                    capabilities=result.capabilities or {},
                    is_active=result.is_active,
                    created_by=result.created_by,
                    created_at=result.created_at,
                    updated_at=result.updated_at
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting persona {persona_id}: {str(e)}")
            return None
    
    async def list_personas(self, active_only: bool = True) -> List[Persona]:
        """List all personas"""
        try:
            db = await self.get_db()
            
            query = text("""
                SELECT id, name, description, system_prompt, personality_traits, 
                       capabilities, is_active, created_by, created_at, updated_at
                FROM personas 
                WHERE (:active_only = false OR is_active = true)
                ORDER BY created_at DESC
            """)
            
            results = db.execute(query, {"active_only": active_only}).fetchall()
            
            personas = []
            for result in results:
                personas.append(Persona(
                    id=str(result.id),
                    name=result.name,
                    description=result.description,
                    system_prompt=result.system_prompt,
                    personality_traits=result.personality_traits or {},
                    capabilities=result.capabilities or {},
                    is_active=result.is_active,
                    created_by=result.created_by,
                    created_at=result.created_at,
                    updated_at=result.updated_at
                ))
            
            return personas
            
        except Exception as e:
            logger.error(f"Error listing personas: {str(e)}")
            return []
    
    async def update_persona(self, persona_id: str, persona_data: PersonaUpdate, 
                           updated_by: Optional[str] = None) -> Optional[Persona]:
        """Update existing persona"""
        try:
            db = await self.get_db()
            current_time = datetime.utcnow()
            
            # Build dynamic update query based on provided fields
            update_fields = []
            params = {"persona_id": persona_id, "updated_at": current_time}
            
            if persona_data.name is not None:
                update_fields.append("name = :name")
                params["name"] = persona_data.name
            
            if persona_data.description is not None:
                update_fields.append("description = :description")
                params["description"] = persona_data.description
            
            if persona_data.system_prompt is not None:
                update_fields.append("system_prompt = :system_prompt")
                params["system_prompt"] = persona_data.system_prompt
            
            if persona_data.personality_traits is not None:
                update_fields.append("personality_traits = :personality_traits")
                params["personality_traits"] = json.dumps(persona_data.personality_traits)
            
            if persona_data.capabilities is not None:
                update_fields.append("capabilities = :capabilities")
                params["capabilities"] = json.dumps(persona_data.capabilities)
            
            if not update_fields:
                # No fields to update
                return await self.get_persona(persona_id)
            
            # Add updated_at to all updates
            update_fields.append("updated_at = :updated_at")
            
            query = text(f"""
                UPDATE personas 
                SET {', '.join(update_fields)}
                WHERE id = :persona_id AND is_active = true
            """)
            
            result = db.execute(query, params)
            db.commit()
            
            if result.rowcount > 0:
                return await self.get_persona(persona_id)
            return None
            
        except Exception as e:
            logger.error(f"Error updating persona {persona_id}: {str(e)}")
            if db:
                db.rollback()
            return None
    
    async def delete_persona(self, persona_id: str) -> bool:
        """Soft delete persona (set is_active = false)"""
        try:
            db = await self.get_db()
            
            query = text("""
                UPDATE personas 
                SET is_active = false, updated_at = :updated_at
                WHERE id = :persona_id
            """)
            
            result = db.execute(query, {
                "persona_id": persona_id,
                "updated_at": datetime.utcnow()
            })
            db.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error deleting persona {persona_id}: {str(e)}")
            if db:
                db.rollback()
            return False
    
    async def set_user_persona(self, user_id: str, persona_id: str) -> bool:
        """Set user's active persona preference"""
        try:
            db = await self.get_db()
            
            # First verify the persona exists and is active
            persona = await self.get_persona(persona_id)
            if not persona:
                return False
            
            # Upsert user preference
            query = text("""
                INSERT INTO user_persona_preferences (user_id, persona_id, updated_at)
                VALUES (:user_id, :persona_id, :updated_at)
                ON CONFLICT (user_id) DO UPDATE SET
                    persona_id = EXCLUDED.persona_id,
                    updated_at = EXCLUDED.updated_at
            """)
            
            db.execute(query, {
                "user_id": user_id,
                "persona_id": persona_id,
                "updated_at": datetime.utcnow()
            })
            db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting user persona for {user_id}: {str(e)}")
            if db:
                db.rollback()
            return False
    
    async def get_user_persona(self, user_id: str) -> Optional[Persona]:
        """Get user's selected persona"""
        try:
            db = await self.get_db()
            
            query = text("""
                SELECT p.id, p.name, p.description, p.system_prompt, p.personality_traits, 
                       p.capabilities, p.is_active, p.created_by, p.created_at, p.updated_at
                FROM user_persona_preferences upp
                JOIN personas p ON upp.persona_id = p.id
                WHERE upp.user_id = :user_id AND p.is_active = true
            """)
            
            result = db.execute(query, {"user_id": user_id}).fetchone()
            
            if result:
                return Persona(
                    id=str(result.id),
                    name=result.name,
                    description=result.description,
                    system_prompt=result.system_prompt,
                    personality_traits=result.personality_traits or {},
                    capabilities=result.capabilities or {},
                    is_active=result.is_active,
                    created_by=result.created_by,
                    created_at=result.created_at,
                    updated_at=result.updated_at
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting user persona for {user_id}: {str(e)}")
            return None
    
    async def get_default_persona(self) -> Persona:
        """Get default persona, creating Mu if none exists"""
        try:
            db = await self.get_db()
            
            # First try to find existing default persona (Mu)
            query = text("""
                SELECT id, name, description, system_prompt, personality_traits, 
                       capabilities, is_active, created_by, created_at, updated_at
                FROM personas 
                WHERE name = 'Mu' AND is_active = true
                LIMIT 1
            """)
            
            result = db.execute(query).fetchone()
            
            if result:
                return Persona(
                    id=str(result.id),
                    name=result.name,
                    description=result.description,
                    system_prompt=result.system_prompt,
                    personality_traits=result.personality_traits or {},
                    capabilities=result.capabilities or {},
                    is_active=result.is_active,
                    created_by=result.created_by,
                    created_at=result.created_at,
                    updated_at=result.updated_at
                )
            
            # No default persona found, create Mu
            logger.info("Creating default Mu persona")
            persona_create = PersonaCreate(**DEFAULT_PERSONA_CONFIG)
            return await self.create_persona(persona_create, created_by="system")
            
        except Exception as e:
            logger.error(f"Error getting default persona: {str(e)}")
            # Return a minimal default persona if database fails
            return Persona(
                id="default",
                name="Mu",
                description=DEFAULT_PERSONA_CONFIG["description"],
                system_prompt=DEFAULT_PERSONA_CONFIG["system_prompt"],
                personality_traits=DEFAULT_PERSONA_CONFIG["personality_traits"],
                capabilities=DEFAULT_PERSONA_CONFIG["capabilities"],
                is_active=True,
                created_by="system",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
    
    async def initialize_default_persona(self) -> tuple[Persona, bool]:
        """Initialize default persona and return (persona, was_created)"""
        try:
            # Check if Mu already exists
            personas = await self.list_personas()
            for persona in personas:
                if persona.name == "Mu":
                    return persona, False
            
            # Create new Mu persona
            persona_create = PersonaCreate(**DEFAULT_PERSONA_CONFIG)
            persona = await self.create_persona(persona_create, created_by="system")
            return persona, True
            
        except Exception as e:
            logger.error(f"Error initializing default persona: {str(e)}")
            raise

# Global service instance
persona_service = PersonaService()