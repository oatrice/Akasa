# Changelog

## [0.3.0] - 2026-03-07

### Added
- **Core Chat Loop**: Implemented the main chat functionality. The bot now processes incoming messages from Telegram, forwards the text to the OpenRouter LLM, and sends the AI-generated reply back to the user.
- **Asynchronous Chat Processing**: Integrated FastAPI's `BackgroundTasks` to handle all external API calls. This ensures the webhook responds to Telegram instantly, preventing timeouts.
- **Service Layer**: Created a new service layer (`ChatService`, `LLMService`, `TelegramService`) to manage business logic, making the architecture more modular and testable.
- **Local Dev Script**: Added a `setup_local_bot.sh` script to automate the process of setting up a local development environment with `ngrok`.
- **Error Handling & Debugging**: Implemented error handling for external API calls and added more detailed logging throughout the chat lifecycle.

### Changed
- **LLM Model**: Upgraded the default LLM from `google/gemma-3-4b-it` to `google/gemma-2-9b-it` for improved performance.
- **Webhook Behavior**: The Telegram webhook endpoint now immediately delegates chat processing to a background task instead of handling it in the request-response cycle.

## [0.2.0] - 2026-03-07

### Added
- **Telegram Webhook Integration**: Implemented a new endpoint (`POST /api/v1/telegram/webhook`) to receive real-time updates from the Telegram Bot API.
- **Webhook Security**: Added validation for the `X-Telegram-Bot-Api-Secret-Token` header on the webhook endpoint to ensure requests originate from Telegram.
- **Configuration Management**: Created a centralized settings module (`app/config.py`) using `pydantic-settings` to load secrets like `TELEGRAM_BOT_TOKEN` and `WEBHOOK_SECRET_TOKEN` from environment variables.
- **Telegram Data Models**: Added Pydantic models (`app/models/telegram.py`) to validate and structure incoming data from the Telegram API.

### Changed
- **Application Startup**: The main FastAPI application (`app/main.py`) now includes the new Telegram router.
- **Dependencies**: Added `pydantic-settings` to `requirements.txt` for improved configuration handling.

## [0.1.0] - 2026-03-07

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
