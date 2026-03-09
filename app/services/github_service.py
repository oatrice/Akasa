import subprocess
import json
import os
import re
from typing import List, Optional
from app.config import settings
from app.models.github import GitHubIssue, GitHubPR, GitHubRepo
import logging

logger = logging.getLogger(__name__)

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

    def sanitize_input(self, text: str) -> str:
        """Basic sanitization to prevent command injection characters."""
        if not text:
            return ""
        return re.sub(r'[;&|`$]', '', text)

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
                if "could not find repository" in stderr or "404" in stderr:
                    raise GitHubServiceError(f"Repository not found: {result.stderr.strip()}")
                
                raise GitHubServiceError(f"GitHub CLI error: {result.stderr.strip()}")
                
            return result
        except Exception as e:
            if not isinstance(e, GitHubServiceError):
                logger.exception("Unexpected error running gh command")
                raise GitHubServiceError(f"Unexpected error: {str(e)}")
            raise

    def list_issues(self, repo: str, limit: int = 10) -> List[GitHubIssue]:
        """List issues for a specific repository."""
        args = ["issue", "list", "--repo", repo, "--limit", str(limit), "--json", "number,title,state,url,author"]
        result = self._run_gh_command(args)
        
        try:
            data = json.loads(result.stdout)
            return [GitHubIssue(**issue) for issue in data]
        except json.JSONDecodeError:
            raise GitHubServiceError("Failed to parse GitHub CLI output as JSON.")

    def create_issue(self, repo: str, title: str, body: str) -> str:
        """Create a new issue and return the URL."""
        title = self.sanitize_input(title)
        body = self.sanitize_input(body)
        
        args = ["issue", "create", "--repo", repo, "--title", title, "--body", body]
        result = self._run_gh_command(args)
        
        url = result.stdout.strip()
        if url.startswith("http"):
            return url
        raise GitHubServiceError(f"Unexpected output from issue creation: {url}")

    def get_pr_status(self, repo: str) -> List[GitHubPR]:
        """Get the status of PRs in a repository."""
        args = ["pr", "status", "--repo", repo, "--json", "number,title,state,url,isDraft,mergeable"]
        result = self._run_gh_command(args)
        
        try:
            data = json.loads(result.stdout)
            prs = data.get("pullRequests", [])
            return [GitHubPR(**pr) for pr in prs]
        except (json.JSONDecodeError, AttributeError, KeyError):
            raise GitHubServiceError("Failed to parse GitHub PR status.")

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

    def get_repo_info(self, repo: str) -> GitHubRepo:
        """Get repository information."""
        args = ["repo", "view", repo, "--json", "fullName,description,url,stargazerCount"]
        result = self._run_gh_command(args)
        
        try:
            data = json.loads(result.stdout)
            return GitHubRepo(**data)
        except json.JSONDecodeError:
            raise GitHubServiceError("Failed to parse Repository info.")
