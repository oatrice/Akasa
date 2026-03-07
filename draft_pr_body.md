## 🎯 [Phase 1] สมัคร OpenRouter + ทดสอบ API

Closes https://github.com/oatrice/Akasa/issues/1

### 📝 Summary

This PR introduces the foundational step for the Akasa project by establishing a connection to the **OpenRouter API**. It serves as a technical proof-of-concept to ensure we can successfully authenticate and interact with a free-tier Large Language Model (LLM).

This work was developed following a strict Test-Driven Development (TDD) cycle, starting with failing tests and progressively implementing the code to make them pass.

### ✨ Changes Implemented

1.  **Project Configuration:**
    *   Added `.env.example` to define the required `OPENROUTER_API_KEY` environment variable.
    *   Updated `.gitignore` to secure the `.env` file and exclude Python cache directories.
    *   Created `requirements.txt` with necessary dependencies: `requests`, `python-dotenv`, `pytest`, and `responses`.

2.  **API Test Script (`scripts/test_openrouter.py`):**
    *   A standalone Python script to test the OpenRouter connection.
    *   It securely loads the API key from environment variables.
    *   Sends a request to a free model (`google/gemma-3-4b-it:free`) and prints the AI's response upon success.
    *   Includes robust error handling for HTTP errors (e.g., 401, 500).

3.  **Comprehensive Unit Tests (`tests/test_openrouter.py`):**
    *   A full test suite for the `call_openrouter_api` function using `pytest` and the `responses` library for mocking.
    *   **Test coverage includes:**
        *   ✅ Happy Path (Successful API call).
        *   ❌ Unauthorized (Invalid API Key).
        *   ❌ Missing API Key (`ValueError`).
        *   ❌ Server-side errors (HTTP 500).
        *   ❌ Malformed API response (e.g., empty `choices` list).

4.  **Documentation & Process:**
    *   Added detailed planning documents (`analysis.md`, `spec.md`, `plan.md`, `sbe.md`) to formalize the feature development process.
    *   Updated the `README.md` roadmap to mark this task as complete.

### 🧪 How to Manually Verify

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up environment:**
    *   Copy `.env.example` to `.env`.
    *   Add your valid `OPENROUTER_API_KEY` to the `.env` file.

3.  **Run the test script:**
    ```bash
    python scripts/test_openrouter.py
    ```
    *   You should see a successful API response printed to the console.

4.  **Run automated tests:**
    ```bash
    pytest
    ```
    *   All tests should pass.