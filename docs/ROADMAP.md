# 🗺️ Akasa Roadmap

> AI-Powered Coding Assistant — ผู้ช่วยเขียนโค้ดอัจฉริยะผ่าน Chat

---

## Phase 1: Foundation — ทดสอบ API และส่งข้อความพื้นฐาน

| # | Issue | Status |
|---|---|---|
| [#1](https://github.com/oatrice/Akasa/issues/1) | สมัคร OpenRouter + ทดสอบ API | ✅ Complete |
| [#2](https://github.com/oatrice/Akasa/issues/2) | สร้าง FastAPI backend | ✅ Complete |
| [#3](https://github.com/oatrice/Akasa/issues/3) | สร้าง Telegram Bot + webhook | ✅ Complete |
| [#4](https://github.com/oatrice/Akasa/issues/4) | ส่งข้อความ ➡️ LLM ➡️ ตอบกลับ | ✅ Complete |
| [#5](https://github.com/oatrice/Akasa/issues/5) | Deploy MVP | 🔲 Todo |

---

## Phase 2: Chat Experience — ปรับปรุงประสบการณ์แชท

| # | Issue | Status |
|---|---|---|
| [#6](https://github.com/oatrice/Akasa/issues/6) | Conversation history (Redis) | ✅ Complete |
| [#7](https://github.com/oatrice/Akasa/issues/7) | Code formatting ใน chat | ✅ Complete |
| [#8](https://github.com/oatrice/Akasa/issues/8) | System prompt สำหรับ coding assistant | ✅ Complete |
| [#13](https://github.com/oatrice/Akasa/issues/13) | Multi-model selection | ✅ Complete |
| [#53](https://github.com/oatrice/Akasa/issues/53) | Clear Error Messaging for OpenRouter Credits | ✅ Complete |
| [#71](https://github.com/oatrice/Akasa/issues/71) | Telegram MarkdownV2 Escape/Fallback + list_github_repos + System Prompt Fix | ✅ Complete |
| [#25](https://github.com/oatrice/Akasa/issues/25) | Local Bot Build Info in Responses | ✅ Complete |
| [#9](https://github.com/oatrice/Akasa/issues/9) | เพิ่ม LINE Bot | 🔲 Todo |
| [#10](https://github.com/oatrice/Akasa/issues/10) | Rate limiting + error handling | 🔲 Todo |

---

## Phase 3: Remote Dev — Core Foundation (Tier 1) 🚀

| # | Issue | Status |
|---|---|---|
| [#17](https://github.com/oatrice/Akasa/issues/17) | ออกแบบโครงสร้างแชทสำหรับการทำงานหลายโปรเจ็กต์ | ✅ Complete |
| [#38](https://github.com/oatrice/Akasa/issues/38) | Project-Specific Memory & Context Restoration | ✅ Complete |
| [#29](https://github.com/oatrice/Akasa/issues/29) | Implement Secure Proactive Notification Endpoint | ✅ Complete |
| [#30](https://github.com/oatrice/Akasa/issues/30) | Support Outbound Messaging in TelegramService | ✅ Complete |

---

## Phase 4: Remote Dev — Orchestration & Build (Tier 2–3)

| # | Issue | Status |
|---|---|---|
| [#31](https://github.com/oatrice/Akasa/issues/31) | GithubService: Subprocess Wrapper for GH CLI | ✅ Complete |
| [#32](https://github.com/oatrice/Akasa/issues/32) | Define GitHub Function Calling for ChatService | ✅ Complete |
| [#49](https://github.com/oatrice/Akasa/issues/49) | Remote Action Confirmation via Akasa Bot (Telegram) | ✅ Complete |
| [#58](https://github.com/oatrice/Akasa/issues/58) | Antigravity IDE Action Confirmation via Akasa Bot | ✅ Complete |
| [#61](https://github.com/oatrice/Akasa/issues/61) | Task Completion Notification for AI Assistants (MCP) | ✅ Complete |
| [#33](https://github.com/oatrice/Akasa/issues/33) | Async Deployment Service for Web & Backend | ✅ Complete |
| [#34](https://github.com/oatrice/Akasa/issues/34) | Post-Build Notification System with URL Verification | ✅ Complete |
| [#67](https://github.com/oatrice/Akasa/issues/67) | AI Agent Timeout Observer (ตรวจจับ Agent ที่หยุดทำงาน) | ✅ Complete |
| [#66](https://github.com/oatrice/Akasa/issues/66) | Telegram → Local Tools Command Queue (Bidirectional Control) | ✅ Complete |
| [#68](https://github.com/oatrice/Akasa/issues/68) | IDE Integration for Command Queue (Zed, Antigravity, Windsurf) | 🔲 Todo |

---

## Phase 5: Remote Dev — Mobile Visual Verification (Tier 4)

| # | Issue | Status |
|---|---|---|
| [#35](https://github.com/oatrice/Akasa/issues/35) | ADB & Simctl Screenshot Service | 🔲 Todo |
| [#36](https://github.com/oatrice/Akasa/issues/36) | Remote UI Control via ADB/Maestro CLI | 🔲 Todo |

---

## Phase 6: Scale, Web Hub & Cross-Platform (Tier 5)

| # | Issue | Status |
|---|---|---|
| [#37](https://github.com/oatrice/Akasa/issues/37) | Unified User Session & Multi-Platform Context Sync (Telegram + macOS) | 🔲 Todo |
| [#28](https://github.com/oatrice/Akasa/issues/28) | Web Dashboard & CLI Integration Hub (GitHub, Render, Vercel) | 🔲 Todo |
| [#11](https://github.com/oatrice/Akasa/issues/11) | เชื่อม GitHub API (อ่านโค้ด, review PR) | 🔲 Todo |
| [#12](https://github.com/oatrice/Akasa/issues/12) | Code Sandbox (รันโค้ดได้จากแชท) | 🔲 Todo |
| [#16](https://github.com/oatrice/Akasa/issues/16) | Custom instructions per user | 🔲 Todo |
| [#14](https://github.com/oatrice/Akasa/issues/14) | Analytics dashboard | 🔲 Todo |
| [#15](https://github.com/oatrice/Akasa/issues/15) | WhatsApp integration | 🔲 Todo |

---

## 📊 Progress Summary

| Phase | Done | Todo | Total |
|---|---|---|---|
| Phase 1 — Foundation | 4 | 1 | 5 |
| Phase 2 — Chat Experience | 7 | 2 | 9 |
| Phase 3 — Remote Dev Core | 4 | 0 | 4 |
| Phase 4 — Orchestration & Build | 8 | 1 | 9 |
| Phase 5 — Mobile Visual | 0 | 2 | 2 |
| Phase 6 — Scale & Cross-Platform | 0 | 7 | 7 |
| **Total** | **23** | **13** | **36** |