# Implementation Plan: Antigravity IDE Action Confirmation via Akasa Bot (Telegram)

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
This feature introduces a Master Control Program (MCP) server, a lightweight FastAPI application running locally on the developer's machine. The Antigravity IDE will communicate with this server to request approval for actions. The MCP server then uses the existing Akasa backend infrastructure to send a confirmation request to the user via Telegram and polls for a response.

This approach decouples the IDE from the core Akasa backend, requiring no changes to the IDE's core logic for handling remote approvals, and reuses the existing secure notification and approval workflow.

### Component View
- **Modified Components**:
    - `app/models/agent_state.py`: To add `'antigravity'` as a valid source for action requests.
    - `app/services/telegram_service.py`: To correctly format the source name in the Telegram message ("Antigravity IDE").
    - `tests/services/test_telegram_service_confirmation.py`: To add test cases for the new `'antigravity'` source.
- **New Components**:
    - `scripts/akasa_mcp_server.py`: A new FastAPI-based server that listens for approval requests from the Antigravity IDE, communicates with the main Akasa backend, and returns the user's decision.
    - `tests/scripts/test_akasa_mcp_server.py`: Unit tests for the new MCP server.
- **Dependencies**:
    - `fastapi`: To build the MCP server.
    - `uvicorn`: To run the MCP server.
    - `httpx`: For the MCP server to make asynchronous HTTP requests to the Akasa backend.

### Data Model Changes
```python
# In app/models/agent_state.py

from typing import Literal, Optional
from pydantic import BaseModel, Field

# Modify ActionRequestSource to include 'antigravity'
ActionRequestSource = Literal["gemini-cli", "antigravity"]

class ActionRequest(BaseModel):
    """Model for requesting an action confirmation."""
    action_id: str = Field(..., description="Unique identifier for the action.")
    chat_id: str = Field(..., description="The chat ID to which the confirmation should be sent.")
    source: ActionRequestSource = Field(..., description="The source of the action request.")
    command: str = Field(..., description="The command to be executed.")
    cwd: Optional[str] = Field(None, description="The working directory for the command.")
    description: Optional[str] = Field(None, description="A description of the action.")

```

---

## 2. Step-by-Step Implementation

### Step 1: Update Backend Models and Services
- **Description**: Extend the existing action request model and Telegram service to recognize and correctly label requests originating from the Antigravity IDE.
- **Code**:
    1.  **`app/models/agent_state.py`**: Modify the `ActionRequestSource` type to `Literal["gemini-cli", "antigravity"]`.
    2.  **`app/services/telegram_service.py`**: In the `_format_confirmation_message` method (or similar), add logic to display "Antigravity IDE" when the `source` is `'antigravity'`.
- **Tests**:
    1.  **`tests/services/test_telegram_service_confirmation.py`**: Add a new test case to verify that a confirmation message for an `action_request` with `source='antigravity'` contains the string "Source: Antigravity IDE".

### Step 2: Create the Akasa MCP Server
- **Description**: Implement a new FastAPI server script that will run locally. This server exposes an endpoint for the Antigravity IDE to call, triggers the approval workflow, and waits for the result.
- **Code**:
    1.  **`scripts/akasa_mcp_server.py`**:
        - Create a new Python script.
        - Use FastAPI to set up a web server.
        - Create a `/request_approval` endpoint that accepts a POST request with the action details (`command`, `cwd`, `description`).
        - The endpoint should generate a unique `action_id`.
        - It will then make a POST request to the main Akasa backend's `/actions/request_approval` endpoint, passing the action details, including `source='antigravity'`. This reuses the existing notification mechanism.
- **Tests**:
    1.  **`tests/scripts/test_akasa_mcp_server.py`**:
        - Create a new test file.
        - Write a test to ensure the `/request_approval` endpoint correctly calls the mocked Akasa backend's `/actions/request_approval` with the right payload (including `source: 'antigravity'`).

### Step 3: Implement Long-Polling for Response
- **Description**: Add long-polling logic to the MCP server to wait for the user's decision from the main Akasa backend.
- **Code**:
    1.  **`scripts/akasa_mcp_server.py`**:
        - After successfully posting to `/actions/request_approval`, the `/request_approval` endpoint will enter a loop.
        - Inside the loop, it will make GET requests to the Akasa backend's `/actions/{action_id}/status` endpoint.
        - The loop will continue until the status is no longer 'pending' or a timeout is reached (e.g., 2 minutes).
        - Once the status is `allowed` or `denied`, the server will return a JSON response to the calling IDE (e.g., `{"status": "allowed"}`).
- **Tests**:
    1.  **`tests/scripts/test_akasa_mcp_server.py`**:
        - Add a test to simulate the polling process where the mocked backend returns 'pending' a few times before returning 'allowed'.
        - Add a test for the 'denied' case.
        - Add a test to verify that the endpoint times out and returns an appropriate error if no decision is made in time.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**:
    - [ ] `tests/services/test_telegram_service_confirmation.py`: Verify correct message formatting for the new source.
    - [ ] `tests/scripts/test_akasa_mcp_server.py`:
        - [ ] Test successful request initiation.
        - [ ] Test successful polling and `allowed` response.
        - [ ] Test successful polling and `denied` response.
        - [ ] Test polling timeout.

### Manual Verification
- [ ] **End-to-End Test**:
    1.  [ ] Run the main Akasa backend application.
    2.  [ ] Run the new MCP server: `uvicorn scripts.akasa_mcp_server:app --port 8123`.
    3.  [ ] Simulate the Antigravity IDE by sending a `curl` request:
        ```bash
        curl -X POST http://localhost:8123/request_approval \
        -H "Content-Type: application/json" \
        -d '{
            "command": "git push --force",
            "cwd": "/path/to/project",
            "description": "Force push to remote repository"
        }'
        ```
    4.  [ ] Verify that a confirmation message appears on the configured Telegram account, clearly stating the command and "Source: Antigravity IDE".
    5.  [ ] Tap the **Allow** button on Telegram.
    6.  [ ] Verify that the `curl` command terminates and prints `{"status":"allowed"}`.
    7.  [ ] Repeat steps 3-5, but tap the **Deny** button.
    8.  [ ] Verify that the `curl` command terminates and prints `{"status":"denied"}`.