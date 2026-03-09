# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|---|---|
| **Feature Name** | GitHub Service: Subprocess Wrapper for GH CLI |
| **Issue URL** | [#31](N/A) |
| **Date** | 9 มีนาคม 2569 |
| **Analyst** | Luma AI (Senior Technical Analyst) |
| **Priority** | 🔴 High |
| **Status** | 📝 Draft |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

บอทไม่สามารถโต้ตอบหรือจัดการ Issues และ Repositories บน GitHub ได้โดยตรงจากแชท ทำให้ผู้ใช้ต้องสลับไปใช้เครื่องมืออื่น ทำให้การทำงานขาดความต่อเนื่อง

### 1.2 User Stories

| # | As a | I want to | So that |
|---|---|---|---|
| 1 | bot user | list GitHub issues via chat | I can quickly check the status of tasks. |
| 2 | bot user | create GitHub issues via chat | I can easily log new tasks without leaving the chat interface. |
| 3 | bot user | check GitHub PR status via chat | I can monitor pull requests. |
* *(Note: The objective mentions "Repository" management, but the technical details only specify issue and PR commands. Repository management features are not detailed and thus not included in user stories or ACs.)*

### 1.3 Acceptance Criteria

- [ ] **AC1:** `GithubService` class ถูกสร้างขึ้นใน `app/services/github_service.py`.
- [ ] **AC2:** `GithubService` ใช้ `subprocess.run` เพื่อเรียกคำสั่ง `gh issue list`, `gh issue create`, และ `gh pr status`.
- [ ] **AC3:** GitHub Personal Access Token (PAT) ถูกอ่านจาก Environment Variables เพื่อใช้ในการยืนยันตัวตน.
- [ ] **AC4:** บอทสามารถแสดงรายการ GitHub issues ได้สำเร็จเมื่อมีการร้องขอผ่านคำสั่งแชท.
- [ ] **AC5:** บอทสามารถสร้าง GitHub issue พร้อม title และ body ได้สำเร็จเมื่อมีการร้องขอผ่านคำสั่งแชท.
- [ ] **AC6:** บอทสามารถแสดงสถานะของ GitHub PRs ได้สำเร็จเมื่อมีการร้องขอผ่านคำสั่งแชท.
- [ ] **AC7:** Input จากผู้ใช้สำหรับคำสั่ง `gh cli` จะถูก sanitize เพื่อป้องกัน Command Injection.

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[User sends command e.g., "/github issues list"] --> B[Bot invokes GithubService]
    B --> C[GithubService constructs gh cli command]
    C --> D[subprocess.run executes gh cli command with PAT]
    D --> E[gh cli interacts with GitHub, returns output/exit code]
    E --> F[GithubService captures and processes output/error]
    F --> G[GithubService returns result to Bot]
    G --> H[Bot formats result and sends to user]
```
*(Example for create issue: User provides title/body -> Bot -> GithubService -> `subprocess.run("gh issue create ...")` -> Bot confirms creation)*

### 2.2 Screen/Page Requirements

This feature is for a chat-based bot, so there are no traditional screens. Interactions occur within the chat interface.
| หน้าจอ (Chat Interface) | Actions | Components |
|---|---|---|
| Chat Interface | User inputs commands (e.g., `/github issues list`, `/github create issue ...`) | Bot responses (textual output, confirmations, errors) |

### 2.3 Input/Output Specification

#### Inputs

| Field | Type | Required | Validation |
|---|---|---|---|
| GitHub CLI Command | string | ✅ | e.g., `issue list`, `issue create`, `pr status` |
| Command Arguments | string | ✅ | e.g., title, body for issue creation, PR identifiers |
| GitHub PAT | string | ✅ | Read from Environment Variable (`GITHUB_TOKEN`) |

#### Outputs

| Field | Type | Description |
|---|---|---|
| CLI Output | string | Standard output from `gh cli` commands (e.g., JSON, text) |
| Error Output | string | Standard error from `gh cli` commands or `subprocess` execution errors |
| Confirmation Message | string | Success confirmation for operations like issue creation |
| Formatted Result | string | Bot's formatted response to the user based on CLI output |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|---|---|---|
| `app/services/github_service.py` | 🔴 High | New core service for GitHub integration using `gh cli` and `subprocess`. |
| Bot Command Handler/Router | 🟡 Medium | Needs updates to route new GitHub commands and handle service responses/errors. |
| Environment Variable Configuration | 🟢 Low | Requires setting `GITHUB_TOKEN` for bot execution. |
| User Interface (Chat Commands) | 🟡 Medium | New commands exposed to users, requiring potential documentation or guidance. |

### 3.2 Breaking Changes

- [ ] **BC1:** None expected, as this is an additive feature.

### 3.3 Backward Compatibility Plan

```
N/A
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

| คำถาม | คำตอบ | หมายเหตุ |
|---|---|---|
| เทคโนโลยีรองรับหรือไม่? (`gh cli`, `subprocess.run`) | ✅ | `gh cli` เป็นเครื่องมือมาตรฐาน และ `subprocess.run` เป็นไลบรารีมาตรฐานของ Python. |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | ทีมควรมีความคุ้นเคยกับการเขียน Python, การใช้ `subprocess` และการจัดการ Environment Variables. |
| Infrastructure รองรับหรือไม่? | ⚠️ | ต้องแน่ใจว่า `gh cli` ถูกติดตั้งในสภาพแวดล้อมที่บอททำงานอยู่ และสามารถจัดการ GitHub PAT ผ่าน Environment Variables ได้อย่างปลอดภัย. |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|---|---|
| **Estimated Effort** | 2-3 days |
| **Deadline** | Not Specified |
| **Buffer Time** | 1 day |
| **Feasible?** | ✅ |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|---|---|---|
| Development Time | N/A | - |
| **Total** | N/A | Assumes existing infrastructure and tools. |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|---|---|---|
| GitHub Personal Access Token (PAT) | 🔴 Critical | Store in Environment Variables (`GITHUB_TOKEN`). Grant minimum necessary scopes. Avoid logging. |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|---|---|---|
| Command Injection via user input | 🔴 High | Use `subprocess.run` with `shell=False` and argument lists. Sanitize and validate all user inputs rigorously. |
| Accidental leakage of PAT | 🔴 High | Store PAT exclusively in environment variables. Never log the token. |

### 5.3 Authentication & Authorization

```
Authentication is handled by the GitHub Personal Access Token (PAT). Authorization is determined by the scopes granted to the PAT. The PAT must have sufficient permissions (e.g., `repo`, `read:org`) to perform the intended actions.
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|---|---|---|
| Response Time (CLI commands) | < 5 seconds | N/A |
| Throughput | Dependent on Bot Concurrency & GitHub API Limits | N/A |
| Error Rate (command execution) | < 1% | N/A |

### 6.2 Scalability Plan

| Scenario | Expected Users | Scaling Strategy |
|---|---|---|
| Normal | Standard Bot Users | Standard Bot Concurrency |
| Peak | High Bot Usage | Monitor `gh cli` performance and GitHub API rate limits. Implement bot command rate limiting if needed. |
| Growth (1yr) | Increasing Users | Ensure `gh cli` installation and PAT management are robust in scaled environments. |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|---|---|---|---|
| GitHub Interaction Capability | Bot cannot interact with GitHub Issues or Repositories. | Bot can manage GitHub Issues and PR status via chat commands using `gh cli`. | Missing dedicated service (`GithubService`) to abstract and securely execute `gh cli` commands. |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|---|---|---|---|---|
| Command Injection via malicious user input | 🟡 Medium | 🔴 High | 6 | Implement robust input validation and sanitization for all user-provided arguments passed to `gh cli` commands. Use `subprocess.run` with `shell=False`. |
| Exposure of GitHub PAT | 🟢 Low | 🔴 Critical | 3 | Store PAT exclusively in environment variables. Do not log the PAT. Ensure minimum required scopes are granted to the PAT. |
| Unreliable `gh cli` output parsing | 🟡 Medium | 🟡 Medium | 4 | Implement thorough error handling for `subprocess.run` (checking exit codes and stderr). Use reliable methods to parse `gh cli`'s JSON output where available, or robust string parsing otherwise. Provide clear error messages to the user. |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|---|---|---|
| Requirement | ✅ Clear | ความต้องการชัดเจนในการเพิ่มความสามารถให้บอทโต้ตอบกับ GitHub. |
| Feature | ✅ Defined | Feature ถูกกำหนดขอบเขตการทำงานที่ชัดเจน (Issue list, create, PR status) โดยใช้ `gh cli`. |
| Impact | ⚠️ Medium | มีผลกระทบต่อ Service ใหม่, การจัดการคำสั่งบอท, และการตั้งค่า Environment Variables. |
| Feasibility | ✅ Feasible | เป็นไปได้ในทางเทคนิค โดยมีข้อควรระวังในการติดตั้ง `gh cli` และการจัดการ PAT. |
| Security | ⚠️ Needs Review | มีความเสี่ยงด้าน Command Injection และการจัดการ PAT ที่ต้องได้รับการตรวจสอบและป้องกันอย่างเข้มงวด. |
| Performance | ✅ Acceptable | ประสิทธิภาพขึ้นอยู่กับ `gh cli` และการเชื่อมต่อเครือข่ายเป็นหลัก. |
| Risk | ⚠️ Some Risks | มีความเสี่ยงที่ต้องจัดการ เช่น Command Injection, การเปิดเผย PAT, และความน่าเชื่อถือในการ parse output. |

### 9.2 Recommendations

1.  **Prioritize Secure Execution:** Implement command injection prevention by using `subprocess.run` with argument lists and strict input sanitization.
2.  **Secure PAT Handling:** Store GitHub PAT in environment variables only, use minimum necessary scopes, and avoid logging.
3.  **Robust Error Handling and Parsing:** Ensure comprehensive error handling for `subprocess` calls and reliable parsing of `gh cli` output to provide clear feedback to users.

### 9.3 Next Steps

- [ ] **pending:** Create `app/services/github_service.py`.
- [ ] **pending:** Implement `GithubService` to wrap `gh issue list`, `gh issue create`, and `gh pr status` using `subprocess.run`.
- [ ] **pending:** Integrate `GithubService` into the bot's command handling logic.
- [ ] **pending:** Add unit tests for the `GithubService`.
- [ ] **pending:** Document new chat commands for GitHub interaction.

---

## 📎 Appendix

### Related Documents

- [Link to PRD]: N/A
- [Link to Design Docs]: N/A
- [Link to API Specs]: N/A

### Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Analyst | Luma AI (Senior Technical Analyst) | 9 มีนาคม 2569 | ✅ |
| Tech Lead | [Name] | [Date] | ⬜ |
| PM | [Name] | [Date] | ⬜ |