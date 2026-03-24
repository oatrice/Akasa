# 🗺️ Akasa Roadmap

> AI-Powered Coding Assistant — ผู้ช่วยเขียนโค้ดอัจฉริยะผ่าน Chat

---

## Phase 1: Foundation — ทดสอบ API และส่งข้อความพื้นฐาน

| # | Issue | Status | Due Date |
|---|---|---|---|
| [#1](https://github.com/oatrice/Akasa/issues/1) | สมัคร OpenRouter + ทดสอบ API | ✅ Complete | 2026-03-08 |
| [#2](https://github.com/oatrice/Akasa/issues/2) | สร้าง FastAPI backend | ✅ Complete | 2026-03-08 |
| [#3](https://github.com/oatrice/Akasa/issues/3) | สร้าง Telegram Bot + webhook | ✅ Complete | 2026-03-08 |
| [#4](https://github.com/oatrice/Akasa/issues/4) | ส่งข้อความ ➡️ LLM ➡️ ตอบกลับ | ✅ Complete | 2026-03-08 |
| [#5](https://github.com/oatrice/Akasa/issues/5) | Deploy MVP | 🔲 Todo | 2026-03-20 |

---

## Phase 2: Chat Experience — ปรับปรุงประสบการณ์แชท

| # | Issue | Status | Due Date |
|---|---|---|---|
| [#6](https://github.com/oatrice/Akasa/issues/6) | Conversation history (Redis) | ✅ Complete | 2026-03-08 |
| [#7](https://github.com/oatrice/Akasa/issues/7) | Code formatting ใน chat | ✅ Complete | 2026-03-08 |
| [#8](https://github.com/oatrice/Akasa/issues/8) | System prompt สำหรับ coding assistant | ✅ Complete | 2026-03-08 |
| [#13](https://github.com/oatrice/Akasa/issues/13) | Multi-model selection | ✅ Complete | 2026-03-08 |
| [#53](https://github.com/oatrice/Akasa/issues/53) | Clear Error Messaging for OpenRouter Credits | ✅ Complete | 2026-03-10 |
| [#71](https://github.com/oatrice/Akasa/issues/71) | Telegram MarkdownV2 Escape/Fallback + list_github_repos + System Prompt Fix | ✅ Complete | 2026-03-18 |
| [#25](https://github.com/oatrice/Akasa/issues/25) | Local Bot Build Info in Responses | ✅ Complete | 2026-03-08 |
| [#9](https://github.com/oatrice/Akasa/issues/9) | เพิ่ม LINE Bot | 🔲 Todo | 2026-03-20 |
| [#10](https://github.com/oatrice/Akasa/issues/10) | Rate limiting + error handling | ✅ Complete | 2026-03-19 |

---

## Phase 3: Remote Dev — Core Foundation (Tier 1) 🚀

| # | Issue | Status | Due Date |
|---|---|---|---|
| [#17](https://github.com/oatrice/Akasa/issues/17) | ออกแบบโครงสร้างแชทสำหรับการทำงานหลายโปรเจ็กต์ | ✅ Complete | 2026-03-19 |
| [#38](https://github.com/oatrice/Akasa/issues/38) | Project-Specific Memory & Context Restoration | ✅ Complete | 2026-03-09 |
| [#29](https://github.com/oatrice/Akasa/issues/29) | Implement Secure Proactive Notification Endpoint | ✅ Complete | 2026-03-09 |
| [#30](https://github.com/oatrice/Akasa/issues/30) | Support Outbound Messaging in TelegramService | ✅ Complete | 2026-03-09 |

---

## Phase 4: Remote Dev — Orchestration & Build (Tier 2–3)

| # | Issue | Status | Due Date |
|---|---|---|---|
| [#31](https://github.com/oatrice/Akasa/issues/31) | GithubService: Subprocess Wrapper for GH CLI | ✅ Complete | 2026-03-10 |
| [#32](https://github.com/oatrice/Akasa/issues/32) | Define GitHub Function Calling for ChatService | ✅ Complete | 2026-03-10 |
| [#49](https://github.com/oatrice/Akasa/issues/49) | Remote Action Confirmation via Akasa Bot (Telegram) | ✅ Complete | 2026-03-12 |
| [#58](https://github.com/oatrice/Akasa/issues/58) | Antigravity IDE Action Confirmation via Akasa Bot | ✅ Complete | 2026-03-13 |
| [#61](https://github.com/oatrice/Akasa/issues/61) | Task Completion Notification for AI Assistants (MCP) | ✅ Complete | 2026-03-13 |
| [#33](https://github.com/oatrice/Akasa/issues/33) | Async Deployment Service for Web & Backend | ✅ Complete | 2026-03-16 |
| [#34](https://github.com/oatrice/Akasa/issues/34) | Post-Build Notification System with URL Verification | ✅ Complete | 2026-03-14 |
| [#67](https://github.com/oatrice/Akasa/issues/67) | AI Agent Timeout Observer (ตรวจจับ Agent ที่หยุดทำงาน) | ✅ Complete | 2026-03-16 |
| [#66](https://github.com/oatrice/Akasa/issues/66) | Telegram → Local Tools Command Queue (Bidirectional Control) | ✅ Complete | 2026-03-16 |
| [#68](https://github.com/oatrice/Akasa/issues/68) | IDE Integration for Command Queue (Zed, Antigravity, Windsurf) | ✅ Complete | 2026-03-19 |
| [#83](https://github.com/oatrice/Akasa/issues/83) | Gemini CLI local project inspection from Telegram context | 🔲 Todo | TBD |

---

## Phase 5: Remote Dev — Mobile Visual Verification (Tier 4)

| # | Issue | Status | Due Date |
|---|---|---|---|
| [#35](https://github.com/oatrice/Akasa/issues/35) | ADB & Simctl Screenshot Service | 🔲 Todo | 2026-03-20 |
| [#36](https://github.com/oatrice/Akasa/issues/36) | Remote UI Control via ADB/Maestro CLI | 🔲 Todo | 2026-03-21 |

---

## Phase 6: Scale, Web Hub & Cross-Platform (Tier 5)

| # | Issue | Status | Due Date |
|---|---|---|---|
| [#37](https://github.com/oatrice/Akasa/issues/37) | Unified User Session & Multi-Platform Context Sync (Telegram + macOS) | ✅ Complete | 2026-03-18 |
| [#28](https://github.com/oatrice/Akasa/issues/28) | Web Dashboard & CLI Integration Hub (GitHub, Render, Vercel) | 🔲 Todo | 2026-03-21 |
| [#11](https://github.com/oatrice/Akasa/issues/11) | เชื่อม GitHub API (อ่านโค้ด, review PR) | 🔲 Todo | 2026-03-20 |
| [#12](https://github.com/oatrice/Akasa/issues/12) | Code Sandbox (รันโค้ดได้จากแชท) | 🔲 Todo | 2026-03-20 |
| [#16](https://github.com/oatrice/Akasa/issues/16) | Custom instructions per user | 🔲 Todo | 2026-03-20 |
| [#14](https://github.com/oatrice/Akasa/issues/14) | Analytics dashboard | 🔲 Todo | 2026-03-21 |
| [#15](https://github.com/oatrice/Akasa/issues/15) | WhatsApp integration | 🔲 Todo | 2026-03-21 |

---

## 📊 Progress Summary

| Phase | Done | Todo | Total |
|---|---|---|---|
| Phase 1 — Foundation | 4 | 1 | 5 |
| Phase 2 — Chat Experience | 7 | 2 | 9 |
| Phase 3 — Remote Dev Core | 4 | 0 | 4 |
| Phase 4 — Orchestration & Build | 9 | 1 | 10 |
| Phase 5 — Mobile Visual | 0 | 2 | 2 |
| Phase 6 — Scale & Cross-Platform | 1 | 6 | 7 |
| **Total** | **25** | **12** | **37** |

---

## 📅 Replan History

> บันทึกการเปลี่ยนแปลง Due Date เพื่อเก็บ history ไว้ย้อนดูภายหลัง

### 2026-03-21 — Initial Consolidation from Luma Metrics

ดึง `due_date` จาก `.luma_metrics.json` เข้า ROADMAP เป็นครั้งแรก พบว่า **Todo items ต่อไปนี้เกิน deadline แล้ว:**

| Issue | Title | Original Due | Status | Note |
|---|---|---|---|---|
| #5 | Deploy MVP | 2026-03-20 | 🔲 Overdue | Phase 1 ยังไม่ได้ deploy |
| #9 | เพิ่ม LINE Bot | 2026-03-20 | 🔲 Overdue | ยังไม่เริ่ม, priority ต่ำ |
| #11 | เชื่อม GitHub API | 2026-03-20 | 🔲 Overdue | Phase 6, ยังไม่เริ่ม |
| #12 | Code Sandbox | 2026-03-20 | 🔲 Overdue | Phase 6, ยังไม่เริ่ม |
| #16 | Custom instructions per user | 2026-03-20 | 🔲 Overdue | Phase 6, ยังไม่เริ่ม |
| #35 | ADB & Simctl Screenshot Service | 2026-03-20 | 🔲 Overdue | Phase 5, ยังไม่เริ่ม |

**Todo items ที่ due วันนี้ (2026-03-21):**

| Issue | Title | Due | Status |
|---|---|---|---|
| #14 | Analytics dashboard | 2026-03-21 | 🔲 Due Today |
| #15 | WhatsApp integration | 2026-03-21 | 🔲 Due Today |
| #28 | Web Dashboard & CLI Integration Hub | 2026-03-21 | 🔲 Due Today |
| #36 | Remote UI Control via ADB/Maestro CLI | 2026-03-21 | 🔲 Due Today |

> ⏳ **Action needed:** ต้อง replan due date ใหม่สำหรับ 10 issues ข้างต้น

## Synced From GitHub

### Issue #82 - Feature: check kanban and ROADMAP.md via Telegram (/gh + NLP prompt)
- **GitHub:** [#82](https://github.com/oatrice/Akasa/issues/82)
- **State:** OPEN
- ✅ **Done**

