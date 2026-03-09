import pytest
from unittest.mock import patch, MagicMock
import subprocess
from app.services.github_service import GitHubService, GitHubServiceError, GitHubAuthError

@pytest.fixture
def github_service():
    return GitHubService()

def test_check_gh_installed_success(github_service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert github_service.check_gh_installed() is True

def test_check_gh_installed_fail(github_service):
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(GitHubServiceError) as exc:
            github_service.check_gh_installed()
        assert "GitHub CLI (gh) is not installed" in str(exc.value)

def test_list_issues_success(github_service):
    mock_output = '[{"number": 1, "title": "Test Issue", "state": "OPEN", "url": "http://github.com/1"}]'
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout=mock_output, 
            stderr=""
        )
        issues = github_service.list_issues("owner/repo")
        assert len(issues) == 1
        assert issues[0].title == "Test Issue"
        assert issues[0].number == 1

def test_list_issues_auth_error(github_service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, 
            stdout="", 
            stderr="GraphQL: Your token has not been granted..."
        )
        with pytest.raises(GitHubAuthError):
            github_service.list_issues("owner/repo")

def test_sanitize_input(github_service):
    unsafe_title = "Issue title; rm -rf /"
    safe_title = github_service.sanitize_input(unsafe_title)
    assert ";" not in safe_title
    assert "rm -rf /" in safe_title # rm -rf / is just text if no semicolon

def test_pr_create_success(github_service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout="https://github.com/owner/repo/pull/1\n", 
            stderr=""
        )
        url = github_service.pr_create("owner/repo", "feat: test", "body", "main", "feature-1")
        assert url == "https://github.com/owner/repo/pull/1"

def test_check_auth_success(github_service):
    """Test check_auth success."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout="Logged in to github.com as oatrice", 
            stderr=""
        )
        assert github_service.check_auth() is True

def test_check_auth_fail(github_service):
    """Test check_auth failure."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, 
            stdout="", 
            stderr="You are not logged into any GitHub hosts."
        )
        with pytest.raises(GitHubAuthError):
            github_service.check_auth()

def test_create_issue_success(github_service):
    """Step 3: Test issue creation."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout="https://github.com/owner/repo/issues/123\n", 
            stderr=""
        )
        url = github_service.create_issue("owner/repo", "Test Title", "Test Body")
        assert url == "https://github.com/owner/repo/issues/123"

def test_get_pr_status_success(github_service):
    """Step 4: Test PR status retrieval."""
    mock_output = '{"pullRequests": [{"number": 1, "title": "Test PR", "state": "OPEN", "url": "http://github.com/1", "isDraft": false, "mergeable": "MERGEABLE"}]}'
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout=mock_output, 
            stderr=""
        )
        prs = github_service.get_pr_status("owner/repo")
        assert len(prs) == 1
        assert prs[0].title == "Test PR"
        assert prs[0].is_draft is False

def test_repo_not_found_error(github_service):
    """Step 6: Test repository not found error handling."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, 
            stdout="", 
            stderr="gh: Could not find repository: owner/non-existent"
        )
        with pytest.raises(GitHubServiceError) as exc:
            github_service.list_issues("owner/non-existent")
        assert "Repository not found" in str(exc.value)

def test_get_repo_info_success(github_service):
    # Fix: Use 'nameWithOwner' and 'url' to match GitHubRepo model aliases
    mock_output = '{"nameWithOwner": "owner/repo", "description": "desc", "url": "http://github.com/repo", "stargazerCount": 10}'
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout=mock_output, 
            stderr=""
        )
        repo = github_service.get_repo_info("owner/repo")
        assert repo.full_name == "owner/repo"
        assert repo.stargazers_count == 10
