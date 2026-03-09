from pydantic import BaseModel, Field
from typing import Optional, List

class GitHubIssue(BaseModel):
    number: int
    title: str
    state: str
    url: str
    author: Optional[dict] = None # gh issue list returns author as a dict {"id": "...", "login": "..."}

class GitHubPR(BaseModel):
    number: int
    title: str
    state: str
    url: str
    is_draft: bool = Field(False, alias="isDraft")
    mergeable: Optional[str] = None

class GitHubRepo(BaseModel):
    full_name: str = Field(..., alias="nameWithOwner")
    description: Optional[str] = None
    html_url: str = Field(..., alias="url")
    stargazers_count: int = Field(0, alias="stargazerCount")
