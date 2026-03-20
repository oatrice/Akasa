"""
Context Sync Models — Feature #23
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProjectContextResponse(BaseModel):
    """Response body for reading the current synced project."""

    active_project: str
    project_path: Optional[str] = None
    project_repo: Optional[str] = None


class ProjectContextUpdateRequest(BaseModel):
    """Request body for updating the current synced project."""

    active_project: str = Field(..., description="Shared active project name")
    project_path: Optional[str] = Field(
        default=None,
        description="Optional absolute path to bind to the active project",
    )
    project_repo: Optional[str] = Field(
        default=None,
        description="Optional GitHub repository in owner/repo format to bind to the active project",
    )

    @field_validator("active_project")
    @classmethod
    def normalize_active_project(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("active_project must not be empty")
        return normalized

    @field_validator("project_path")
    @classmethod
    def normalize_project_path(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("project_path must not be empty")
        return normalized

    @field_validator("project_repo")
    @classmethod
    def normalize_project_repo(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("project_repo must not be empty")
        return normalized
