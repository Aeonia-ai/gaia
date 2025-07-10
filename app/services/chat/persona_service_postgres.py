from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.shared.database import get_db
from app.shared.models.persona import Persona, PersonaCreate, PersonaUpdate, UserPersonaPreference
from app.shared.logging import logger

class PostgresPersonaService:
    """Service for managing personas in PostgreSQL database"""
    
    def __init__(self):
        pass
    
    def _get_db(self) -> Session:
        """Get database session"""
        return next(get_db())
    
    async def create_persona(self, persona_data: PersonaCreate, created_by: str = None) -> Persona:
        """Create a new persona"""
        try:
            db = self._get_db()
            
            # Insert persona into database
            result = db.execute(
                text("""
                    INSERT INTO personas (name, description, system_prompt, personality_traits, capabilities, is_active, created_by)
                    VALUES (:name, :description, :system_prompt, :personality_traits, :capabilities, :is_active, :created_by)
                    RETURNING id, name, description, system_prompt, personality_traits, capabilities, is_active, created_by, created_at, updated_at
                """),
                {
                    "name": persona_data.name,
                    "description": persona_data.description,
                    "system_prompt": persona_data.system_prompt,
                    "personality_traits": persona_data.personality_traits,
                    "capabilities": persona_data.capabilities,
                    "is_active": persona_data.is_active,
                    "created_by": created_by
                }
            )
            
            row = result.fetchone()
            db.commit()
            db.close()
            
            if row:
                return Persona(
                    id=str(row.id),
                    name=row.name,
                    description=row.description,
                    system_prompt=row.system_prompt,
                    personality_traits=row.personality_traits or {},
                    capabilities=row.capabilities or {},
                    is_active=row.is_active,
                    created_by=str(row.created_by) if row.created_by else None,
                    created_at=row.created_at,
                    updated_at=row.updated_at
                )
            else:
                raise ValueError("Failed to create persona - no data returned")
                
        except Exception as e:
            logger.error(f"Database error creating persona: {e}")
            raise ValueError(f"Failed to create persona: {e}")
    
    async def get_persona(self, persona_id: str) -> Optional[Persona]:
        """Get a persona by ID"""
        try:
            db = self._get_db()
            
            result = db.execute(
                text("""
                    SELECT id, name, description, system_prompt, personality_traits, capabilities, is_active, created_by, created_at, updated_at
                    FROM personas 
                    WHERE id = :persona_id
                """),
                {"persona_id": persona_id}
            )
            
            row = result.fetchone()
            db.close()
            
            if row:
                return Persona(
                    id=str(row.id),
                    name=row.name,
                    description=row.description,
                    system_prompt=row.system_prompt,
                    personality_traits=row.personality_traits or {},
                    capabilities=row.capabilities or {},
                    is_active=row.is_active,
                    created_by=str(row.created_by) if row.created_by else None,
                    created_at=row.created_at,
                    updated_at=row.updated_at
                )
            return None
            
        except Exception as e:
            logger.error(f"Database error getting persona {persona_id}: {e}")
            raise ValueError(f"Failed to get persona: {e}")
    
    async def list_personas(self, active_only: bool = True, created_by: str = None) -> List[Persona]:
        """List all personas, optionally filtered"""
        try:
            db = self._get_db()
            
            query = """
                SELECT id, name, description, system_prompt, personality_traits, capabilities, is_active, created_by, created_at, updated_at
                FROM personas 
                WHERE 1=1
            """
            params = {}
            
            if active_only:
                query += " AND is_active = :is_active"
                params["is_active"] = True
            
            if created_by:
                query += " AND created_by = :created_by"
                params["created_by"] = created_by
            
            query += " ORDER BY created_at DESC"
            
            result = db.execute(text(query), params)
            rows = result.fetchall()
            db.close()
            
            personas = []
            for row in rows:
                personas.append(Persona(
                    id=str(row.id),
                    name=row.name,
                    description=row.description,
                    system_prompt=row.system_prompt,
                    personality_traits=row.personality_traits or {},
                    capabilities=row.capabilities or {},
                    is_active=row.is_active,
                    created_by=str(row.created_by) if row.created_by else None,
                    created_at=row.created_at,
                    updated_at=row.updated_at
                ))
            
            return personas
            
        except Exception as e:
            logger.error(f"Database error listing personas: {e}")
            raise ValueError(f"Failed to list personas: {e}")
    
    async def update_persona(self, persona_id: str, persona_data: PersonaUpdate) -> Optional[Persona]:
        """Update an existing persona"""
        try:
            db = self._get_db()
            
            # Build update query dynamically
            update_fields = []
            params = {"persona_id": persona_id}
            
            for field, value in persona_data.model_dump(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = :{field}")
                    params[field] = value
            
            if not update_fields:
                # No fields to update
                db.close()
                return await self.get_persona(persona_id)
            
            query = f"""
                UPDATE personas 
                SET {', '.join(update_fields)}, updated_at = NOW()
                WHERE id = :persona_id
                RETURNING id, name, description, system_prompt, personality_traits, capabilities, is_active, created_by, created_at, updated_at
            """
            
            result = db.execute(text(query), params)
            row = result.fetchone()
            db.commit()
            db.close()
            
            if row:
                return Persona(
                    id=str(row.id),
                    name=row.name,
                    description=row.description,
                    system_prompt=row.system_prompt,
                    personality_traits=row.personality_traits or {},
                    capabilities=row.capabilities or {},
                    is_active=row.is_active,
                    created_by=str(row.created_by) if row.created_by else None,
                    created_at=row.created_at,
                    updated_at=row.updated_at
                )
            return None
            
        except Exception as e:
            logger.error(f"Database error updating persona {persona_id}: {e}")
            raise ValueError(f"Failed to update persona: {e}")
    
    async def delete_persona(self, persona_id: str) -> bool:
        """Delete a persona (soft delete by setting is_active=False)"""
        try:
            db = self._get_db()
            
            result = db.execute(
                text("""
                    UPDATE personas 
                    SET is_active = false, updated_at = NOW()
                    WHERE id = :persona_id
                """),
                {"persona_id": persona_id}
            )
            
            db.commit()
            db.close()
            
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Database error deleting persona {persona_id}: {e}")
            raise ValueError(f"Failed to delete persona: {e}")
    
    async def set_user_persona(self, user_id: str, persona_id: str) -> UserPersonaPreference:
        """Set a user's active persona preference"""
        try:
            db = self._get_db()
            
            # First verify the persona exists and is active
            persona = await self.get_persona(persona_id)
            if not persona:
                raise ValueError(f"Persona {persona_id} not found")
            if not persona.is_active:
                raise ValueError(f"Persona {persona_id} is not active")
            
            # Upsert user preference
            result = db.execute(
                text("""
                    INSERT INTO user_persona_preferences (user_id, persona_id, updated_at)
                    VALUES (:user_id, :persona_id, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        persona_id = EXCLUDED.persona_id,
                        updated_at = NOW()
                    RETURNING user_id, persona_id, updated_at
                """),
                {
                    "user_id": user_id,
                    "persona_id": persona_id
                }
            )
            
            row = result.fetchone()
            db.commit()
            db.close()
            
            if row:
                return UserPersonaPreference(
                    user_id=str(row.user_id),
                    persona_id=str(row.persona_id),
                    updated_at=row.updated_at
                )
            else:
                raise ValueError("Failed to set user persona preference")
                
        except Exception as e:
            logger.error(f"Database error setting user persona: {e}")
            raise ValueError(f"Failed to set user persona: {e}")
    
    async def get_user_persona(self, user_id: str) -> Optional[Persona]:
        """Get a user's currently selected persona"""
        try:
            db = self._get_db()
            
            # Get user's preference
            result = db.execute(
                text("""
                    SELECT persona_id FROM user_persona_preferences 
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            )
            
            row = result.fetchone()
            db.close()
            
            if row:
                return await self.get_persona(str(row.persona_id))
            return None
            
        except Exception as e:
            logger.error(f"Database error getting user persona for {user_id}: {e}")
            raise ValueError(f"Failed to get user persona: {e}")
    
    async def get_default_persona(self) -> Optional[Persona]:
        """Get the default persona (first active persona, or create Mu if none exist)"""
        try:
            # Try to get existing active personas
            personas = await self.list_personas(active_only=True)
            
            if personas:
                # Return the first active persona
                return personas[0]
            
            # No personas exist, create the default "Mu" persona
            logger.info("No personas found, creating default Mu persona")
            return await self._create_default_mu_persona()
            
        except Exception as e:
            logger.error(f"Error getting default persona: {e}")
            raise
    
    async def _create_default_mu_persona(self) -> Persona:
        """Create the default Mu persona with built-in system prompt"""
        try:
            # Use a built-in default system prompt
            system_prompt = """You are Mu, a cheerful and helpful AI assistant. You have an upbeat, positive personality and are always eager to help users with their questions and tasks. You approach every interaction with enthusiasm and care, making sure to provide clear, helpful responses while maintaining a friendly tone."""
            
            mu_persona = PersonaCreate(
                name="Mu",
                description="Cheerful robot companion with helpful, upbeat personality. Inspired by supportive anime sidekicks.",
                system_prompt=system_prompt,
                personality_traits={
                    "cheerful": True,
                    "helpful": True,
                    "robotic_charm": True,
                    "supportive": True,
                    "meditation_capable": True
                },
                capabilities={
                    "general_conversation": True,
                    "meditation_guidance": True,
                    "breathing_exercises": True,
                    "emotional_support": True,
                    "tool_usage": True
                },
                is_active=True
            )
            
            return await self.create_persona(mu_persona, created_by="system")
            
        except Exception as e:
            logger.error(f"Failed to create default Mu persona: {e}")
            raise ValueError(f"Failed to create default persona: {e}")