# 🌌 Akasa — AI Coding Assistant Chatbot

> ผู้ช่วยเขียนโค้ดผ่าน Messaging App — เขียนโค้ดได้ทุกที่ ไม่ต้องอยู่หน้าคอม

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- 🤖 **AI Coding Assistant** — ถามโค้ด, debug, ขอ snippet ผ่านแชท
- 💬 **Multi-Platform** — รองรับ Telegram, LINE, WhatsApp
- 🧠 **Context Memory** — จำบทสนทนาและ context การเขียนโค้ด
- 🔌 **Multi-LLM** — เชื่อมต่อ OpenRouter, Claude, GPT-4o, Gemini
- 🛠️ **Tool Integration** — เชื่อม GitHub, Code Sandbox (อนาคต)
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
OPENROUTER_API_KEY=your_openrouter_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
WEBHOOK_SECRET_TOKEN=a_strong_random_secret
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://localhost:5432/akasa
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

## 📋 Roadmap

### Phase 1: MVP 🎯 *(Current)*
- [x] สมัคร OpenRouter + ทดสอบ API
- [x] สร้าง FastAPI backend
- [x] สร้าง Telegram Bot + webhook
- [x] ส่งข้อความ → LLM → ตอบกลับ
- [ ] Deploy (local / Railway)

### Phase 2: Memory & Multi-Platform
- [x] Conversation history (Redis)
- [ ] Code formatting ใน chat
- [ ] System prompt สำหรับ coding assistant
- [ ] เพิ่ม LINE Bot
- [ ] Rate limiting + error handling

### Phase 3: Tools & RAG
- [ ] เชื่อม GitHub API (อ่านโค้ด, review PR)
- [ ] Code Sandbox (รันโค้ดได้จากแชท)
- [ ] RAG — สอนบอทให้รู้จัก codebase
- [ ] Voice Note → Whisper → LLM

### Phase 4: Polish
- [ ] Multi-model selection (เลือกโมเดลใน chat)
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

MIT License — see [LICENSE](LICENSE) for details.