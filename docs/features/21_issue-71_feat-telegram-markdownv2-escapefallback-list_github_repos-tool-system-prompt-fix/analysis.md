# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Telegram MarkdownV2 escape/fallback, list_github_repos tool, system prompt fix |
| **Issue URL** | [Issue #71](https://github.com/oatrice/akasa/issues/71) |
| **Date** | March 16, 2026 |
| **Analyst** | Luma AI (Senior Technical Analyst) |
| **Priority** | 🔴 High |
| **Status** | 🚀 In Progress |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

```
1. ผู้ใช้พบปัญหา Telegram API ตอบกลับ 400 Bad Request เมื่อ LLM สร้างข้อความที่มีอักขระพิเศษ (เช่น _, *, [, ]) ที่ไม่ได้ escape ตามมาตรฐาน MarkdownV2
2. System Prompt ปัจจุบันมีความเข้มงวดเกินไป ทำให้ปฏิเสธคำถามที่เกี่ยวข้องกับ Project Management หรือ DevOps ซึ่งเป็นส่วนหนึ่งของการพัฒนา Software
3. Bot ยังขาดความสามารถในการเรียกดูรายการ Repository ของผู้ใช้ ทำให้ไม่สะดวกในการจัดการโปรเจกต์
4. CI Test พังเมื่อไม่มีการตั้งค่า `AKASA_CHAT_ID` environment variable
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | User | receive responses from the bot without errors even if they contain special characters | I can read the answer instead of seeing a crash or no response. |
| 2 | Developer | ask about DevOps and Project Management workflows | I can get assistance on the full software development lifecycle, not just coding. |
| 3 | User | list my GitHub repositories via the bot | I can quickly see available projects without leaving the chat interface. |
| 4 | Developer | run tests in CI environment without setting `AKASA_CHAT_ID` | The build pipeline passes reliably. |

### 1.3 Acceptance Criteria

- [ ] **AC1:** ระบบต้องทำการ Escape อักขระพิเศษตามมาตรฐาน Telegram MarkdownV2 ก่อนส่งข้อความ
- [ ] **AC2:** หากการส่งด้วย MarkdownV2 ล้มเหลว (400 Bad Request) ระบบต้องสามารถส่งข้อความเดิมซ้ำในรูปแบบ Plain Text ได้อัตโนมัติ (Fallback mechanism)
- [ ] **AC3:** System Prompt อนุญาตให้ตอบคำถามเรื่อง Project Management, DevOps และ Workflow ได้
- [ ] **AC4:** มี Tool ใหม่ `list_github_repos` ที่เรียกใช้คำสั่ง `gh repo list` ได้ถูกต้อง
- [ ] **AC5:** Unit Tests ผ่านทั้งหมด แม้ไม่มี `AKASA_CHAT_ID` ใน Environment

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[User Sends Message] --> B[LLM Process]
    B --> C{Tool Call?}
    C -->|Yes: list_github_repos| D[Execute gh repo list]
    D --> E[Format Repo List]
    E --> F[Generate Final Response]
    C -->|No| F
    F --> G[Escape MarkdownV2]
    G --> H[Send to Telegram API]
    H --> I{Success?}
    I -->|Yes| J[End]
    I -->|No (400 Bad Request)| K[Catch Error]
    K --> L[Send as Plain Text]
    L --> J
```

### 2.2 Screen/Page Requirements

| หน้าจอ | Actions | Components |
|--------|---------|------------|
| Telegram Chat | User types `/chat list my repos` | Chat Interface |
| Telegram Chat | Bot replies with repo list | Message Bubble (Markdown formatted) |

### 2.3 Input/Output Specification

#### Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `list_github_repos` | Tool Call | ❌ | None (Optional limits can be added later) |

#### Outputs

| Field | Type | Description |
|-------|------|-------------|
| Repository List | String | JSON or Text list of repositories (Name, Description, URL) |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| `app/services/chat_service.py` | 🟡 Medium | Logic for tool handling and message sending (Markdown escape/fallback). |
| `app/services/github_service.py` | 🟢 Low | Adding `list_repos` method. |
| `app/routers/commands.py` | 🟢 Low | Handling empty env vars for CI. |
| `app/config.py` | 🟢 Low | System prompt configuration. |

### 3.2 Breaking Changes

- [ ] **BC1:** None. The fallback to plain text ensures backward compatibility with existing clients/behavior.

### 3.3 Backward Compatibility Plan

```
ระบบมีการ implement Fallback mechanism: หาก MarkdownV2 มีปัญหา จะส่งเป็น Plain Text เสมอ เพื่อให้มั่นใจว่าผู้ใช้จะได้รับข้อความแน่นอน
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Python regex for escaping, `gh` CLI for repos. |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | Standard Python & Telegram API usage. |
| Infrastructure รองรับหรือไม่? | ✅ | Uses existing server & GitHub CLI auth. |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 0.5 days |
| **Deadline** | N/A |
| **Buffer Time** | 0 days |
| **Feasible?** | ✅ |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| N/A | 0 | Internal development |
| **Total** | 0 | |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| GitHub Repository Data | 🟡 Sensitive | Access via authenticated `gh` CLI (user context). |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| Code Injection in Markdown | 🟢 Low | `escape_markdown_v2` logic handles special chars. |
| Command Injection | 🟢 Low | `subprocess` calls use distinct arguments, no shell=True for variable parts. |

### 5.3 Authentication & Authorization

```
ใช้ GitHub CLI (`gh`) ที่ authenticate อยู่แล้วบนเครื่อง Server (Local Tools context)
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Markdown Escape Overhead | < 10ms | N/A |
| Fallback Retry Latency | < 500ms | N/A |

### 6.2 Scalability Plan

| Scenario | Expected Users | Scaling Strategy |
|----------|---------------|------------------|
| Normal | Single User (Self-hosted) | No scaling needed. |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| Stability | Bot crashes on markdown errors | Bot automatically falls back to plain text | Robust Error Handling |
| Capability | Can't list repos | Can list repos via `gh` | Tool Implementation |
| Scope | Strict Coding only | Coding + DevOps + PM | System Prompt adjustment |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| Telegram API changes Markdown spec | 🟢 Low | 🟡 Medium | 2 | Fallback to plain text protects against this. |
| `gh` CLI not authenticated | 🟢 Low | 🟡 Medium | 2 | Error handling in `GitHubService` to report auth status. |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|------|--------|--------------|
| Requirement | ✅ Clear | แก้ปัญหา 400 Bad Request และเพิ่มความสามารถพื้นฐานที่จำเป็น |
| Feature | ✅ Defined | เพิ่ม Tool และปรับปรุง Reliability |
| Impact | 🟢 Low | กระทบเฉพาะส่วน Chat logic และ GitHub service |
| Feasibility | ✅ Feasible | ใช้เวลาพัฒนาน้อย |
| Security | ✅ Acceptable | ใช้ Existing Auth |
| Performance | ✅ Acceptable | Overhead ต่ำมาก |
| Risk | 🟢 Low | ความเสี่ยงต่ำ มีแผนรองรับ (Fallback) |

### 9.2 Recommendations

1. **Implement Fallback First:** ให้ความสำคัญกับ Markdown fallback ก่อนเพื่อให้ User Experience ดีขึ้นทันที
2. **Verify GH CLI:** ตรวจสอบว่า `gh` CLI ติดตั้งและ login แล้วใน environment ที่รัน Akasa
3. **Extend Tests:** เพิ่ม Test case สำหรับข้อความที่มีอักขระพิเศษหลากหลายรูปแบบ

### 9.3 Next Steps

- [x] Apply fixes for Telegram Markdown escaping
- [x] update `GitHubService` with `list_repos`
- [x] Update System Prompt
- [x] Fix CI/CD tests

---

## 📎 Appendix

### Related Documents

- [Telegram Bot API - MarkdownV2 Style](https://core.telegram.org/bots/api#markdownv2-style)
- [GitHub CLI Manual](https://cli.github.com/manual/)

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Luma AI | March 16, 2026 | ✅ |
| Tech Lead | - | - | ⬜ |
| PM | - | - | ⬜ |