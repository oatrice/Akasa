# 🌌 Akasa — AI Coding Assistant Chatbot

> ผู้ช่วยเขียนโค้ดผ่าน Messaging App — เขียนโค้ดได้ทุกที่ ไม่ต้องอยู่หน้าคอม

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- 🤖 **AI Coding Assistant** — ถามโค้ด, debug, ขอ snippet ผ่านแชท
- 📱 **Remote Dev Workspace** (v0.7.0+) — จัดการ GitHub, สั่ง Build/Deploy, และดู Screenshot จาก Emulator/Simulator ผ่านแชท
- 🔔 **Proactive Notifications** — แจ้งเตือนงาน Long-running tasks หรือข้อความจากระบบภายนอกสู่มือถือทันที
- 💬 **Multi-Platform** — รองรับ Telegram, LINE, WhatsApp
- 📂 **Multi-Project Support** — จัดการและสลับ Context ระหว่างโปรเจ็กต์ด้วยคำสั่ง `/project` พร้อมประวัติแชทที่แยกจากกัน
- 🧠 **Context Memory** — จำบทสนทนาและสถานะการทำงานล่าสุดของแต่ละโปรเจ็กต์ (Agent State) เมื่อสลับกลับมาจะมีการสรุปงานค้างให้
- 📝 **Task Notes** — บันทึก Task ที่กำลังทำอยู่สำหรับโปรเจ็กต์ปัจจุบันด้วยคำสั่ง `/note <your task description>` เพื่อให้บอทจำบริบทได้แม่นยำขึ้น
- 🔌 **Multi-LLM** — สลับโมเดล AI ได้ผ่านคำสั่ง `/model` (GPT-4o, Claude 3, Gemini, etc.)
- 🛠️ **Tool Integration** — เชื่อม GitHub CLI, Vercel, Render, ADB/Simctl
- 📱 **Mobile-First UX** — ตอบสั้น กระชับ เหมาะกับหน้าจอมือถือ

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Messaging   │────▶│   Backend    │────▶│  LLM API    │
│  Platform    │◀────│  (FastAPI)   │◀────│ (OpenRouter) │
│ (Telegram)   │     │              │     │              │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │   Redis +    │
                    │  PostgreSQL  │
                    └──────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | เหตุผล |
|-------|-----------|--------|
| **Backend** | Python + FastAPI | Async, ecosystem AI ดี |
| **LLM** | OpenRouter (MVP) | โมเดลฟรี, เปลี่ยนโมเดลง่าย |
| **Chat** | Telegram (MVP) | ฟรี ไม่จำกัด API ง่าย |
| **Memory** | Redis | Session + short-term memory |
| **Database** | PostgreSQL | Long-term storage |
| **Deployment** | Railway / VPS | เสถียร รันตลอด 24 ชม. |

---

## 📁 Project Structure

```
akasa/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Settings & env vars
│   ├── models/               # Pydantic models
│   │   └── telegram.py
│   ├── routers/              # API endpoints
│   │   ├── telegram.py       # Telegram webhook
│   │   └── health.py         # Health check
│   └── services/             # Business logic
│       ├── chat_service.py     # Chat orchestration
│       ├── llm_service.py      # LLM provider integration
│       ├── telegram_service.py # Telegram API communication
│       └── redis_service.py    # Conversation history management
│   └── utils/                # Utility functions
│       └── markdown_utils.py
├── tests/
│   ├── integration/          # Integration tests
│   │   └── test_redis_integration.py
│   └── services/             # Service layer unit tests
│       ├── test_chat_service.py
│       └── ...
├── docs/
│   └── akasa_analysis.md     # Project analysis
├── .env.example
├── .gitignore
├── requirements.txt
├── setup_local_bot.sh       # Local dev setup script
├── VERSION
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [Docker](https://www.docker.com/) (to run Redis locally)
- OpenRouter API Key ([สมัครที่นี่](https://openrouter.ai))
- Telegram Bot Token ([สร้างที่ BotFather](https://t.me/BotFather))
- [ngrok](https://ngrok.com/download) for local testing.

### Installation

```bash
# Clone
git clone https://github.com/oatrice/Akasa.git
cd Akasa

# Virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# แก้ไข .env ใส่ API keys
```

### Configuration

```env
# .env
# App Environment: "local" or "production"
ENV=local

# --- Secrets ---
OPENROUTER_API_KEY=your_openrouter_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
WEBHOOK_SECRET_TOKEN=a_strong_random_secret

# --- Services ---
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://localhost:5432/akasa
LLM_MODEL="google/gemma-2-9b-it:free"
```

### Run

#### Local Development & Testing
This is the recommended way to run the bot locally. The script will start `ngrok`, get a public URL, and automatically set the Telegram webhook for you.

```bash
# In one terminal, start Redis
docker run -d -p 6379:6379 redis

# In a second terminal, run the server
uvicorn app.main:app --reload --port 8000

# In a third terminal, run the setup script
chmod +x setup_local_bot.sh
./setup_local_bot.sh
```
After the script runs successfully, you can send messages to your bot in the Telegram app.

#### Production
```bash
# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## ⌨️ Commands

| Command | Description | Example |
|---|---|---|
| `/project` | ดูโปรเจ็กต์ปัจจุบันและโปรเจ็กต์ทั้งหมด | `/project` |
| `/project select <name>` | สลับไปทำงานในโปรเจ็กต์อื่น | `/project select my-app` |
| `/project new <name>` | สร้างและสลับไปโปรเจ็กต์ใหม่ | `/project new new-feature` |
| `/project rename <old> <new>` | เปลี่ยนชื่อโปรเจ็กต์ | `/project rename old-name new-name`|
| `/model` | ดูโมเดล AI ที่ใช้ปัจจุบันและรายการที่เลือกได้ | `/model` |
| `/model <alias>` | เปลี่ยนโมเดล AI ที่ต้องการใช้ | `/model claude` |
| `/note <description>` | บันทึก Task ปัจจุบันเพื่อช่วยให้บอทจำบริบท | `/note working on the login bug` |

---

## 📋 Roadmap

### Phase 1: MVP 🎯 *(Current)*
- [x] สมัคร OpenRouter + ทดสอบ API
- [x] สร้าง FastAPI backend
- [x] สร้าง Telegram Bot + webhook
- [x] ส่งข้อความ → LLM → ตอบกลับ
- [ ] Deploy (local / Railway)

### Phase 2: Memory & Multi-Platform
- [x] Conversation history (Redis)
- [x] Project-Specific Memory (via `/note` command)
- [x] Code formatting ใน chat
- [x] System prompt สำหรับ coding assistant
- [ ] เพิ่ม LINE Bot
- [ ] Rate limiting + error handling

### Phase 3: Tools & RAG
- [ ] เชื่อม GitHub API (อ่านโค้ด, review PR)
- [ ] Code Sandbox (รันโค้ดได้จากแชท)
- [ ] RAG — สอนบอทให้รู้จัก codebase
- [ ] Voice Note → Whisper → LLM

### Phase 4: Polish
- [x] Multi-model selection (เลือกโมเดลใน chat)
- [ ] Analytics dashboard
- [ ] WhatsApp integration
- [ ] Custom instructions per user

---

## 💰 Cost Estimate

| Stage | ค่าใช้จ่าย/เดือน |
|-------|----------------|
| **MVP** (OpenRouter free + Telegram) | **$0** |
| **Dev** (Claude/GPT + VPS) | ~$10-15 |
| **Scale** (Multi-platform + DB) | ~$20-30 |

---

## 🤝 Contributing

This is a personal project by [@oatrice](https://github.com/oatrice).

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.## [0.10.0] - 2026-03-09

### Added
- **API สำหรับส่งการแจ้งเตือน**: เพิ่ม Endpoint `POST /api/v1/notifications/send` ที่ปลอดภัยด้วย API Key สำหรับให้ระบบภายนอก (เช่น Gemini CLI) ส่งข้อความแจ้งเตือนไปยังผู้ใช้ Telegram ได้โดยตรง (Proactive Notifications)
- **การจัดการบริบทโปรเจกต์**: ผู้ใช้สามารถสลับระหว่างโปรเจกต์ต่างๆ ได้อย่างราบรื่น โดยบอทจะจดจำและแสดงสรุป Task ล่าสุดที่ทำไว้ในแต่ละโปรเจกต์เมื่อสลับกลับมา
- **คำสั่ง `/note`**: เพิ่มคำสั่งให้ผู้ใช้สามารถบันทึกหรืออัปเดต Task ปัจจุบันสำหรับโปรเจกต์ที่กำลังทำงานอยู่ได้
- **การบันทึก Agent State**: สถานะการทำงานของบอท (เช่น Task ปัจจุบัน, ไฟล์ที่กำลังแก้ไข) จะถูกบันทึกแยกตามโปรเจกต์ เพื่อให้การกู้คืนบริบทมีประสิทธิภาพ

### Fixed
- **การสร้าง Update Object**: แก้ไขการสร้าง Object `Update` ใน Test Suite เพื่อจัดการกับ Alias ของ `from` ได้อย่างถูกต้อง
- **ลำดับ Decorator ของ Mock**: แก้ไขลำดับของ Mock Decorator ใน Test Case ของ `handle_chat_message` เพื่อให้ทำงานได้อย่างถูกต้อง
- **Type Fixes & Test Guidance**: ปรับปรุง Type Hinting และคำแนะนำในการทดสอบตามรายงาน Code Review

### Changed
- **Refactoring `telegram_service`**: เปลี่ยนชื่อ Singleton Instance ของ `telegram_service` เป็น `tg_service` เพื่อความสอดคล้อง
- **Test Refactoring**: ปรับปรุงการเขียน Test สำหรับ `chat_service` โดยใช้ `patch.object` เพื่อหลีกเลี่ยงปัญหาการชนกันของชื่อ Mock
- **Sync AI Brain Artifacts**: อัปเดตเอกสารประกอบในส่วน AI Brain ให้สอดคล้องกับการเปลี่ยนแปลงล่าสุด