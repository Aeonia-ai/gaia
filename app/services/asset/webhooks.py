"""
Asset generation webhook endpoints for receiving callbacks from AI providers.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import hmac
import hashlib
import json

from app.core import logger
from app.core.config import get_settings
from app.services.assets.storage_service import SupabaseStorageService
from app.models.assets import GeneratedAsset, AssetCategory, StorageType

router = APIRouter(prefix="/webhooks", tags=["Asset Webhooks"])

# In-memory store for pending generations (use Redis in production)
pending_generations: Dict[str, Dict[str, Any]] = {}

@router.post("/meshy")
async def meshy_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint for Meshy AI generation callbacks.
    
    Expected payload:
    {
        "task_id": "task_12345",
        "status": "SUCCEEDED" | "FAILED",
        "result": {
            "model_urls": {"glb": "...", "fbx": "..."},
            "thumbnail_url": "...",
            "error": "..." (if failed)
        }
    }
    """
    try:
        # Get raw body for signature validation
        body = await request.body()
        
        # Validate webhook signature (if configured)
        if not _validate_meshy_signature(request.headers, body):
            logger.warning("Invalid Meshy webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        try:
            payload = json.loads(body.decode())
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        task_id = payload.get("task_id")
        if not task_id:
            raise HTTPException(status_code=400, detail="Missing task_id")
        
        logger.info(f"Received Meshy webhook for task {task_id}: {payload.get('status')}")
        
        # Process webhook in background
        background_tasks.add_task(_process_meshy_webhook, task_id, payload)
        
        return JSONResponse(
            status_code=200,
            content={"status": "received", "task_id": task_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Meshy webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.post("/midjourney") 
async def midjourney_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint for Midjourney generation callbacks.
    
    Expected payload:
    {
        "id": "job_12345",
        "status": "completed" | "failed",
        "image_url": "...",
        "thumbnail_url": "...",
        "error": "..." (if failed)
    }
    """
    try:
        body = await request.body()
        
        # Validate webhook signature
        if not _validate_midjourney_signature(request.headers, body):
            logger.warning("Invalid Midjourney webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        payload = json.loads(body.decode())
        job_id = payload.get("id")
        
        if not job_id:
            raise HTTPException(status_code=400, detail="Missing job id")
        
        logger.info(f"Received Midjourney webhook for job {job_id}: {payload.get('status')}")
        
        background_tasks.add_task(_process_midjourney_webhook, job_id, payload)
        
        return JSONResponse(
            status_code=200,
            content={"status": "received", "job_id": job_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Midjourney webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.post("/mubert")
async def mubert_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint for Mubert audio generation callbacks.
    
    Expected payload:
    {
        "id": "task_12345", 
        "status": "completed" | "failed",
        "download_url": "...",
        "waveform_url": "...",
        "duration": 30,
        "error": "..." (if failed)
    }
    """
    try:
        body = await request.body()
        
        # Validate webhook signature
        if not _validate_mubert_signature(request.headers, body):
            logger.warning("Invalid Mubert webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        payload = json.loads(body.decode())
        task_id = payload.get("id")
        
        if not task_id:
            raise HTTPException(status_code=400, detail="Missing task id")
        
        logger.info(f"Received Mubert webhook for task {task_id}: {payload.get('status')}")
        
        background_tasks.add_task(_process_mubert_webhook, task_id, payload)
        
        return JSONResponse(
            status_code=200,
            content={"status": "received", "task_id": task_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mubert webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def _process_meshy_webhook(task_id: str, payload: Dict[str, Any]):
    """Process Meshy webhook payload in background."""
    try:
        status = payload.get("status")
        
        # Get pending generation info
        generation_info = pending_generations.get(task_id)
        if not generation_info:
            logger.warning(f"No pending generation found for Meshy task {task_id}")
            return
        
        if status == "SUCCEEDED":
            # Update generation with results
            result = payload.get("result", {})
            
            # Store the completed asset
            storage_service = SupabaseStorageService()
            
            # Download and store the 3D model
            model_url = result.get("model_urls", {}).get("glb")
            if model_url:
                # TODO: Download model and store in Supabase Storage
                logger.info(f"Meshy task {task_id} completed successfully")
                
                # Update pending generation status
                generation_info["status"] = "completed"
                generation_info["result"] = result
                generation_info["completed_at"] = datetime.utcnow().isoformat()
            else:
                logger.error(f"Meshy task {task_id} succeeded but no model URL provided")
                
        elif status == "FAILED":
            error = payload.get("result", {}).get("error", "Unknown error")
            logger.error(f"Meshy task {task_id} failed: {error}")
            
            generation_info["status"] = "failed"
            generation_info["error"] = error
            generation_info["completed_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        logger.error(f"Failed to process Meshy webhook for task {task_id}: {e}")


async def _process_midjourney_webhook(job_id: str, payload: Dict[str, Any]):
    """Process Midjourney webhook payload in background."""
    try:
        status = payload.get("status")
        
        generation_info = pending_generations.get(job_id)
        if not generation_info:
            logger.warning(f"No pending generation found for Midjourney job {job_id}")
            return
        
        if status == "completed":
            # Store the completed image
            image_url = payload.get("image_url")
            if image_url:
                logger.info(f"Midjourney job {job_id} completed successfully")
                
                generation_info["status"] = "completed"
                generation_info["result"] = payload
                generation_info["completed_at"] = datetime.utcnow().isoformat()
            else:
                logger.error(f"Midjourney job {job_id} completed but no image URL provided")
                
        elif status == "failed":
            error = payload.get("error", "Unknown error")
            logger.error(f"Midjourney job {job_id} failed: {error}")
            
            generation_info["status"] = "failed"
            generation_info["error"] = error
            generation_info["completed_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        logger.error(f"Failed to process Midjourney webhook for job {job_id}: {e}")


async def _process_mubert_webhook(task_id: str, payload: Dict[str, Any]):
    """Process Mubert webhook payload in background."""
    try:
        status = payload.get("status")
        
        generation_info = pending_generations.get(task_id)
        if not generation_info:
            logger.warning(f"No pending generation found for Mubert task {task_id}")
            return
        
        if status == "completed":
            # Store the completed audio
            download_url = payload.get("download_url")
            if download_url:
                logger.info(f"Mubert task {task_id} completed successfully")
                
                generation_info["status"] = "completed"
                generation_info["result"] = payload
                generation_info["completed_at"] = datetime.utcnow().isoformat()
            else:
                logger.error(f"Mubert task {task_id} completed but no download URL provided")
                
        elif status == "failed":
            error = payload.get("error", "Unknown error")
            logger.error(f"Mubert task {task_id} failed: {error}")
            
            generation_info["status"] = "failed"
            generation_info["error"] = error
            generation_info["completed_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        logger.error(f"Failed to process Mubert webhook for task {task_id}: {e}")


def _validate_meshy_signature(headers: Dict[str, str], body: bytes) -> bool:
    """Validate Meshy webhook signature."""
    settings = get_settings()
    webhook_secret = getattr(settings, 'MESHY_WEBHOOK_SECRET', None)
    
    if not webhook_secret:
        # Skip validation if no secret is configured (development mode)
        return True
    
    signature_header = headers.get("x-meshy-signature")
    if not signature_header:
        return False
    
    # Compute expected signature
    expected_signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature_header)


def _validate_midjourney_signature(headers: Dict[str, str], body: bytes) -> bool:
    """Validate Midjourney webhook signature."""
    settings = get_settings()
    webhook_secret = getattr(settings, 'MIDJOURNEY_WEBHOOK_SECRET', None)
    
    if not webhook_secret:
        return True
    
    signature_header = headers.get("x-midjourney-signature")
    if not signature_header:
        return False
    
    expected_signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature_header)


def _validate_mubert_signature(headers: Dict[str, str], body: bytes) -> bool:
    """Validate Mubert webhook signature."""
    settings = get_settings()
    webhook_secret = getattr(settings, 'MUBERT_WEBHOOK_SECRET', None)
    
    if not webhook_secret:
        return True
    
    signature_header = headers.get("x-mubert-signature")
    if not signature_header:
        return False
    
    expected_signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature_header)


def register_pending_generation(task_id: str, generation_info: Dict[str, Any]):
    """Register a pending generation for webhook tracking."""
    pending_generations[task_id] = {
        **generation_info,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }


def get_generation_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a pending generation."""
    return pending_generations.get(task_id)


def cleanup_completed_generation(task_id: str):
    """Remove a completed generation from tracking."""
    pending_generations.pop(task_id, None)