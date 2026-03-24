import base64
import subprocess
import json
import os
import re
from typing import Any, List, Optional
from app.config import settings
from app.models.github import GitHubIssue, GitHubPR, GitHubRepo
import logging

logger = logging.getLogger(__name__)

_DURATION_TOKEN_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>hours?|hrs?|hr|h|minutes?|mins?|min|m|seconds?|secs?|sec|s)",
    re.IGNORECASE,
)
_GITHUB_REMOTE_PATTERNS = [
    re.compile(r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"),
    re.compile(r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"),
    re.compile(r"^ssh://git@github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"),
]
_ROADMAP_RELATIVE_PATH = os.path.join("docs", "ROADMAP.md")

class GitHubServiceError(Exception):
    """Base exception for GitHub Service errors."""
    pass

class GitHubAuthError(GitHubServiceError):
    """Exception raised for authentication issues."""
    pass

class GitHubService:
    def __init__(self):
        self.token = settings.GITHUB_TOKEN
        self.gh_path = "gh"

    def check_gh_installed(self) -> bool:
        """Check if GitHub CLI (gh) is installed in the system."""
        try:
            subprocess.run([self.gh_path, "--version"], capture_output=True, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise GitHubServiceError("GitHub CLI (gh) is not installed on the server.")

    def check_auth(self) -> bool:
        """Check if GitHub CLI is authenticated."""
        try:
            self._run_gh_command(["auth", "status"])
            return True
        except GitHubAuthError:
            raise
        except GitHubServiceError as e:
            raise GitHubAuthError(f"Authentication check failed: {str(e)}")

    def sanitize_input(self, text: str) -> str:
        """Basic sanitization to prevent command injection characters."""
        if not text:
            return ""
        return re.sub(r'[;&|`$]', '', text)

    def _parse_json_output(self, stdout: str) -> Any:
        text = (stdout or "").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def _extract_list_payload(self, data: Any, preferred_key: str) -> list[dict]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            if isinstance(data.get(preferred_key), list):
                return [item for item in data[preferred_key] if isinstance(item, dict)]
            for value in data.values():
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    def _normalize_duration_for_project(self, duration: str) -> str:
        text = (duration or "").strip()
        if not text:
            return text

        matches = list(_DURATION_TOKEN_RE.finditer(text))
        if not matches:
            if text.isdigit():
                return self._format_duration_minutes_hours(float(text))
            return text

        total_seconds = 0.0
        for match in matches:
            value = float(match.group("value"))
            unit = match.group("unit").lower()
            if unit.startswith("h"):
                total_seconds += value * 3600
            elif unit.startswith("m"):
                total_seconds += value * 60
            else:
                total_seconds += value

        return self._format_duration_minutes_hours(total_seconds)

    def _format_duration_minutes_hours(self, total_seconds: float) -> str:
        if total_seconds < 60:
            seconds = max(int(round(total_seconds)), 0)
            return f"{seconds}s"

        rounded_minutes = max(int(round(total_seconds / 60.0)), 0)
        hours, minutes = divmod(rounded_minutes, 60)

        if hours and minutes:
            return f"{hours}h {minutes}m"
        if hours:
            return f"{hours}h"
        return f"{minutes}m"

    def _get_project_owner(self, repo: str) -> str:
        configured_owner = (settings.GITHUB_PROJECT_OWNER or "").strip()
        if configured_owner:
            return configured_owner
        return repo.split("/", 1)[0]

    def _get_project_id(self, project_owner: str, project_number: int) -> str:
        result = self._run_gh_command(
            [
                "project",
                "view",
                str(project_number),
                "--owner",
                project_owner,
                "--format",
                "json",
            ]
        )
        data = self._parse_json_output(result.stdout)
        if isinstance(data, dict) and data.get("id"):
            return str(data["id"])
        if isinstance(data, str) and data:
            return data
        raise GitHubServiceError("Failed to resolve GitHub project ID.")

    def _get_or_create_duration_field_id(
        self,
        project_owner: str,
        project_number: int,
        field_name: str,
    ) -> str:
        result = self._run_gh_command(
            [
                "project",
                "field-list",
                str(project_number),
                "--owner",
                project_owner,
                "--format",
                "json",
            ]
        )
        fields = self._extract_list_payload(
            self._parse_json_output(result.stdout), preferred_key="fields"
        )
        for field in fields:
            if field.get("name") == field_name and field.get("id"):
                return str(field["id"])

        create_result = self._run_gh_command(
            [
                "project",
                "field-create",
                str(project_number),
                "--owner",
                project_owner,
                "--name",
                field_name,
                "--data-type",
                "TEXT",
                "--format",
                "json",
            ]
        )
        created = self._parse_json_output(create_result.stdout)
        if isinstance(created, dict) and created.get("id"):
            return str(created["id"])
        raise GitHubServiceError(f"Failed to create project field '{field_name}'.")

    def _get_project_item_id(
        self,
        project_owner: str,
        project_number: int,
        issue_url: str,
    ) -> Optional[str]:
        result = self._run_gh_command(
            [
                "project",
                "item-list",
                str(project_number),
                "--owner",
                project_owner,
                "--format",
                "json",
            ]
        )
        items = self._extract_list_payload(
            self._parse_json_output(result.stdout), preferred_key="items"
        )
        for item in items:
            content = item.get("content")
            if isinstance(content, dict) and content.get("url") == issue_url and item.get("id"):
                return str(item["id"])
        return None

    def _ensure_project_item_id(
        self,
        project_owner: str,
        project_number: int,
        issue_url: str,
    ) -> str:
        existing_item_id = self._get_project_item_id(project_owner, project_number, issue_url)
        if existing_item_id:
            return existing_item_id

        try:
            add_result = self._run_gh_command(
                [
                    "project",
                    "item-add",
                    str(project_number),
                    "--owner",
                    project_owner,
                    "--url",
                    issue_url,
                    "--format",
                    "json",
                ]
            )
            added = self._parse_json_output(add_result.stdout)
            if isinstance(added, dict) and added.get("id"):
                return str(added["id"])
        except GitHubServiceError:
            # Another automation may have added the issue between list and add.
            pass

        added_item_id = self._get_project_item_id(project_owner, project_number, issue_url)
        if added_item_id:
            return added_item_id
        raise GitHubServiceError("Failed to resolve GitHub project item ID for the issue.")

    def sync_issue_duration_to_project_card(
        self,
        repo: str,
        issue_url: str,
        duration: str,
    ) -> None:
        project_number = settings.GITHUB_PROJECT_NUMBER
        if not project_number:
            raise GitHubServiceError("GITHUB_PROJECT_NUMBER is not configured.")

        project_owner = self._get_project_owner(repo)
        field_name = (settings.GITHUB_PROJECT_DURATION_FIELD_NAME or "Duration").strip() or "Duration"
        normalized_duration = self._normalize_duration_for_project(duration)

        project_id = self._get_project_id(project_owner, project_number)
        field_id = self._get_or_create_duration_field_id(
            project_owner, project_number, field_name
        )
        item_id = self._ensure_project_item_id(project_owner, project_number, issue_url)

        self._run_gh_command(
            [
                "project",
                "item-edit",
                "--id",
                item_id,
                "--project-id",
                project_id,
                "--field-id",
                field_id,
                "--text",
                normalized_duration,
            ]
        )

    def _run_gh_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Execute a gh CLI command securely."""
        self.check_gh_installed()
        
        env = os.environ.copy()
        if self.token:
            env["GH_TOKEN"] = self.token
        
        try:
            result = subprocess.run(
                [self.gh_path] + args,
                capture_output=True,
                text=True,
                env=env,
                check=False
            )
            
            if result.returncode != 0:
                stderr = result.stderr.lower()
                if "not logged in" in stderr or "token" in stderr or "graphql: your token" in stderr:
                    raise GitHubAuthError(f"GitHub Authentication failed: {result.stderr.strip()}")
                if "could not find repository" in stderr or ("404" in stderr and "repo" in stderr):
                    raise GitHubServiceError(f"Repository not found: {result.stderr.strip()}")
                
                raise GitHubServiceError(f"GitHub CLI error: {result.stderr.strip()}")
                
            return result
        except Exception as e:
            if not isinstance(e, GitHubServiceError):
                logger.exception("Unexpected error running gh command")
                raise GitHubServiceError(f"Unexpected error: {str(e)}")
            raise

    def _extract_repo_from_remote_url(self, remote_url: str) -> Optional[str]:
        cleaned = (remote_url or "").strip()
        if not cleaned:
            return None

        for pattern in _GITHUB_REMOTE_PATTERNS:
            match = pattern.match(cleaned)
            if match:
                return f"{match.group('owner')}/{match.group('repo')}"
        return None

    def get_repo_from_local_path(self, project_path: str) -> Optional[str]:
        """Resolve owner/repo from a local git remote URL."""
        normalized_path = os.path.abspath(os.path.expanduser(project_path))

        remote_candidates: list[str] = []
        try:
            origin_url = self._run_git_command(
                ["-C", normalized_path, "remote", "get-url", "origin"]
            )
            remote_candidates.append(origin_url)
        except GitHubServiceError:
            pass

        try:
            remotes_output = self._run_git_command(["-C", normalized_path, "remote"])
            for remote_name in remotes_output.splitlines():
                name = remote_name.strip()
                if not name or name == "origin":
                    continue
                try:
                    remote_candidates.append(
                        self._run_git_command(
                            ["-C", normalized_path, "remote", "get-url", name]
                        )
                    )
                except GitHubServiceError:
                    continue
        except GitHubServiceError:
            pass

        for remote_url in remote_candidates:
            repo = self._extract_repo_from_remote_url(remote_url)
            if repo:
                return repo

        return None

    def get_local_roadmap_content(self, project_path: str) -> tuple[str, str]:
        """Read planning docs from a bound local project path."""
        planning_docs = ["docs/ROADMAP.md", "docs/7_ISSUE_NEXT_STEPS.md", "docs/8_NEXT_WEEK_THEME.md"]
        base_path = os.path.abspath(os.path.expanduser(project_path))
        
        found_paths = []
        combined_content = []
        
        for doc_path in planning_docs:
            full_path = os.path.join(base_path, *doc_path.split("/"))
            if os.path.isfile(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        combined_content.append(f"## 📁 {doc_path}\n{f.read()}")
                        found_paths.append(doc_path)
                except OSError as e:
                    logger.warning(f"Failed to read local roadmap {doc_path}: {e}")
                    
        if not combined_content:
            raise GitHubServiceError(f"No planning docs (ROADMAP.md etc) found in bound path: {project_path}")
            
        main_path = os.path.join(base_path, found_paths[0])
        return main_path, "\n\n".join(combined_content)

    def get_remote_roadmap_content(self, repo: str) -> tuple[str, str]:
        """Fetch planning docs from GitHub repository contents API."""
        planning_docs = ["docs/ROADMAP.md", "docs/7_ISSUE_NEXT_STEPS.md", "docs/8_NEXT_WEEK_THEME.md"]
        
        found_urls = []
        combined_content = []
        
        for doc_path in planning_docs:
            try:
                result = self._run_gh_command(["api", f"repos/{repo}/contents/{doc_path}"])
                data = self._parse_json_output(result.stdout)
                
                if isinstance(data, dict):
                    encoded_content = data.get("content")
                    if encoded_content:
                        raw_bytes = base64.b64decode(str(encoded_content), validate=False)
                        content = raw_bytes.decode("utf-8")
                        combined_content.append(f"## 📁 {doc_path}\n{content}")
                        
                        url = data.get("html_url") or data.get("download_url") or f"https://github.com/{repo}/blob/HEAD/{doc_path}"
                        found_urls.append(str(url))
            except GitHubServiceError as e:
                message = str(e).lower()
                if "404" not in message and "not found" not in message:
                    logger.warning(f"Failed to fetch remote planning doc {doc_path} for {repo}: {e}")
            except (ValueError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to decode remote planning doc {doc_path} for {repo}: {e}")
                
        if not combined_content:
            raise GitHubServiceError(f"No planning docs (ROADMAP.md etc) found in {repo}.")
            
        return found_urls[0], "\n\n".join(combined_content)

    def _list_owner_projects(self, owner: str, limit: int = 30) -> list[dict]:
        result = self._run_gh_command(
            [
                "project",
                "list",
                "--owner",
                owner,
                "--limit",
                str(limit),
                "--format",
                "json",
            ]
        )
        return self._extract_list_payload(
            self._parse_json_output(result.stdout), preferred_key="projects"
        )

    def _get_project_items(
        self,
        owner: str,
        project_number: int,
        limit: int = 100,
    ) -> list[dict]:
        result = self._run_gh_command(
            [
                "project",
                "item-list",
                str(project_number),
                "--owner",
                owner,
                "--limit",
                str(limit),
                "--format",
                "json",
            ]
        )
        return self._extract_list_payload(
            self._parse_json_output(result.stdout), preferred_key="items"
        )

    def _get_project_view_data(self, owner: str, project_number: int) -> dict:
        result = self._run_gh_command(
            [
                "project",
                "view",
                str(project_number),
                "--owner",
                owner,
                "--format",
                "json",
            ]
        )
        data = self._parse_json_output(result.stdout)
        return data if isinstance(data, dict) else {}

    def _extract_item_repo(self, item: dict) -> Optional[str]:
        content = item.get("content")
        if isinstance(content, dict):
            repository = content.get("repository")
            if isinstance(repository, str) and repository:
                return repository
            if isinstance(repository, dict):
                for key in ("nameWithOwner", "fullName", "full_name"):
                    value = repository.get(key)
                    if isinstance(value, str) and value:
                        return value

        for key in ("repository", "repo"):
            value = item.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, dict):
                for inner_key in ("nameWithOwner", "fullName", "full_name"):
                    inner_value = value.get(inner_key)
                    if isinstance(inner_value, str) and inner_value:
                        return inner_value

        return None

    def _item_matches_repo(self, item: dict, repo: str) -> bool:
        repo_lower = repo.lower()
        item_repo = self._extract_item_repo(item)
        if item_repo and item_repo.lower() == repo_lower:
            return True

        content = item.get("content")
        candidate_urls = []
        if isinstance(content, dict):
            if isinstance(content.get("url"), str):
                candidate_urls.append(content["url"])
        if isinstance(item.get("url"), str):
            candidate_urls.append(item["url"])

        return any(f"github.com/{repo_lower}/" in url.lower() for url in candidate_urls)

    def _extract_item_status(self, item: dict) -> str:
        for key in ("status", "Status", "column", "columnName"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        field_values = item.get("fieldValues") or item.get("field_values")
        if isinstance(field_values, dict):
            status_value = field_values.get("Status") or field_values.get("status")
            if isinstance(status_value, str) and status_value.strip():
                return status_value.strip()

        if isinstance(field_values, list):
            for field in field_values:
                if not isinstance(field, dict):
                    continue
                field_name = field.get("name")
                if not field_name and isinstance(field.get("field"), dict):
                    field_name = field["field"].get("name")
                if str(field_name).strip().lower() != "status":
                    continue

                for key in ("optionName", "value", "text", "name", "title", "status"):
                    value = field.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                option = field.get("option")
                if isinstance(option, dict):
                    for key in ("name", "value"):
                        value = option.get(key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()

        return "Open"

    def _extract_item_brief(self, item: dict) -> dict:
        content = item.get("content") if isinstance(item.get("content"), dict) else {}
        title = (
            content.get("title")
            or item.get("title")
            or content.get("body")
            or "Untitled"
        )
        url = content.get("url") or item.get("url")
        number = content.get("number") or item.get("number")
        return {
            "title": str(title),
            "url": str(url) if url else None,
            "number": number if isinstance(number, int) else None,
        }

    def get_repo_kanban_summary(
        self,
        repo: str,
        project_limit: int = 30,
        item_limit: int = 100,
        fallback_issue_limit: int = 5,
    ) -> dict:
        """Return kanban summary data for a repo, falling back to open issues."""
        owner = repo.split("/", 1)[0]
        try:
            projects = self._list_owner_projects(owner, limit=project_limit)
        except GitHubServiceError as e:
            logger.warning(
                "Falling back to open issues for %s because project discovery failed: %s",
                repo,
                e,
            )
            projects = []

        candidates = []
        for project in projects:
            project_number = project.get("number")
            if not isinstance(project_number, int):
                continue

            try:
                items = self._get_project_items(owner, project_number, limit=item_limit)
            except GitHubServiceError as e:
                logger.warning(
                    "Skipping GitHub project %s for %s due to item-list error: %s",
                    project_number,
                    repo,
                    e,
                )
                continue

            matched_items = [item for item in items if self._item_matches_repo(item, repo)]
            if matched_items:
                candidates.append(
                    {
                        "project": project,
                        "items": matched_items,
                    }
                )

        if not candidates:
            issues = self.list_issues(repo, limit=fallback_issue_limit)
            return {
                "repo": repo,
                "source": "open_issues",
                "issues": [
                    {
                        "number": issue.number,
                        "title": issue.title,
                        "url": issue.url,
                    }
                    for issue in issues
                ],
            }

        candidates.sort(key=lambda candidate: len(candidate["items"]), reverse=True)
        selected = candidates[0]
        project = selected["project"]
        project_number = int(project.get("number"))
        try:
            project_view = self._get_project_view_data(owner, project_number)
        except GitHubServiceError as e:
            logger.warning(
                "Failed to fetch detailed GitHub project view for %s #%s: %s",
                repo,
                project_number,
                e,
            )
            project_view = {}

        columns: dict[str, list[dict]] = {}
        for item in selected["items"]:
            status = self._extract_item_status(item)
            columns.setdefault(status, []).append(self._extract_item_brief(item))

        ordered_columns = []
        for status_name, items in columns.items():
            ordered_columns.append(
                {
                    "name": status_name,
                    "count": len(items),
                    "items": items[:3],
                }
            )
        ordered_columns.sort(key=lambda column: (-column["count"], column["name"].lower()))

        selection_note = None
        if len(candidates) > 1:
            project_title = (
                project_view.get("title")
                or project.get("title")
                or f"Project {project_number}"
            )
            selection_note = (
                f"Multiple linked projects found. Showing '{project_title}' "
                "based on the strongest linked-repo match."
            )

        return {
            "repo": repo,
            "source": "project",
            "project_title": (
                project_view.get("title")
                or project.get("title")
                or f"Project {project_number}"
            ),
            "project_url": project_view.get("url") or project.get("url"),
            "project_number": project_number,
            "columns": ordered_columns,
            "selection_note": selection_note,
        }

    def get_issue(self, repo: str, issue_number: int) -> GitHubIssue:
        """Get details of a specific issue."""
        args = ["issue", "view", str(issue_number), "--repo", repo, "--json", "number,title,state,url,body,author"]
        result = self._run_gh_command(args)

        try:
            data = json.loads(result.stdout)
            return GitHubIssue(**data)
        except (json.JSONDecodeError, AttributeError, KeyError) as e:
            raise GitHubServiceError(f"Failed to parse issue details: {str(e)}")

    def list_issues(self, repo: str, limit: int = 30) -> List[GitHubIssue]:
        """List open issues in a repository."""
        args = ["issue", "list", "--repo", repo, "--limit", str(limit), "--json", "number,title,state,url,author"]
        result = self._run_gh_command(args)

        try:
            data = json.loads(result.stdout)
            return [GitHubIssue(**issue) for issue in data]
        except (json.JSONDecodeError, AttributeError, KeyError):
            raise GitHubServiceError("Failed to parse GitHub issues list.")

    def search_issues(self, query: str, repo: str, limit: int = 30) -> List[GitHubIssue]:
        """Search for issues in a repository."""
        # gh issue list --search "query" --repo repo
        args = ["issue", "list", "--repo", repo, "--search", query, "--limit", str(limit), "--json", "number,title,state,url,author"]
        result = self._run_gh_command(args)

        try:
            data = json.loads(result.stdout)
            return [GitHubIssue(**issue) for issue in data]
        except (json.JSONDecodeError, AttributeError, KeyError):
            raise GitHubServiceError("Failed to parse GitHub search results.")

    def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        duration: Optional[str] = None,
    ) -> str:

        """Create a new issue and return the URL."""
        title = self.sanitize_input(title)
        body = self.sanitize_input(body)
        
        args = ["issue", "create", "--repo", repo, "--title", title, "--body", body]
        result = self._run_gh_command(args)
        
        url = result.stdout.strip()
        if url.startswith("http"):
            if duration:
                try:
                    self.sync_issue_duration_to_project_card(
                        repo=repo,
                        issue_url=url,
                        duration=duration,
                    )
                except GitHubServiceError as exc:
                    logger.warning(
                        "Issue created but failed to sync Duration project field: %s",
                        exc,
                    )
            return url
        raise GitHubServiceError(f"Unexpected output from issue creation: {url}")

    def create_comment(self, repo: str, issue_number: int, body: str) -> str:
        """Add a comment to an existing issue or pull request and return the URL."""
        body = self.sanitize_input(body)
        
        # gh issue comment <number> --body "..."
        args = ["issue", "comment", str(issue_number), "--repo", repo, "--body", body]
        result = self._run_gh_command(args)
        
        url = result.stdout.strip()
        if url.startswith("http"):
            return url
        raise GitHubServiceError(f"Unexpected output from comment creation: {url}")

    def close_issue(self, repo: str, issue_number: int) -> str:
        """Close an existing issue."""
        args = ["issue", "close", str(issue_number), "--repo", repo]
        result = self._run_gh_command(args)
        return f"Successfully closed issue #{issue_number} in {repo}"

    def delete_issue(self, repo: str, issue_number: int) -> str:
        """Delete an existing issue (Permanent)."""
        # gh issue delete <number> --repo <repo> --yes (to skip confirmation)
        args = ["issue", "delete", str(issue_number), "--repo", repo, "--yes"]
        result = self._run_gh_command(args)
        return f"Successfully deleted issue #{issue_number} from {repo}"

    def get_pr_status(self, repo: str) -> List[GitHubPR]:
        """Get the status of PRs in a repository."""
        # Use 'status' instead of 'list' to match existing tests and models
        args = ["pr", "status", "--repo", repo, "--json", "number,title,state,url,isDraft,mergeable,author"]
        result = self._run_gh_command(args)
        
        try:
            data = json.loads(result.stdout)
            # 'pr status' returns an object with 'pullRequests' key
            prs_data = data.get("pullRequests", [])
            return [GitHubPR(**pr) for pr in prs_data]
        except (json.JSONDecodeError, AttributeError, KeyError) as e:
            logger.error(f"Failed to parse GitHub PR status: {e}")
            raise GitHubServiceError(f"Failed to parse GitHub PR status: {str(e)}")

    def pr_create(self, repo: str, title: str, body: str, base: str = "main", head: str = "") -> str:
        """Create a new Pull Request and return the URL."""
        title = self.sanitize_input(title)
        body = self.sanitize_input(body)
        
        args = ["pr", "create", "--repo", repo, "--title", title, "--body", body, "--base", base]
        if head:
            args.extend(["--head", head])
            
        result = self._run_gh_command(args)
        url = result.stdout.strip()
        if url.startswith("http"):
            return url
        raise GitHubServiceError(f"Unexpected output from PR creation: {url}")

    def list_repos(self, owner: str = "", limit: int = 30) -> List[GitHubRepo]:
        """List repositories for the authenticated user or a specified owner."""
        args = ["repo", "list"]
        if owner:
            args.append(owner)
        args.extend(["--limit", str(limit), "--json", "nameWithOwner,description,url,stargazerCount"])
        result = self._run_gh_command(args)

        try:
            data = json.loads(result.stdout)
            return [GitHubRepo(**repo) for repo in data]
        except (json.JSONDecodeError, AttributeError, KeyError) as e:
            raise GitHubServiceError(f"Failed to parse repos list: {str(e)}")

    def get_repo_info(self, repo: str) -> GitHubRepo:
        """Get repository information."""
        args = ["repo", "view", repo, "--json", "nameWithOwner,description,url,stargazerCount"]
        result = self._run_gh_command(args)
        
        try:
            data = json.loads(result.stdout)
            return GitHubRepo(**data)
        except json.JSONDecodeError:
            raise GitHubServiceError("Failed to parse Repository info.")

    # --- Git Operations via Shell (subprocess) ---
    
    def _run_git_command(self, args: List[str]) -> str:
        """รันคำสั่ง git โดยตรงใน workspace"""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            raise GitHubServiceError(f"Git error: {e.stderr.strip()}")

    def git_status(self) -> str:
        """ตรวจสอบสถานะไฟล์ในเครื่อง"""
        return self._run_git_command(["status", "--short"])

    def git_add(self, path: str = ".") -> str:
        """Stage ไฟล์"""
        self._run_git_command(["add", path])
        return f"Files at '{path}' added to staging."

    def git_commit(self, message: str) -> str:
        """บันทึกการเปลี่ยนแปลง"""
        message = self.sanitize_input(message)
        return self._run_git_command(["commit", "-m", message])

    def git_push(self, branch: str = "main") -> str:
        """ส่งข้อมูลขึ้น GitHub"""
        return self._run_git_command(["push", "origin", branch])

    def get_local_git_history(self, project_path: str, limit: int = 5) -> str:
        """Get recent git history from a local project path."""
        normalized_path = os.path.abspath(os.path.expanduser(project_path))
        try:
            return self._run_git_command(["-C", normalized_path, "log", f"-n{limit}", "--oneline"])
        except Exception:
            return ""

    def get_local_luma_state(self, project_path: str) -> dict:
        """Read .luma_state.json from a local project path."""
        normalized_path = os.path.abspath(os.path.expanduser(project_path))
        luma_path = os.path.join(normalized_path, ".luma_state.json")
        if not os.path.isfile(luma_path):
            return {}
        try:
            with open(luma_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
