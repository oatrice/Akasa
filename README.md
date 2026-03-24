# 🌌 Akasa — AI Coding Assistant Chatbot

> ผู้ช่วยเขียนโค้ดผ่าน Messaging App — เขียนโค้ดได้ทุกที่ ไม่ต้องอยู่หน้าคอม

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- 🤖 **AI Coding Assistant** — ถามโค้ด, debug, ขอ snippet ผ่านแชท
- 📱 **Remote Dev Workspace** (v0.7.0+) — จัดการ GitHub (สร้าง Issue, สร้าง PR, **สรุป Roadmap**), จัดการ **Planning Docs** (`spec`, `plan`, `sbe`, `analysis`), สั่ง Build/Deploy **แบบ Asynchronous**, และดู Screenshot จาก Emulator/Simulator ผ่านแชท
- 🔄 **Bidirectional Control** — สั่งงาน Local Tools (Command Queue) ผ่าน Multi-Protocol Daemon และรับผลลัพธ์กลับในแชท
- 🔒 **Secure Action Confirmation** — ยืนยันการทำงานที่สำคัญ (เช่น สร้าง GitHub PR หรือคำสั่งจาก IDE/MCP) ผ่านปุ่มใน Telegram ก่อนสั่งรันจริง
- 🔔 **Proactive Notifications** — แจ้งเตือนงาน Long-running, AI Agent Timeout, Review Ready, หรือสถานะ Deploy แบบ Asynchronous พร้อมแสดงแหล่งที่มา (Source) ที่ชัดเจน
- 🛡️ **Topic Restriction** — ระบบตรวจสอบและจำกัดหัวข้อการสนทนาให้เน้นเรื่องการเขียนโค้ดและเทคนิคเท่านั้น
- 💬 **Multi-Platform** — รองรับ Telegram, LINE, WhatsApp
- 📂 **Multi-Project Support** — จัดการและสลับ Context ระหว่างโปรเจ็กต์ด้วยคำสั่ง `/project`, `project overview` และ `project status` **พร้อมระบบสรุปงานปัจจุบันด้วย AI (Current Work Summary)** พร้อมประวัติแชทที่แยกจากกัน
- 🧠 **Context Memory** — จำบทสนทนาและสถานะการทำงานล่าสุดของแต่ละโปรเจ็กต์ (Agent State) เมื่อสลับกลับมาจะมีการสรุปงานค้างให้
- 📝 **Task Notes** — บันทึก Task ที่กำลังทำอยู่สำหรับโปรเจ็กต์ปัจจุบันด้วยคำสั่ง `/note <your task description>` เพื่อให้บอทจำบริบทได้แม่นยำขึ้น
- 🔌 **Multi-LLM** — สลับโมเดล AI ได้ผ่านคำสั่ง `/model` (GPT-4o, Claude 3, Gemini, etc.)
- 🛠️ **Tool Integration** — เชื่อม GitHub CLI, Vercel, Render, ADB/Simctl, **Gemini CLI** และรองรับ MCP (Model Context Protocol)
- 📱 **Mobile-First UX** — ตอบสั้น กระชับ เหมาะกับหน้าจอมือถือ พร้อมระบบ Markdown-aware chunking สำหรับข้อความยาว (>4096 ตัวอักษร)

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
│   │   ├── telegram.py
│   │   ├── notification.py   # Task & status notifications
│   │   ├── command.py        # Command queue models
│   │   └── deployment.py     # Asynchronous deployment models
│   ├── routers/              # API endpoints
│   │   ├── actions.py        # Remote action confirmation
│   │   ├── commands.py       # Command Queue endpoints
│   │   ├── notifications.py  # AI task completion notifications
│   │   ├── telegram.py       # Telegram webhook
│   │   ├── deployments.py    # Asynchronous deployment endpoints
│   │   └── health.py         # Health check
│   └── services/             # Business logic
│       ├── chat_service.py     # Chat orchestration
│       ├── command_queue_service.py # Bidirectional command queue
│       ├── github_service.py   # GitHub API communication
│       ├── llm_service.py      # LLM provider integration
│       ├── deploy_service.py   # Asynchronous deployment logic
│       ├── telegram_service.py # Telegram API communication
│       ├── timeout_watcher_service.py # AI Agent timeout observer
│       └── redis_service.py    # Conversation history management
│   └── utils/                # Utility functions
│       ├── markdown_utils.py
│       └── source_display.py
├── scripts/
│   ├── akasa_mcp_server.py  # MCP Server for IDE integration
│   ├── local_tool_daemon.py # Daemon สำหรับการ execute command queue แบบ multi-protocol
│   └── setup_local_bot.sh   # Local dev setup script
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
├── VERSION
└── README.md
```