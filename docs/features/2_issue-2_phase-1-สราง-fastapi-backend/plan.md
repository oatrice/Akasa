# Implementation Plan: [Phase 1] FastAPI Backend Foundation

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Ready for Dev

## 1. Architecture & Design
*High-level technical approach.*

This task involves scaffolding a new FastAPI application inside an `app/` directory. It will be the core of the Akasa backend. The initial implementation will be minimal, containing only a single health check endpoint to verify that the service is running. This lays the groundwork for future feature development.

### Component View
- **New Components**:
    - `app/`: A new directory to house all backend application code.
    - `app/main.py`: The main entry point for the FastAPI application.
    - `tests/test_main.py`: A new test file for the backend's core functionality.
- **Modified Components**:
    - `requirements.txt`: Will be updated to include backend-specific dependencies.
- **Dependencies**:
    - `fastapi`: The core web framework.
    - `uvicorn[standard]`: The ASGI server to run the application.
    - `httpx`: Required by `TestClient` for testing the application.

### Data Model Changes
```python
# No data model or database schema changes are required for this task.
```

---

## 2. Step-by-Step Implementation

### Step 1: Setup Project Dependencies and Structure

- **Code**:
    1.  **Create Application Directory**: Create a new directory named `app` in the project root.
    2.  **Create `__init__.py`**: Create an empty file `app/__init__.py` to mark the `app` directory as a Python package.
    3.  **Update `requirements.txt`**: Modify the `requirements.txt` file to include the new dependencies for the backend.
        ```diff
        requests
        python-dotenv
        pytest
        responses
        +fastapi
        +uvicorn[standard]
        +httpx
        ```
- **Verification**:
    - Run `pip install -r requirements.txt`. The command should execute without errors, installing `fastapi`, `uvicorn`, and `httpx`.
    - The `app/` directory and `app/__init__.py` file should exist in the project structure.

### Step 2: Create FastAPI Application with Health Endpoint

- **Code**:
    1.  **Create `main.py`**: Create a new file `app/main.py`.
    2.  **Implement Application**: Add the following code to `app/main.py` to create a basic FastAPI app with a `/health` route.
        ```python
        from fastapi import FastAPI
        from typing import Dict

        app = FastAPI(
            title="Akasa API",
            version="0.1.0",
        )

        @app.get("/health", tags=["Monitoring"])
        def health_check() -> Dict[str, str]:
            """
            Endpoint to verify that the service is running.
            """
            return {"status": "ok"}
        ```
- **Verification**:
    - From the project's root directory, run the command `uvicorn app.main:app --reload`. The server should start successfully on `http://127.0.0.1:8000`.

### Step 3: Implement Unit Tests for the API

- **Code**:
    1.  **Create `test_main.py`**: Create a new test file `tests/test_main.py`.
    2.  **Add Test Cases**: Add tests to verify the `health_check` endpoint and error handling for non-existent routes.
        ```python
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)


        def test_health_check_success():
            """
            Tests that the /health endpoint returns a 200 OK status and correct JSON.
            """
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


        def test_route_not_found():
            """
            Tests that accessing a non-existent route returns a 404 Not Found error.
            """
            response = client.get("/this-route-does-not-exist")
            assert response.status_code == 404
            assert response.json() == {"detail": "Not Found"}

        
        def test_method_not_allowed():
            """
            Tests that using an incorrect HTTP method on an existing route returns 405.
            """
            response = client.post("/health")
            assert response.status_code == 405
            assert response.json() == {"detail": "Method Not Allowed"}
        ```
- **Verification**:
    - Run `pytest`. The tests within `tests/test_main.py` should all pass successfully.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**: Run `pytest` from the project root. All tests in `tests/test_main.py` must pass.

### Manual Verification
- [ ] **Start the server**: Run `uvicorn app.main:app --port 8000` from the project root. The server should start without errors.
- [ ] **Check Health Endpoint**: Open a new terminal and run `curl http://127.0.0.1:8000/health`. The expected output is `{"status":"ok"}`.
- [ ] **Check Not Found Endpoint**: Run `curl -i http://127.0.0.1:8000/invalid-path`. The response header should include `HTTP/1.1 404 Not Found`.
- [ ] **Check Swagger UI**: Open a web browser to `http://127.0.0.1:8000/docs`. The auto-generated API documentation should be visible.