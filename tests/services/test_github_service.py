import pytest
from unittest.mock import patch, MagicMock
import subprocess
import base64
from app.services.github_service import GitHubService, GitHubServiceError, GitHubAuthError
from app.config import settings
from app.models.github import GitHubIssue

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

def test_normalize_duration_for_project(github_service):
    assert github_service._normalize_duration_for_project("38883s") == "10h 48m"
    assert github_service._normalize_duration_for_project("90m") == "1h 30m"
    assert github_service._normalize_duration_for_project("2h") == "2h"
    assert github_service._normalize_duration_for_project("45s") == "45s"

def test_create_issue_with_duration_syncs_project_card(github_service, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_PROJECT_OWNER", "oatrice")
    monkeypatch.setattr(settings, "GITHUB_PROJECT_NUMBER", 9)
    monkeypatch.setattr(settings, "GITHUB_PROJECT_DURATION_FIELD_NAME", "Duration")

    with patch.object(github_service, "_run_gh_command") as mock_run:
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="https://github.com/owner/repo/issues/123\n",
                stderr="",
            ),
            MagicMock(returncode=0, stdout='{"id":"project_123"}', stderr=""),
            MagicMock(
                returncode=0,
                stdout='{"fields":[{"id":"field_duration","name":"Duration","dataType":"TEXT"}]}',
                stderr="",
            ),
            MagicMock(returncode=0, stdout='{"items":[]}', stderr=""),
            MagicMock(returncode=0, stdout='{"id":"item_123"}', stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        url = github_service.create_issue(
            "owner/repo",
            "Test Title",
            "Test Body",
            duration="38883s",
        )

    assert url == "https://github.com/owner/repo/issues/123"
    assert mock_run.call_args_list[0].args[0] == [
        "issue",
        "create",
        "--repo",
        "owner/repo",
        "--title",
        "Test Title",
        "--body",
        "Test Body",
    ]
    assert mock_run.call_args_list[-1].args[0] == [
        "project",
        "item-edit",
        "--id",
        "item_123",
        "--project-id",
        "project_123",
        "--field-id",
        "field_duration",
        "--text",
        "10h 48m",
    ]

def test_create_issue_returns_url_when_duration_sync_fails(github_service, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_PROJECT_OWNER", "oatrice")
    monkeypatch.setattr(settings, "GITHUB_PROJECT_NUMBER", 9)

    with patch.object(github_service, "_run_gh_command") as mock_run:
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="https://github.com/owner/repo/issues/123\n",
                stderr="",
            ),
            GitHubServiceError("project scope missing"),
        ]

        url = github_service.create_issue(
            "owner/repo",
            "Test Title",
            "Test Body",
            duration="90m",
        )

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


def test_extract_repo_from_remote_url_supports_https_and_ssh(github_service):
    assert (
        github_service._extract_repo_from_remote_url(
            "https://github.com/oatrice/Akasa.git"
        )
        == "oatrice/Akasa"
    )
    assert (
        github_service._extract_repo_from_remote_url("git@github.com:oatrice/Akasa.git")
        == "oatrice/Akasa"
    )


def test_get_repo_from_local_path_uses_origin_when_available(github_service):
    with patch.object(github_service, "_run_git_command") as mock_git:
        mock_git.side_effect = [
            "https://github.com/oatrice/Akasa.git",
            "origin\nupstream\n",
            "git@github.com:someone/else.git",
        ]

        repo = github_service.get_repo_from_local_path("/tmp/akasa")

    assert repo == "oatrice/Akasa"


def test_get_local_roadmap_content_reads_docs_roadmap(github_service, tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    roadmap_path = docs_dir / "ROADMAP.md"
    roadmap_path.write_text("# Roadmap\n\n## Phase 1\n", encoding="utf-8")

    resolved_path, content = github_service.get_local_roadmap_content(str(tmp_path))

    assert resolved_path.endswith("docs/ROADMAP.md")
    assert "Phase 1" in content


def test_get_remote_roadmap_content_decodes_base64(github_service):
    encoded = base64.b64encode(b"# Roadmap\n\n## Phase 1\n").decode("ascii")
    with patch.object(github_service, "_run_gh_command") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                '{"content":"%s","encoding":"base64","html_url":"https://github.com/owner/repo/blob/main/docs/ROADMAP.md"}'
                % encoded
            ),
            stderr="",
        )

        url, content = github_service.get_remote_roadmap_content("owner/repo")

    assert url == "https://github.com/owner/repo/blob/main/docs/ROADMAP.md"
    assert "Phase 1" in content


def test_get_repo_kanban_summary_chooses_linked_project_with_most_matches(github_service):
    with patch.object(github_service, "_list_owner_projects") as mock_projects, patch.object(
        github_service, "_get_project_items"
    ) as mock_items, patch.object(github_service, "_get_project_view_data") as mock_view:
        mock_projects.return_value = [
            {"number": 1, "title": "Platform"},
            {"number": 2, "title": "Akasa Delivery"},
        ]
        mock_items.side_effect = [
            [
                {
                    "status": "In Progress",
                    "content": {
                        "repository": "oatrice/Akasa",
                        "title": "Investigate queue lag",
                        "number": 81,
                        "url": "https://github.com/oatrice/Akasa/issues/81",
                    },
                }
            ],
            [
                {
                    "status": "Todo",
                    "content": {
                        "repository": "oatrice/Akasa",
                        "title": "Add kanban command",
                        "number": 82,
                        "url": "https://github.com/oatrice/Akasa/issues/82",
                    },
                },
                {
                    "status": "Todo",
                    "content": {
                        "repository": "oatrice/Akasa",
                        "title": "Summarize roadmap",
                        "number": 83,
                        "url": "https://github.com/oatrice/Akasa/issues/83",
                    },
                },
            ],
        ]
        mock_view.return_value = {
            "title": "Akasa Delivery",
            "url": "https://github.com/users/oatrice/projects/2",
        }

        summary = github_service.get_repo_kanban_summary("oatrice/Akasa")

    assert summary["source"] == "project"
    assert summary["project_title"] == "Akasa Delivery"
    assert summary["selection_note"] is not None
    assert summary["columns"][0]["name"] == "Todo"
    assert summary["columns"][0]["count"] == 2


def test_get_repo_kanban_summary_falls_back_to_open_issues(github_service):
    with patch.object(github_service, "_list_owner_projects", return_value=[]), patch.object(
        github_service,
        "list_issues",
        return_value=[
            GitHubIssue(
                number=82,
                title="Add kanban command",
                state="OPEN",
                url="https://github.com/oatrice/Akasa/issues/82",
            )
        ],
    ):
        summary = github_service.get_repo_kanban_summary("oatrice/Akasa")

    assert summary["source"] == "open_issues"
    assert summary["issues"][0]["number"] == 82


def test_get_repo_kanban_summary_falls_back_to_open_issues_when_project_discovery_fails(
    github_service,
):
    with patch.object(
        github_service,
        "_list_owner_projects",
        side_effect=GitHubServiceError("unknown owner type"),
    ), patch.object(
        github_service,
        "list_issues",
        return_value=[
            GitHubIssue(
                number=82,
                title="Add kanban command",
                state="OPEN",
                url="https://github.com/oatrice/Akasa/issues/82",
            )
        ],
    ):
        summary = github_service.get_repo_kanban_summary("oatrice/Akasa")

    assert summary["source"] == "open_issues"
    assert summary["issues"][0]["title"] == "Add kanban command"

def test_search_issues_success_with_limit(github_service):
    """Test search_issues with limit parameter."""
    mock_output = '[{"number": 1, "title": "Test Issue", "state": "CLOSED", "url": "http://github.com/1"}]'
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout=mock_output, 
            stderr=""
        )
        issues = github_service.search_issues("is:closed", "owner/repo", limit=3)
        assert len(issues) == 1
        assert issues[0].title == "Test Issue"
        assert issues[0].number == 1
        
        # Verify that '--limit' '3' was passed to the gh command
        args = mock_run.call_args[0][0]
        assert "--limit" in args
        assert "3" in args
