# Changelog

## [0.7.0](https://github.com/oatrice/Akasa/compare/v0.6.0...v0.7.0) (2026-03-08)

### Features
- **การรองรับหลายโมเดล**: ผู้ใช้สามารถแสดงรายการและสลับระหว่างโมเดลภาษาขนาดใหญ่ (เช่น GPT-4o, Claude 3 Opus, Gemini 1.5 Pro) ได้ทันทีโดยใช้คำสั่ง `/model` ใหม่ โดยโมเดลที่เลือกจะถูกบันทึกไว้สำหรับการสนทนานั้นๆ
- **ขยายแคตตาล็อกโมเดล**: เพิ่มโมเดลใหม่ๆ เข้ามาในแคตตาล็อก รวมถึงตัวเลือกจาก Deepseek และ Meta (Llama)
- **เพิ่มความเสถียร**: เพิ่มตรรกะการลองใหม่ (retry logic) อัตโนมัติสำหรับการเรียก API ไปยัง OpenRouter เพื่อจัดการกับปัญหาเครือข่ายที่เกิดขึ้นชั่วคราวได้ดีขึ้น
- **การตั้งค่า**: เปลี่ยนชื่อตัวแปรสภาพแวดล้อม `LLM_API_KEY` เป็น `OPENROUTER_API_KEY` เพื่อให้สื่อความหมายชัดเจนขึ้น กรุณาอัปเดตไฟล์ `.env` ของคุณ
- อัปเดตตัวระบุโมเดลและชื่อที่แสดงเพื่อความชัดเจนและสอดคล้องกัน

## [0.6.0](https://github.com/oatrice/Akasa/compare/v0.5.0...v0.6.0) (2026-03-08)

### Features
- **System Prompt**: A system prompt has been added to define the bot's persona as an expert coding assistant. This ensures responses are consistently concise, technical, and focused on software development topics.
- **Development Build Info**: In local development mode, a footer containing the app version and environment is automatically appended to bot messages for easier debugging.
- **Bot Persona**: The bot is now more specialized and will primarily focus on answering coding and software development questions, guided by the new system prompt.
- **Configurability**: The LLM model is now configurable via the `LLM_MODEL` environment variable.

### Bug Fixes
- Corrected a file path resolution issue for the `VERSION` file, ensuring the build information footer can be reliably appended.

## [0.5.0](https://github.com/oatrice/Akasa/compare/v0.4.0...v0.5.0) (2026-03-07)

### Features
- **MarkdownV2 Formatting**: The bot now supports rich text formatting. Code snippets sent in the chat are now automatically displayed in formatted blocks with syntax highlighting.
- A new text escaping utility (`app/utils/markdown_utils.py`) was created to intelligently handle special Markdown characters while preserving the content of code blocks.
- Added comprehensive unit tests for the new Markdown escaping logic to ensure reliability.
- The `TelegramService` now sends all messages using `parse_mode="MarkdownV2"` by default to enable rich formatting.

### Bug Fixes
- Corrected import placement in `telegram_service.py` to adhere to PEP8 standards.

## [0.4.0](https://github.com/oatrice/Akasa/compare/v0.3.0...v0.4.0) (2026-03-07)

### Features
- **Conversation Memory**: Implemented Redis-backed chat history, enabling the bot to remember the context of recent messages and understand follow-up questions.
- **Redis Service**: Created a new, dedicated service (`redis_service.py`) to manage all interactions with Redis, including storing, retrieving, and trimming conversation history to a fixed size.
- **Integration Tests**: Added a new integration testing suite (`tests/integration`) to validate the Redis service against a live Redis instance.
- **Chat Logic**: The `ChatService` has been updated to fetch conversation history from Redis before calling the LLM and to save the new user message and AI reply back to Redis.
- **Fault Tolerance**: The `ChatService` now gracefully degrades to a stateless (memory-less) mode if the Redis service is unavailable, ensuring the bot remains functional.
- **LLM Service**: The `LLMService` now accepts a list of message objects to support conversational context, instead of a single prompt string.
- **CI Pipeline**: The GitHub Actions workflow (`python-tests.yml`) has been updated to spin up a Redis service, allowing integration tests to run in the CI environment.

## [0.3.0](https://github.com/oatrice/Akasa/compare/v0.2.0...v0.3.0) (2026-03-07)

### Features
- **Core Chat Loop**: Implemented the main chat functionality. The bot now processes incoming messages from Telegram, forwards the text to the OpenRouter LLM, and sends the AI-generated reply back to the user.
- **Asynchronous Chat Processing**: Integrated FastAPI's `BackgroundTasks` to handle all external API calls. This ensures the webhook responds to Telegram instantly, preventing timeouts.
- **Service Layer**: Created a new service layer (`ChatService`, `LLMService`, `TelegramService`) to manage business logic, making the architecture more modular and testable.
- **Local Dev Script**: Added a `setup_local_bot.sh` script to automate the process of setting up a local development environment with `ngrok`.
- **Error Handling & Debugging**: Implemented error handling for external API calls and added more detailed logging throughout the chat lifecycle.
- **LLM Model**: Upgraded the default LLM from `google/gemma-3-4b-it` to `google/gemma-2-9b-it` for improved performance.
- **Webhook Behavior**: The Telegram webhook endpoint now immediately delegates chat processing to a background task instead of handling it in the request-response cycle.

## [0.2.0](https://github.com/oatrice/Akasa/compare/v0.1.0...v0.2.0) (2026-03-07)

### Features
- **Telegram Webhook Integration**: Implemented a new endpoint (`POST /api/v1/telegram/webhook`) to receive real-time updates from the Telegram Bot API.
- **Webhook Security**: Added validation for the `X-Telegram-Bot-Api-Secret-Token` header on the webhook endpoint to ensure requests originate from Telegram.
- **Configuration Management**: Created a centralized settings module (`app/config.py`) using `pydantic-settings` to load secrets like `TELEGRAM_BOT_TOKEN` and `WEBHOOK_SECRET_TOKEN` from environment variables.
- **Telegram Data Models**: Added Pydantic models (`app/models/telegram.py`) to validate and structure incoming data from the Telegram API.
- **Application Startup**: The main FastAPI application (`app/main.py`) now includes the new Telegram router.
- **Dependencies**: Added `pydantic-settings` to `requirements.txt` for improved configuration handling.

## [0.1.0](https://github.com/oatrice/Akasa/releases/tag/v0.1.0) (2026-03-07)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
