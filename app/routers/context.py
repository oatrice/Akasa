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


@router.get(
    "/project",
    response_model=ProjectContextResponse,
    response_model_exclude_none=True,
)
async def get_active_project(_auth: bool = Depends(verify_api_key)):
    """Return the owner chat's current project for local tool sync."""
    try:
        project = await redis_service.get_owner_current_project()
        project_path = await redis_service.get_owner_project_path(project)
        project_repo = await redis_service.get_owner_project_repo(project)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to read owner project context: {exc}", exc_info=True)
        raise HTTPException(status_code=503, detail="Context sync unavailable.")

    return ProjectContextResponse(
        active_project=project,
        project_path=project_path,
        project_repo=project_repo,
    )


@router.put(
    "/project",
    response_model=ProjectContextResponse,
    response_model_exclude_none=True,
)
async def update_active_project(
    request: ProjectContextUpdateRequest,
    _auth: bool = Depends(verify_api_key),
):
    """Update the owner chat's current project for local tool sync."""
    try:
        project = await redis_service.set_owner_current_project(request.active_project)
        if request.project_path is not None:
            project_path = await redis_service.set_owner_project_path(
                project,
                request.project_path,
            )
        else:
            project_path = await redis_service.get_owner_project_path(project)

        if request.project_repo is not None:
            project_repo = await redis_service.set_owner_project_repo(
                project,
                request.project_repo,
            )
        else:
            project_repo = await redis_service.get_owner_project_repo(project)
    except ValueError as exc:
        detail = str(exc)
        status_code = 503 if "Owner chat" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail)
    except Exception as exc:
        logger.error(f"Failed to update owner project context: {exc}", exc_info=True)
        raise HTTPException(status_code=503, detail="Context sync unavailable.")

    return ProjectContextResponse(
        active_project=project,
        project_path=project_path,
        project_repo=project_repo,
    )
