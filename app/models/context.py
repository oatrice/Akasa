"""
Context Sync Models — Feature #23
"""

from pydantic import BaseModel, Field, field_validator


class ProjectContextResponse(BaseModel):
    """Response body for reading the current synced project."""

    active_project: str


class ProjectContextUpdateRequest(BaseModel):
    """Request body for updating the current synced project."""

    active_project: str = Field(..., description="Shared active project name")

    @field_validator("active_project")
    @classmethod
    def normalize_active_project(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("active_project must not be empty")
        return normalized
