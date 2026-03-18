import pytest
import os
from app.services.github_service import GitHubService, GitHubServiceError, GitHubAuthError
from app.config import settings

# Skip tests if no GITHUB_TOKEN is present
pytestmark = pytest.mark.skipif(
    not settings.GITHUB_TOKEN,
    reason="GITHUB_TOKEN not set in environment or .env"
)


def _is_external_github_env_issue(exc: Exception) -> bool:
    """Return True when failures are caused by external auth/network environment."""
    msg = str(exc).lower()
    keywords = [
        "failed to log in",
        "authentication failed",
        "token is invalid",
        "not logged in",
        "error connecting to api.github.com",
        "check your internet connection",
        "timed out",
        "network",
    ]
    return any(keyword in msg for keyword in keywords)


@pytest.fixture
def github_service():
    return GitHubService()


@pytest.fixture(scope="module", autouse=True)
def require_github_integration_prerequisites():
    """Skip integration module when auth/network prerequisites are not available."""
    service = GitHubService()
    try:
        service.check_auth()
    except (GitHubAuthError, GitHubServiceError) as exc:
        if _is_external_github_env_issue(exc):
            pytest.skip(f"Skipping GitHub integration tests due to env issue: {exc}")
        raise


def test_integration_check_auth(github_service):
    """Integration: Verify authentication status with real GitHub API."""
    try:
        assert github_service.check_auth() is True
    except (GitHubAuthError, GitHubServiceError) as e:
        if _is_external_github_env_issue(e):
            pytest.skip(f"Skipping due to GitHub environment issue: {e}")
        pytest.fail(f"Auth check failed: {e}")
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
        if _is_external_github_env_issue(e):
            pytest.skip(f"Skipping due to GitHub environment issue: {e}")
        pytest.fail(f"Listing issues failed: {e}")


def test_integration_get_repo_info(github_service):
    """Integration: Get repo info for Akasa repository."""
    repo = "oatrice/Akasa"
    try:
        info = github_service.get_repo_info(repo)
        assert info.full_name == repo
        assert info.html_url.startswith("https://github.com/")
    except GitHubServiceError as e:
        if _is_external_github_env_issue(e):
            pytest.skip(f"Skipping due to GitHub environment issue: {e}")
        pytest.fail(f"Getting repo info failed: {e}")
