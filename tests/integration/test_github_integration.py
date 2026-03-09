import pytest
import os
from app.services.github_service import GitHubService, GitHubServiceError
from app.config import settings

# Skip tests if no GITHUB_TOKEN is present
pytestmark = pytest.mark.skipif(
    not settings.GITHUB_TOKEN,
    reason="GITHUB_TOKEN not set in environment or .env"
)

@pytest.fixture
def github_service():
    return GitHubService()

def test_integration_check_auth(github_service):
    """Integration: Verify authentication status with real GitHub API."""
    try:
        assert github_service.check_auth() is True
    except Exception as e:
        pytest.fail(f"Auth check failed: {e}")

def test_integration_list_issues(github_service):
    """Integration: List issues for Akasa repository."""
    repo = "oatrice/Akasa"
    try:
        issues = github_service.list_issues(repo, limit=1)
        assert isinstance(issues, list)
        if len(issues) > 0:
            assert issues[0].number > 0
            assert issues[0].title != ""
    except GitHubServiceError as e:
        pytest.fail(f"Listing issues failed: {e}")

def test_integration_get_repo_info(github_service):
    """Integration: Get repo info for Akasa repository."""
    repo = "oatrice/Akasa"
    try:
        info = github_service.get_repo_info(repo)
        assert info.full_name == repo
        assert info.html_url.startswith("https://github.com/")
    except GitHubServiceError as e:
        pytest.fail(f"Getting repo info failed: {e}")
