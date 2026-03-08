# Changelog

## [0.8.0](https://github.com/oatrice/Akasa/compare/v0.7.0...v0.8.0) (2026-03-08)


### Features

* [Phase 1] ส่งข้อความ ➡️ LLM ➡️ ตอบกลับ... ([1b13667](https://github.com/oatrice/Akasa/commit/1b13667bbc21b285f3dda3220735019e27a15ea5))
* [Phase 1] ส่งข้อความ ➡️ LLM ➡️ ตอบกลับ... ([b432ef7](https://github.com/oatrice/Akasa/commit/b432ef7ea163fb96d9886b1fee45cf9de7364d94))
* [Phase 1] สมัคร OpenRouter + ทดสอบ API... ([d0595fb](https://github.com/oatrice/Akasa/commit/d0595fb1e3d2a121ab7defd4d86b0871ec5e784f))
* [Phase 1] สมัคร OpenRouter + ทดสอบ API... ([f26ac69](https://github.com/oatrice/Akasa/commit/f26ac698dca40cb4288e0af2fa090acd1b80ee0f))
* [Phase 1] สร้าง FastAPI backend... ([28446dd](https://github.com/oatrice/Akasa/commit/28446dda77d1854b9d7d17d27c2e9c51bae7fbb9))
* [Phase 1] สร้าง FastAPI backend... ([5ec0699](https://github.com/oatrice/Akasa/commit/5ec0699db16d701be89ad91bfe497a9058637f89))
* [Phase 1] สร้าง Telegram Bot + Webhook ([505875d](https://github.com/oatrice/Akasa/commit/505875d5c619c46aa33535b7530154be0127a684))
* [Phase 2] Code formatting ใน chat... ([3b99a98](https://github.com/oatrice/Akasa/commit/3b99a98ff3de8c6bf0d4cd498c3681f8819d2720))
* [Phase 2] Code formatting ใน chat... ([cbcc2cf](https://github.com/oatrice/Akasa/commit/cbcc2cfd53e91606b68fc044310dd1416b41e383))
* [Phase 2] Conversation history (Redis)... ([dc975a6](https://github.com/oatrice/Akasa/commit/dc975a6930595f79927fd8ee29541d2e78cce086))
* [Phase 2] Conversation history (Redis)... ([cfb5fe2](https://github.com/oatrice/Akasa/commit/cfb5fe27e8f885a4e886f0421dd48390eec5d3ee))
* [Phase 2] System prompt สำหรับ coding assistant (#... ([0773b5d](https://github.com/oatrice/Akasa/commit/0773b5dd8e17a132f1d3389a1b5c0db8160b8f10))
* [Phase 2] System prompt สำหรับ coding assistant (#... ([5909114](https://github.com/oatrice/Akasa/commit/59091144815c3671bd3753d28f79eb5e684d57fc))
* [Phase 4] Multi-model selection... ([#27](https://github.com/oatrice/Akasa/issues/27)) ([b1cb4ca](https://github.com/oatrice/Akasa/commit/b1cb4ca799ac4c804d088634abc7d4ac6ae336cb))
* add local dev setup script, enhance debugging, and upgrade LLM ([ab3267b](https://github.com/oatrice/Akasa/commit/ab3267b8e3f160593abf15a65faf3cc034ddf50b))
* add local dev setup script, enhance debugging, and upgrade LLM ([f7be4ad](https://github.com/oatrice/Akasa/commit/f7be4ad483568a6581037d2f0af9bada7f006c2d))
* add MarkdownV2 formatting support for Telegram bot ([93ed8e1](https://github.com/oatrice/Akasa/commit/93ed8e1361f4c54d4757d82303a0e7271cc32eae))
* add OpenRouter response validation and error tests ([8bad6a4](https://github.com/oatrice/Akasa/commit/8bad6a492a345397ae3a445ff501e0c9eddcb806))
* add Redis-backed conversation memory with fault tolerance ([c80f8ae](https://github.com/oatrice/Akasa/commit/c80f8ae0fd0f71b7cfff87457b3f97358727f628))
* add Telegram bot webhook integration with configuration management ([35d24e9](https://github.com/oatrice/Akasa/commit/35d24e9e4cc8258d3d3ce78497e99782d7320afd))
* **chat:** add Redis-backed chat history with graceful degradation ([6f4ddad](https://github.com/oatrice/Akasa/commit/6f4ddaddd2a244ecebf8766fda1e561736e22538))
* **chat:** append build info footer in local development mode ([ac5423a](https://github.com/oatrice/Akasa/commit/ac5423ad084acb084e371b16ff167f31730019c7))
* **chat:** prepend system prompt to LLM context ([11bb269](https://github.com/oatrice/Akasa/commit/11bb269342bf57dee2762d5c1ee06be27640de47))
* implement async chat processing with OpenRouter LLM integration ([dc60a99](https://github.com/oatrice/Akasa/commit/dc60a99485e83c2ff2bd49c76ad6e4ff3c74d653))
* **issue-2:** implement phase 1 fastapi backend foundation with TDD ([a325cfc](https://github.com/oatrice/Akasa/commit/a325cfc963cbbd870180f1cdc50f47acf2719d0f))
* restrict AI to coding topics and add env to build info ([f52e9d1](https://github.com/oatrice/Akasa/commit/f52e9d120de8d224df7fc63598a8f2c64f2c6165))
* **telegram:** add MarkdownV2 support with proper text escaping ([79f20d4](https://github.com/oatrice/Akasa/commit/79f20d482ace06ca65860019fd9ec6991ba9352d))


### Bug Fixes

* **chat_service:** correct VERSION file path resolution ([2eb3e90](https://github.com/oatrice/Akasa/commit/2eb3e9014231c71e65787dec58aad93553faeca6))
* resolve CI failures - remove duplicate test files, add pytest-asyncio and respx to requirements, add pyproject.toml ([32b3d32](https://github.com/oatrice/Akasa/commit/32b3d32253ed26cac387cfd3bf2337866b92e250))
* resolve CI failures - remove duplicate test files, add pytest-asyncio and respx to requirements, add pyproject.toml ([4af150f](https://github.com/oatrice/Akasa/commit/4af150fe60669b8e4584cb7e703da7ead0bec77e))
* **telegram:** prevent auth bypass with empty webhook secret token ([0d0151f](https://github.com/oatrice/Akasa/commit/0d0151fab03eb44f28205eb524f278be72e3e247))

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
