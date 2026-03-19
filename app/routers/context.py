"""
Context Sync Router — Feature #23
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.models.context import ProjectContextResponse, ProjectContextUpdateRequest
from app.routers.notifications import verify_api_key
from app.services import redis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/context", tags=["context"])


@router.get("/project", response_model=ProjectContextResponse)
async def get_active_project(_auth: bool = Depends(verify_api_key)):
    """Return the owner chat's current project for local tool sync."""
    try:
        project = await redis_service.get_owner_current_project()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to read owner project context: {exc}", exc_info=True)
        raise HTTPException(status_code=503, detail="Context sync unavailable.")

    return ProjectContextResponse(active_project=project)


@router.put("/project", response_model=ProjectContextResponse)
async def update_active_project(
    request: ProjectContextUpdateRequest,
    _auth: bool = Depends(verify_api_key),
):
    """Update the owner chat's current project for local tool sync."""
    try:
        project = await redis_service.set_owner_current_project(request.active_project)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to update owner project context: {exc}", exc_info=True)
        raise HTTPException(status_code=503, detail="Context sync unavailable.")

    return ProjectContextResponse(active_project=project)
