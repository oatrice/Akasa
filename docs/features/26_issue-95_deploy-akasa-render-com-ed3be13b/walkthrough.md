# Walkthrough: Render.com Deployment Setup

We have completed the tasks required to configure Akasa for a one-click deployment to Render.com using Blueprint specs.

## Changes Made

### 1. Created Render Blueprint Configuration
* Created [render.yaml](file:///Users/oatrice/Software%20Project/Akasa/render.yaml) at the project root defining the web service, python version, build command (`pip install -r requirements.txt`), startup command (`uvicorn app.main:app`), and production environment variables.

### 2. Added Dynamic Redis Fallback
* Modified [redis_service.py](file:///Users/oatrice/Software%20Project/Akasa/app/services/redis_service.py) and [local_tool_daemon.py](file:///Users/oatrice/Software%20Project/Akasa/scripts/local_tool_daemon.py) to dynamically attempt a connection to the configured Redis instance. If unreachable, it transparently falls back to `fakeredis` (in-memory) instead of crashing on startup. This allows Akasa to run successfully out-of-the-box on Render.com without necessitating a paid Redis instance immediately.

### 3. Pushed Changes to GitLab
* Committed and successfully pushed the changes to the GitLab remote repository `oatricedev/Akasa`.

## How to Deploy on Render

1. Log into your [Render.com Dashboard](https://dashboard.render.com).
2. Click **New** -> **Blueprint**.
3. Select your `oatricedev/Akasa` repository.
4. Render will automatically parse the `render.yaml` file.
5. In the variables section, configure `TELEGRAM_BOT_TOKEN`.
6. Click **Apply** to deploy the services.
