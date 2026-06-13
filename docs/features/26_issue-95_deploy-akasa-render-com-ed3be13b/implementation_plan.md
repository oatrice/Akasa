# Deploy Akasa to Render.com

This plan outlines the steps to deploy the Akasa FastAPI backend to Render.com using a `render.yaml` Blueprint specification. This allows for a structured, repeatable, and one-click deployment.

## User Review Required

> [!IMPORTANT]
> **Redis Option:** By default, the app will use our newly added dynamic `fakeredis` fallback (in-memory) if a Redis service is not bound. For production persistence (to save Telegram chat history/agent state across redeploys), we recommend linking a Redis service. The `render.yaml` proposed below leaves this optional but configurable.

> [!WARNING]
> **Environment Variables:** You will need to manually configure `TELEGRAM_BOT_TOKEN` in the Render dashboard after the initial deployment configuration, as it is a sensitive credential.

## Proposed Changes

### [Deployment Configuration]

We will create a `render.yaml` file at the root of the project to define the Render Web Service.

#### [NEW] [render.yaml](file:///Users/oatrice/Software%20Project/Akasa/render.yaml)
Create a Render Blueprint configuration specifying the Python environment, build command, start command, and necessary environment variables.

```yaml
services:
  - type: web
    name: akasa-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: PYTHON_VERSION
        value: 3.9.6 # Matching local python version; can be upgraded to 3.12+ if desired
      - key: AKASA_API_KEY
        generateValue: true
      - key: WEBHOOK_SECRET_TOKEN
        generateValue: true
      - key: TELEGRAM_BOT_TOKEN
        sync: false # Must be entered manually in Render dashboard
      - key: REDIS_URL
        value: "" # Empty value triggers the dynamic fakeredis fallback
```

## Verification Plan

### Manual Verification
1. Push the `render.yaml` to the GitLab repository.
2. Link the repository to Render.com and apply the blueprint.
3. Configure `TELEGRAM_BOT_TOKEN` in the Render environment variables dashboard.
4. Verify the deployment succeeds and the backend `/health` endpoint returns `{"status":"ok"}`.
5. Verify the webhook URL can be configured on Telegram.
