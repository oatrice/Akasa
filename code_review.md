# Luma Code Review Report

**Date:** 2026-03-10 10:44:58
**Files Reviewed:** ['app/services/llm_service.py', 'app/services/github_service.py', '.gitignore', 'docs/features/14_issue-32_feature-define-github-function-calling-for-chatservice/plan.md', 'docs/features/14_issue-32_feature-define-github-function-calling-for-chatservice/analysis.md', 'tests/services/test_chat_service_tools.py', 'app/services/chat_service.py', 'docs/features/14_issue-32_feature-define-github-function-calling-for-chatservice/spec.md', 'docs/features/14_issue-32_feature-define-github-function-calling-for-chatservice/sbe.md', 'docs/ROADMAP.md', 'app/models/github.py']

## 📝 Reviewer Feedback

In `app/services/chat_service.py`, the `_handle_standard_message` function has a significant logic error related to how chat history is saved after a tool call is executed.

Currently, the implementation only saves the initial user prompt and the final text reply to Redis. It discards the crucial intermediate messages: the assistant's request to use a tool (`tool_calls`) and the result of that tool's execution (`role: "tool"`).

This causes context loss. On the next turn, the LLM has no memory that a tool was used, making follow-up questions impossible.

**The Fix:**

The entire conversational turn, including tool calls and their results, must be persisted to history.

In `app/services/chat_service.py`, the history saving logic at the end of `_handle_standard_message` needs to be changed. Instead of just saving the `prompt` and `reply`, it should save the sequence of messages that were generated.

Here is the corrected logic for the end of the `_handle_standard_message` function:

```python
# In app/services/chat_service.py, replace the final `try...except` block 
# in `_handle_standard_message` with this:

    # 6. ส่งคำตอบกลับหาผู้ใช้
    await _send_response(chat_id, reply)

    # 7. บันทึก user message + tool exchange + assistant reply ลง Redis
    try:
        # Start with the user's message
        messages_to_save = [{"role": "user", "content": prompt}]

        # If the response was a dict, it means tool calls happened.
        # The `messages` list contains the assistant's tool_call request and the tool results.
        # We need to find those messages and add them to our save list.
        if isinstance(response, dict):
            # Find messages appended after the user prompt
            start_index = 0
            for i, msg in enumerate(messages):
                if msg.get("role") == "user" and msg.get("content") == prompt:
                    start_index = i + 1
                    break
            
            if start_index > 0:
                messages_to_save.extend(messages[start_index:])
        
        # Add the final text reply from the assistant
        messages_to_save.append({"role": "assistant", "content": reply})

        # Save each new message to history
        import json
        for msg in messages_to_save:
            # The redis service currently only supports string content. To handle complex
            # messages like tool_calls, we must serialize the content if it's not a simple string.
            # A proper fix would involve updating redis_service to handle JSON directly.
            # This is a workaround:
            content = msg.get("content")
            if not isinstance(content, str) and msg.get("tool_calls"):
                # For assistant message with tool_calls, save the whole message dict as content.
                # The role will be 'assistant'. On retrieval, this would need to be parsed.
                 await redis_service.add_message_to_history(
                     chat_id, 
                     "assistant", 
                     json.dumps({"tool_calls": msg.get("tool_calls")}), 
                     project_name=current_project
                 )
            elif msg.get("role") == "tool":
                 # For tool results, serialize the content.
                 await redis_service.add_message_to_history(
                     chat_id, 
                     "tool", 
                     str(content), # content from tool is already a string
                     project_name=current_project
                 )
            else:
                 await redis_service.add_message_to_history(
                     chat_id, 
                     msg["role"], 
                     content, 
                     project_name=current_project
                 )

    except Exception as e:
        logger.warning(f"Redis add_message_to_history failed for {chat_id} (Project: {current_project}): {e}")

```

**Reasoning for the fix:**

The original code's history saving was incorrect:
`await redis_service.add_message_to_history(chat_id, "user", prompt, ...)`
`await redis_service.add_message_to_history(chat_id, "assistant", reply, ...)`

This only saves the beginning and end of the conversation turn, losing all intermediate context about which tools were called and what their results were.

The corrected code reconstructs the list of messages from the current turn (`messages_to_save`) and iterates through them. It correctly saves the user prompt, the assistant's tool call requests (by serializing the `tool_calls` object to a JSON string), the tool results, and the final assistant reply. This ensures that the chat history in Redis is complete, preserving the full context for future interactions. A proper, long-term solution would require updating `redis_service` to natively handle JSON objects, but this change correctly identifies and fixes the logic error within `chat_service.py` as best as possible.

## 🧪 Test Suggestions

แน่นอนครับ นี่คือคู่มือการตรวจสอบการเปลี่ยนแปลงโค้ดด้วยตนเองครับ

### คู่มือการตรวจสอบการเปลี่ยนแปลงด้วยตนเอง (Manual Verification Guide)

คู่มือนี้จะแนะนำวิธีการทดสอบการเปลี่ยนแปลงใน `GitHubService` บนเครื่องของคุณโดยตรง การทดสอบจะเน้นไปที่การเรียกใช้ฟังก์ชันต่างๆ ของ `gh` CLI ผ่านโค้ด Python เพื่อให้แน่ใจว่าทำงานได้ถูกต้อง

#### ข้อกำหนดเบื้องต้น:

1.  **ติดตั้ง `gh` CLI:** ตรวจสอบให้แน่ใจว่าคุณได้ติดตั้ง `gh` CLI และลงชื่อเข้าใช้บัญชี GitHub ของคุณแล้ว
    ```bash
    gh auth login
    ```
2.  **ตั้งค่า GitHub Token:** โค้ดจำเป็นต้องใช้ `GITHUB_TOKEN` ในการยืนยันตัวตน คุณสามารถตั้งค่าผ่าน environment variable หรือสร้างไฟล์ `.env` ในโปรเจกต์:
    ```
    GITHUB_TOKEN="ghp_your_personal_access_token"
    ```
3.  **เตรียม Repository สำหรับทดสอบ:** คุณต้องมี GitHub repository ที่คุณสามารถใช้ทดสอบการสร้าง issue และ pull request ได้ (เช่น `your-username/test-repo`)
4.  **เปิด Interactive Shell:** เข้าไปใน virtual environment ของโปรเจกต์แล้วเปิด Python interactive shell:
    ```bash
    source venv/bin/activate
    pip install -r requirements.txt
    ipython
    ```

---

#### ขั้นตอนการทดสอบ:

**ขั้นตอนที่ 1: เตรียม Service และข้อมูลทดสอบ**

ใน `ipython` shell ของคุณ, import `GitHubService` และสร้าง instance ขึ้นมา โดยแทนที่ `your-username/your-repo` ด้วย repository ของคุณ

```python
import os
from dotenv import load_dotenv
from app.services.github_service import GitHubService

# โหลด environment variables จากไฟล์ .env (ถ้ามี)
load_dotenv()

# ข้อมูลสำหรับทดสอบ
REPO = "your-username/your-repo" # <-- !! แก้ไขเป็น repo ของคุณ
gh_service = GitHubService(token=os.getenv("GITHUB_TOKEN"))

print("GitHubService is ready.")
```

**ผลลัพธ์ที่คาดหวัง:**
ข้อความ `GitHubService is ready.` จะแสดงขึ้นมาโดยไม่มี error

---

**ขั้นตอนที่ 2: ทดสอบการดึงข้อมูล Issue ที่มีอยู่ (`get_issue`)**

เรียกใช้ `get_issue` เพื่อดึงข้อมูลของ issue ที่มีอยู่แล้วใน repo ของคุณ (แก้ไข `issue_number` ให้ถูกต้อง)

```python
# แก้ไข issue_number เป็น issue ที่มีอยู่จริงใน repo ของคุณ
issue = gh_service.get_issue(repo=REPO, issue_number=1) 
print(issue)
```

**ผลลัพธ์ที่คาดหวัง:**
คุณจะเห็น dictionary ที่มีข้อมูลของ issue นั้นๆ ซึ่งประกอบด้วย `number`, `title`, `body`, และ `url`

---

**ขั้นตอนที่ 3: ทดสอบการแสดงรายการ Issues (`list_issues`)**

เรียกใช้ `list_issues` เพื่อดึงรายการ issue ล่าสุดจาก repo

```python
issues = gh_service.list_issues(repo=REPO, limit=5)
print(issues)
```

**ผลลัพธ์ที่คาดหวัง:**
คุณจะเห็น list ของ dictionaries ซึ่งแต่ละอันคือ issue ที่มีข้อมูล `number`, `title`, `body`, และ `url`

---

**ขั้นตอนที่ 4: ทดสอบการค้นหา Issues (`search_issues`)**

ทดลองค้นหา issue ด้วยคำค้นหาที่ต้องการ

```python
# แก้ไข query ให้ตรงกับ issue ที่คุณต้องการค้นหา
search_results = gh_service.search_issues(query="bug", repo=REPO)
print(search_results)
```

**ผลลัพธ์ที่คาดหวัง:**
คุณจะเห็น list ของ issue dictionaries ที่ตรงกับเงื่อนไขการค้นหา

---

**ขั้นตอนที่ 5: ทดสอบการสร้าง Issue ใหม่ (`create_issue`)**

ทดลองสร้าง issue ใหม่ใน repository ของคุณ

```python
new_issue = gh_service.create_issue(
    repo=REPO,
    title="[Test] Gemini CLI Manual Verification",
    body="This is a test issue created automatically."
)
print(new_issue)
```

**ผลลัพธ์ที่คาดหวัง:**
1.  คุณจะได้รับ dictionary ที่มีข้อมูลของ issue ที่เพิ่งสร้างใหม่ (`number`, `title`, `body`, `url`)
2.  เมื่อเปิด `url` ที่ได้มาในเบราว์เซอร์ คุณจะเห็น issue ใหม่ที่ถูกสร้างขึ้นใน GitHub repository ของคุณจริงๆ

---

**ขั้นตอนที่ 6: ทดสอบการสร้าง Pull Request ใหม่ (`create_pr`)**

ขั้นตอนนี้ซับซ้อนที่สุดและต้องมีการเตรียม branch ก่อน

1.  **เตรียม Branch:**
    *   ใน local project ของคุณ, สร้าง branch ใหม่, ทำการเปลี่ยนแปลงไฟล์เล็กน้อย, commit, และ push ไปยัง GitHub
    ```bash
    git checkout -b test-pr-branch
    echo "# Test change" >> test_file.md
    git add test_file.md
    git commit -m "feat: Add test file for PR verification"
    git push origin test-pr-branch
    ```

2.  **เรียกใช้ `create_pr`:**
    กลับไปที่ `ipython` shell แล้วรันโค้ดเพื่อสร้าง PR (สมมติว่าคุณต้องการ merge `test-pr-branch` เข้า `main`)

    ```python
    new_pr = gh_service.create_pr(
        repo=REPO,
        title="[Test] Gemini PR Verification",
        body="This is a test pull request.",
        head="test-pr-branch", # <-- Branch ที่มี commit ใหม่
        base="main"             # <-- Branch หลักที่ต้องการ merge เข้า
    )
    print(new_pr)
    ```

**ผลลัพธ์ที่คาดหวัง:**
1.  คุณจะได้รับ dictionary ที่มีข้อมูลของ PR ที่เพิ่งสร้าง (`number`, `title`, `body`, `url`)
2.  เมื่อเปิด `url` ที่ได้มาในเบราว์เซอร์ คุณจะเห็น pull request ใหม่ที่ถูกสร้างขึ้นใน GitHub repository ของคุณ

หลังจากทดสอบเสร็จสิ้น คุณสามารถลบ issue, PR, และ branch ที่สร้างขึ้นเพื่อทดสอบได้เลย

