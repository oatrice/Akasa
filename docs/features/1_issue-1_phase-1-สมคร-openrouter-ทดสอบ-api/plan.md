# Implementation Plan: [Phase 1] Test OpenRouter API Connection

| | |
|---|---|
| **Feature Name** | [Phase 1] สมัคร OpenRouter + ทดสอบ API |
| **Issue URL** | [#1](https://github.com/oatrice/Akasa/issues/1) |
| **Status** | **Ready for Dev** |
| **Date** | 2026-03-07 |

---

## 1. Objective

To create a standalone Python script that validates the connectivity and authentication with the OpenRouter API. This script will serve as a technical proof-of-concept, ensuring the `OPENROUTER_API_KEY` is correctly used to fetch a response from a free-tier language model.

## 2. Prerequisites

- Python 3.8+ installed.
- A valid `OPENROUTER_API_KEY` obtained from [openrouter.ai](https://openrouter.ai).

## 3. Technical Implementation Steps

### Step 1: Project Setup

**Task:** Prepare the environment by creating necessary files for managing dependencies and environment variables.

1.  **Create `requirements.txt`:**
    *   **File:** `requirements.txt` (New)
    *   **Content:**
        ```
        requests
        python-dotenv
        ```
2.  **Create `.env.example`:**
    *   **File:** `.env.example` (New)
    *   **Content:**
        ```
        # OpenRouter API Key
        OPENROUTER_API_KEY="your_api_key_here"
        ```
3.  **Update `.gitignore`:**
    *   **File:** `.gitignore` (Modify)
    *   **Action:** Add the following lines to prevent committing secrets and environment-specific files.
        ```
        # Environment variables
        .env

        # Python cache
        __pycache__/
        *.pyc
        ```

**Verification:**
*   Run `pip install -r requirements.txt`. The `requests` and `python-dotenv` libraries should be installed without errors.
*   The `.env.example` file should exist, and the `.gitignore` file should contain `.env`.

### Step 2: Create the API Test Script

**Task:** Develop the Python script that will perform the API call.

1.  **Create Script Directory:**
    *   **Action:** Create a new directory named `scripts`.
2.  **Create Script File:**
    *   **File:** `scripts/test_openrouter.py` (New)
    *   **Content:** Implement the full logic as described below.

    ```python
    import os
    import requests
    import json
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    # 1. Get API Key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in .env file.")
        exit()

    # 2. Prepare API Request
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    MODEL = "mistralai/mistral-7b-instruct:free"
    PROMPT = "What are the top 3 benefits of using Python?"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}]
    }

    print(f"Sending request to model: {MODEL}...")

    try:
        # 3. Send Request and Handle Response
        response = requests.post(API_URL, headers=headers, json=data)

        # Check for non-200 status codes
        response.raise_for_status()

        # 4. Process Successful Response
        response_json = response.json()
        ai_message = response_json['choices'][0]['message']['content']

        print("\n--- API Call Successful ---")
        print(f"Status Code: {response.status_code}")
        print("\nAI Response:")
        print(ai_message)
        print("\n--------------------------\n")

    except requests.exceptions.HTTPError as http_err:
        # Handle HTTP errors (e.g., 401, 404, etc.)
        print(f"\n--- API Call Failed ---")
        print(f"HTTP Error: {http_err}")
        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        try:
            print(json.dumps(response.json(), indent=2))
        except json.JSONDecodeError:
            print(response.text)
        print("\n-----------------------\n")

    except Exception as e:
        # Handle other errors (network, etc.)
        print(f"An unexpected error occurred: {e}")

    ```

**Verification:**
*   The file `scripts/test_openrouter.py` exists and contains the code above.
*   The script logic correctly reads the API key, constructs the request, sends it, and handles both success and error cases.

### Step 3: Execution and Testing

**Task:** Run the script to verify its functionality against the acceptance criteria.

1.  **Create `.env` file:**
    *   Copy `.env.example` to a new file named `.env`.
    *   Replace `"your_api_key_here"` with your actual, valid OpenRouter API key.

2.  **Test Case 1: Happy Path (Valid Key)**
    *   **Action:** Run the script from the root directory: `python scripts/test_openrouter.py`
    *   **Expected Outcome:**
        *   The console prints "API Call Successful".
        *   Status code is 200.
        *   An AI-generated response answering the prompt is displayed.

3.  **Test Case 2: Error Handling (Invalid Key)**
    *   **Action:**
        1.  Edit the `.env` file and change `OPENROUTER_API_KEY` to an incorrect value (e.g., `sk-or-invalid123`).
        2.  Run the script again: `python scripts/test_openrouter.py`
    *   **Expected Outcome:**
        *   The console prints "API Call Failed".
        *   The status code is `401`.
        *   The response body shows an error message like `"Incorrect API key provided..."`.

## 4. File Manifest

*   **New Files:**
    *   `requirements.txt`
    *   `.env.example`
    *   `scripts/test_openrouter.py`
*   **Modified Files:**
    *   `.gitignore`

[SYSTEM] Gemini CLI failed to process the request. The prompt has been saved to: /Users/oatrice/Software-projects/Akasa/docs/features/1_issue-1_phase-1-สมคร-openrouter-ทดสอบ-api/ai_brain/luma_failed_prompt_1772835057.md. Please use an external AI to process it.