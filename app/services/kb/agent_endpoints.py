"""
KB Agent API Endpoints

RESTful API endpoints for the KB Intelligent Agent functionality.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.shared.security import get_current_auth_legacy as get_current_auth
from .kb_agent import kb_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["KB Agent"])

class AgentQueryRequest(BaseModel):
    query: str
    context_path: str = "/"
    mode: str = "decision"  # decision, synthesis, validation
    model_hint: Optional[str] = None

class WorkflowRequest(BaseModel):
    workflow_path: str
    parameters: Dict[str, Any] = {}

class ValidationRequest(BaseModel):
    action: str
    rules_path: str
    context: Dict[str, Any] = {}

@router.post("/interpret")
async def interpret_knowledge(
    request: AgentQueryRequest,
    auth: dict = Depends(get_current_auth)
) -> Dict[str, Any]:
    """
    Interpret knowledge from KB and generate intelligent response.

    Modes:
    - decision: Make decisions based on KB knowledge
    - synthesis: Synthesize information across multiple sources
    - validation: Validate actions against rules
    """
    try:
        user_id = auth.get("email", auth.get("user_id", "unknown"))

        result = await kb_agent.interpret_knowledge(
            query=request.query,
            context_path=request.context_path,
            user_id=user_id,
            mode=request.mode,
            model_hint=request.model_hint
        )

        logger.info(f"KB agent interpretation for user {user_id}: mode={request.mode}, files={result.get('context_files', 0)}")

        return {
            "status": "success",
            "result": result,
            "metadata": {
                "user_id": user_id,
                "context_path": request.context_path,
                "mode": request.mode
            }
        }

    except Exception as e:
        logger.error(f"KB agent interpretation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Interpretation failed: {str(e)}")

@router.post("/workflow")
async def execute_workflow(
    request: WorkflowRequest,
    auth: dict = Depends(get_current_auth)
) -> Dict[str, Any]:
    """
    Execute a workflow defined in markdown.

    Workflows are step-by-step procedures defined in KB markdown files
    that the agent can interpret and execute with provided parameters.
    """
    try:
        user_id = auth.get("email", auth.get("user_id", "unknown"))

        result = await kb_agent.execute_knowledge_workflow(
            workflow_path=request.workflow_path,
            parameters=request.parameters,
            user_id=user_id
        )

        logger.info(f"KB agent workflow execution for user {user_id}: {request.workflow_path}")

        return {
            "status": "success",
            "result": result,
            "metadata": {
                "user_id": user_id,
                "workflow_path": request.workflow_path,
                "parameters_count": len(request.parameters)
            }
        }

    except Exception as e:
        logger.error(f"KB agent workflow execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

@router.post("/validate")
async def validate_action(
    request: ValidationRequest,
    auth: dict = Depends(get_current_auth)
) -> Dict[str, Any]:
    """
    Validate an action against rules defined in KB.

    This endpoint checks if a proposed action is valid according to
    the rules and guidelines stored in the knowledge base.
    """
    try:
        user_id = auth.get("email", auth.get("user_id", "unknown"))

        result = await kb_agent.validate_against_rules(
            action=request.action,
            rules_path=request.rules_path,
            context=request.context,
            user_id=user_id
        )

        logger.info(f"KB agent validation for user {user_id}: {request.action} against {request.rules_path}")

        return {
            "status": "success",
            "result": result,
            "metadata": {
                "user_id": user_id,
                "action": request.action,
                "rules_path": request.rules_path
            }
        }

    except Exception as e:
        logger.error(f"KB agent validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.get("/status")
async def agent_status(
    auth: dict = Depends(get_current_auth)
) -> Dict[str, Any]:
    """
    Get KB agent status and capabilities.
    """
    try:
        is_initialized = kb_agent.llm_service is not None
        cache_size = len(kb_agent.rule_cache) if hasattr(kb_agent, 'rule_cache') else 0

        return {
            "status": "success",
            "agent_status": {
                "initialized": is_initialized,
                "cache_entries": cache_size,
                "capabilities": [
                    "knowledge_interpretation",
                    "workflow_execution",
                    "rule_validation",
                    "decision_making",
                    "information_synthesis"
                ],
                "supported_modes": ["decision", "synthesis", "validation"]
            }
        }

    except Exception as e:
        logger.error(f"KB agent status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.post("/cache/clear")
async def clear_cache(
    auth: dict = Depends(get_current_auth)
) -> Dict[str, Any]:
    """
    Clear the KB agent's rule cache.
    """
    try:
        if hasattr(kb_agent, 'rule_cache'):
            cache_size = len(kb_agent.rule_cache)
            kb_agent.rule_cache.clear()
            logger.info(f"KB agent cache cleared: {cache_size} entries removed")

            return {
                "status": "success",
                "message": f"Cache cleared: {cache_size} entries removed"
            }
        else:
            return {
                "status": "success",
                "message": "No cache to clear"
            }

    except Exception as e:
        logger.error(f"KB agent cache clear failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")