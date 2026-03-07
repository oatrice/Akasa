# PR Draft Prompt

You are an AI assistant helping to create a Pull Request description.
    
TASK: [Phase 1] สมัคร OpenRouter + ทดสอบ API
ISSUE: {
  "title": "[Phase 1] \u0e2a\u0e21\u0e31\u0e04\u0e23 OpenRouter + \u0e17\u0e14\u0e2a\u0e2d\u0e1a API",
  "number": 1,
  "body": "\u0e2a\u0e21\u0e31\u0e04\u0e23 OpenRouter + \u0e44\u0e14\u0e49 API key, \u0e17\u0e14\u0e2a\u0e2d\u0e1a\u0e40\u0e23\u0e35\u0e22\u0e01 LLM \u0e1c\u0e48\u0e32\u0e19 OpenRouter API (free model)\n\n## \ud83e\udde0 AI Brain Context\n- [walkthrough.md.metadata.json](https://raw.githubusercontent.com/oatrice/Akasa/feat/1-openrouter-api-setup/docs/features/1_issue-1_phase-1-\u0e2a\u0e21\u0e04\u0e23-openrouter-\u0e17\u0e14\u0e2a\u0e2d\u0e1a-api/ai_brain/walkthrough.md.metadata.json)\n- [walkthrough.md.resolved](https://raw.githubusercontent.com/oatrice/Akasa/feat/1-openrouter-api-setup/docs/features/1_issue-1_phase-1-\u0e2a\u0e21\u0e04\u0e23-openrouter-\u0e17\u0e14\u0e2a\u0e2d\u0e1a-api/ai_brain/walkthrough.md.resolved)\n- [task.md.resolved.2](https://raw.githubusercontent.com/oatrice/Akasa/feat/1-openrouter-api-setup/docs/features/1_issue-1_phase-1-\u0e2a\u0e21\u0e04\u0e23-openrouter-\u0e17\u0e14\u0e2a\u0e2d\u0e1a-api/ai_brain/task.md.resolved.2)\n- [task.md.metadata.json](https://raw.githubusercontent.com/oatrice/Akasa/feat/1-openrouter-api-setup/docs/features/1_issue-1_phase-1-\u0e2a\u0e21\u0e04\u0e23-openrouter-\u0e17\u0e14\u0e2a\u0e2d\u0e1a-api/ai_brain/task.md.metadata.json)\n- [task.md.resolved.3](https://raw.githubusercontent.com/oatrice/Akasa/feat/1-openrouter-api-setup/docs/features/1_issue-1_phase-1-\u0e2a\u0e21\u0e04\u0e23-openrouter-\u0e17\u0e14\u0e2a\u0e2d\u0e1a-api/ai_brain/task.md.resolved.3)\n- [task.md.resolved](https://raw.githubusercontent.com/oatrice/Akasa/feat/1-openrouter-api-setup/docs/features/1_issue-1_phase-1-\u0e2a\u0e21\u0e04\u0e23-openrouter-\u0e17\u0e14\u0e2a\u0e2d\u0e1a-api/ai_brain/task.md.resolved)\n- [change_default_branch_1772838707180.webp](https://raw.githubusercontent.com/oatrice/Akasa/feat/1-openrouter-api-setup/docs/features/1_issue-1_phase-1-\u0e2a\u0e21\u0e04\u0e23-openrouter-\u0e17\u0e14\u0e2a\u0e2d\u0e1a-api/ai_brain/change_default_branch_1772838707180.webp)\n- [task.md.resolved.1](https://raw.githubusercontent.com/oatrice/Akasa/feat/1-openrouter-api-setup/docs/features/1_issue-1_phase-1-\u0e2a\u0e21\u0e04\u0e23-openrouter-\u0e17\u0e14\u0e2a\u0e2d\u0e1a-api/ai_brain/task.md.resolved.1)\n- [task.md.resolved.0](https://raw.githubusercontent.com/oatrice/Akasa/feat/1-openrouter-api-setup/docs/features/1_issue-1_phase-1-\u0e2a\u0e21\u0e04\u0e23-openrouter-\u0e17\u0e14\u0e2a\u0e2d\u0e1a-api/ai_brain/task.md.resolved.0)\n- [walkthrough.md.resolved.0](https://raw.githubusercontent.com/oatrice/Akasa/feat/1-openrouter-api-setup/docs/features/1_issue-1_phase-1-\u0e2a\u0e21\u0e04\u0e23-openrouter-\u0e17\u0e14\u0e2a\u0e2d\u0e1a-api/ai_brain/walkthrough.md.resolved.0)\n",
  "url": "https://github.com/oatrice/Akasa/issues/1"
}

GIT CONTEXT:
COMMITS:
f26ac69 feat: [Phase 1] สมัคร OpenRouter + ทดสอบ API...
04f5078 docs: sync AI brain artifacts
8bad6a4 feat: add OpenRouter response validation and error tests
0dbade4 docs(phase-1): Add completion docs for OpenRouter API testing
e7c7b60 chore(scripts): switch default OpenRouter model to Gemma 3 4B
f702b23 chore: setup project config with OpenRouter env template and gitignore

STATS:
.env.example                                       |   2 +
 .gitignore                                         |  13 +
 README.md                                          |   4 +-
 .../change_default_branch_1772838707180.webp"      | Bin 0 -> 493614 bytes
 .../ai_brain/luma_failed_prompt_1772835057.md"     | 106 ++++++
 .../ai_brain/task.md"                              |  15 +
 .../ai_brain/task.md.metadata.json"                |   6 +
 .../ai_brain/task.md.resolved"                     |  15 +
 .../ai_brain/task.md.resolved.0"                   |  15 +
 .../ai_brain/task.md.resolved.1"                   |  15 +
 .../ai_brain/task.md.resolved.2"                   |  15 +
 .../ai_brain/task.md.resolved.3"                   |  15 +
 .../ai_brain/walkthrough.md"                       |  32 ++
 .../ai_brain/walkthrough.md.metadata.json"         |   5 +
 .../ai_brain/walkthrough.md.resolved"              |  32 ++
 .../ai_brain/walkthrough.md.resolved.0"            |  32 ++
 .../analysis.md"                                   |  72 ++++
 .../code_review.md"                                |  15 +
 .../plan.md"                                       | 171 ++++++++++
 .../sbe.md"                                        |  56 ++++
 .../spec.md"                                       |  78 +++++
 docs/templates/analysis_template.md                | 244 ++++++++++++++
 docs/templates/bug_report_template.md              |  26 ++
 docs/templates/feature_issue_template.md           |  29 ++
 docs/templates/feature_spec_template.md            | 366 +++++++++++++++++++++
 docs/templates/plan_template.md                    |  55 ++++
 docs/templates/technical_task_template.md          |  21 ++
 requirements.txt                                   |   4 +
 scripts/__init__.py                                |   0
 scripts/test_openrouter.py                         |  74 +++++
 tests/test_openrouter.py                           | 125 +++++++
 31 files changed, 1656 insertions(+), 2 deletions(-)

KEY FILE DIFFS:
diff --git a/scripts/__init__.py b/scripts/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/scripts/test_openrouter.py b/scripts/test_openrouter.py
new file mode 100644
index 0000000..28c1bbe
--- /dev/null
+++ b/scripts/test_openrouter.py
@@ -0,0 +1,74 @@
+import os
+import requests
+import json
+from dotenv import load_dotenv
+
+def call_openrouter_api(prompt: str, model: str = "google/gemma-3-4b-it:free") -> dict:
+    """
+    Calls the OpenRouter API with a given prompt and model.
+    """
+    # Load environment variables
+    load_dotenv()
+    
+    api_key = os.getenv("OPENROUTER_API_KEY")
+    if not api_key:
+        raise ValueError("Error: OPENROUTER_API_KEY not found in environment variables.")
+
+    api_url = "https://openrouter.ai/api/v1/chat/completions"
+    
+    headers = {
+        "Authorization": f"Bearer {api_key}",
+        "Content-Type": "application/json"
+    }
+
+    data = {
+        "model": model,
+        "messages": [{"role": "user", "content": prompt}]
+    }
+    
+    response = requests.post(api_url, headers=headers, json=data)
+    
+    # Raise an exception for bad status codes
+    response.raise_for_status()
+    
+    result = response.json()
+    
+    # Validate response structure
+    choices = result.get("choices")
+    if not choices or not isinstance(choices, list) or len(choices) == 0:
+        raise ValueError("Invalid API response: 'choices' is empty or missing.")
+    
+    return result
+
+def main():
+    try:
+        model = "google/gemma-3-4b-it:free"
+        prompt = "What are the top 3 benefits of using Python?"
+        print(f"Sending request to model: {model}...")
+        
+        response_json = call_openrouter_api(prompt, model)
+        ai_message = response_json['choices'][0]['message']['content']
+        
+        print("\n--- API Call Successful ---")
+        print("Status Code: 200")
+        print("\nAI Response:")
+        print(ai_message)
+        print("\n--------------------------\n")
+        
+    except requests.exceptions.HTTPError as http_err:
+        print(f"\n--- API Call Failed ---")
+        print(f"HTTP Error: {http_err}")
+        try:
+            # Try to print the detailed JSON error response
+            print("Response Body:")
+            print(json.dumps(http_err.response.json(), indent=2))
+        except ValueError:
+            print("Response Body:")
+            print(http_err.response.text)
+        print("\n-----------------------\n")
+        
+    except Exception as e:
+        print(f"An unexpected error occurred: {e}")
+
+if __name__ == "__main__":
+    main()
diff --git a/tests/test_openrouter.py b/tests/test_openrouter.py
new file mode 100644
index 0000000..8995e20
--- /dev/null
+++ b/tests/test_openrouter.py
@@ -0,0 +1,125 @@
+import os
+import pytest
+import responses
+from unittest.mock import patch
+import sys
+
+# Add the project root to sys.path so we can import from scripts
+sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
+
+# We will import the function to test from scripts.test_openrouter
+# For TDD, this import will initially fail until we create the file
+from scripts.test_openrouter import call_openrouter_api
+
+@responses.activate
+def test_call_openrouter_api_success():
+    # 1. Setup mock response
+    api_key = "test_valid_key"
+    os.environ["OPENROUTER_API_KEY"] = api_key
+    
+    expected_response = {
+        "id": "gen-12345",
+        "model": "mistralai/mistral-7b-instruct:free",
+        "choices": [
+            {
+                "message": {
+                    "role": "assistant",
+                    "content": "2"
+                }
+            }
+        ]
+    }
+    
+    responses.add(
+        responses.POST,
+        "https://openrouter.ai/api/v1/chat/completions",
+        json=expected_response,
+        status=200
+    )
+    
+    # 2. Execute
+    # We will test a function call_openrouter_api(prompt, model)
+    result = call_openrouter_api(prompt="What is 1+1?", model="mistralai/mistral-7b-instruct:free")
+    
+    # 3. Assert
+    assert result is not None
+    assert result["choices"][0]["message"]["content"] == "2"
+    
+    # Verify request headers
+    assert len(responses.calls) == 1
+    request = responses.calls[0].request
+    assert request.headers["Authorization"] == f"Bearer {api_key}"
+    assert request.headers["Content-Type"] == "application/json"
+
+@responses.activate
+def test_call_openrouter_api_unauthorized():
+    # 1. Setup mock response for invalid key
+    os.environ["OPENROUTER_API_KEY"] = "invalid_key"
+    
+    error_response = {
+        "error": {
+            "message": "Incorrect API key provided...",
+            "type": "invalid_request_error",
+            "code": "invalid_api_key"
+        }
+    }
+    
+    responses.add(
+        responses.POST,
+        "https://openrouter.ai/api/v1/chat/completions",
+        json=error_response,
+        status=401
+    )
+    
+    # 2. Execute & Assert
+    with pytest.raises(Exception) as exc_info:
+        call_openrouter_api(prompt="Test prompt", model="mistralai/mistral-7b-instruct:free")
+        
+    assert "401" in str(exc_info.value)
+
+def test_call_openrouter_api_missing_key():
+    """Test that ValueError is raised when API key is not set."""
+    # Remove the key from environment
+    os.environ.pop("OPENROUTER_API_KEY", None)
+    
+    # Patch load_dotenv to prevent loading real .env file
+    with patch("scripts.test_openrouter.load_dotenv"):
+        with pytest.raises(ValueError) as exc_info:
+            call_openrouter_api(prompt="Test prompt")
+    
+    assert "OPENROUTER_API_KEY" in str(exc_info.value)
+
+@responses.activate
+def test_call_openrouter_api_server_error():
+    """Test that server errors (500/503) are handled correctly."""
+    os.environ["OPENROUTER_API_KEY"] = "test_key"
+    
+    responses.add(
+        responses.POST,
+        "https://openrouter.ai/api/v1/chat/completions",
+        json={"error": {"message": "Internal Server Error"}},
+        status=500
+    )
+    
+    with pytest.raises(Exception) as exc_info:
+        call_openrouter_api(prompt="Test prompt")
+    
+    assert "500" in str(exc_info.value)
+
+@responses.activate
+def test_call_openrouter_api_malformed_response():
+    """Test that malformed JSON (empty choices) raises ValueError, not IndexError."""
+    os.environ["OPENROUTER_API_KEY"] = "test_key"
+    
+    # Response 200 OK but with empty choices list
+    responses.add(
+        responses.POST,
+        "https://openrouter.ai/api/v1/chat/completions",
+        json={"id": "gen-123", "choices": []},
+        status=200
+    )
+    
+    with pytest.raises(ValueError) as exc_info:
+        call_openrouter_api(prompt="Test prompt")
+    
+    assert "choices" in str(exc_info.value).lower() or "response" in str(exc_info.value).lower()


PR TEMPLATE:


INSTRUCTIONS:
1. Generate a comprehensive PR description in Markdown format.
2. If a template is provided, fill it out intelligently.
3. If no template, use a standard structure: Summary, Changes, Impact.
4. Focus on 'Why' and 'What'.
5. Do not include 'Here is the PR description' preamble. Just the body.
6. IMPORTANT: Always use the exact FULL URL for closing issues. You must write `Closes https://github.com/oatrice/Akasa/issues/1`. Do NOT use short syntax (e.g., #123) and do not invent an owner/repo.
