import os
import sys

# เพิ่ม root directory เข้าไปใน path เพื่อให้ import app ได้
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.github_service import GitHubService, GitHubServiceError, GitHubAuthError
from app.config import settings

def verify():
    print("🔍 Starting GitHub Service Verification...")
    print(f"🌍 Environment: {settings.ENVIRONMENT}")
    
    if not settings.GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN is not set in .env")
        return

    service = GitHubService()
    
    # ทดสอบดึงข้อมูล Repo
    repo_name = "oatrice/Akasa" # คุณสามารถเปลี่ยนเป็น repo อื่นได้
    print(f"\n1. Testing: get_repo_info('{repo_name}')")
    try:
        repo = service.get_repo_info(repo_name)
        print(f"✅ Success! Full Name: {repo.full_name}")
        print(f"⭐ Stars: {repo.stargazers_count}")
    except GitHubAuthError as e:
        print(f"🔐 Auth Error: {e}")
    except GitHubServiceError as e:
        print(f"❌ Service Error: {e}")
    except Exception as e:
        print(f"⚠️ Unexpected Error: {e}")

    # ทดสอบดึงรายการ Issues
    print(f"\n2. Testing: list_issues('{repo_name}')")
    try:
        issues = service.list_issues(repo_name, limit=5)
        print(f"✅ Success! Found {len(issues)} issues.")
        for issue in issues:
            print(f"  - #{issue.number}: {issue.title}")
    except Exception as e:
        print(f"❌ Failed to list issues: {e}")

if __name__ == "__main__":
    verify()
