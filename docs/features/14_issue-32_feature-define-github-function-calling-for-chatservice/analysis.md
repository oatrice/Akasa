# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Define GitHub Function Calling for ChatService |
| **Issue URL** | [#32](https://github.com/oatrice/Akasa/issues/32) |
| **Date** | March 10, 2026 |
| **Analyst** | Luma AI (Senior Technical Analyst) |
| **Priority** | 🔴 High |
| **Status** | 📝 Draft |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

```
ปัจจุบัน Chat bot (Akasa) ทำหน้าที่เป็นเพียงตัวกลางในการสนทนากับ LLM เท่านั้น แต่ยังไม่มีความสามารถในการโต้ตอบกับเครื่องมือภายนอก เช่น GitHub ซึ่งจำกัดประโยชน์ในการใช้งานในฐานะผู้ช่วยนักพัฒนาซอฟต์แวร์ ปัญหานี้ทำให้ผู้ใช้ต้องสลับไปมาระหว่างหน้าต่างแชทและ GitHub เพื่อทำงานต่างๆ เช่น การสร้าง Issue หรือการแสดงความคิดเห็นใน PR ทำให้ขั้นตอนการทำงานไม่ราบรื่น
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | Developer | instruct the chat assistant to perform GitHub actions using natural language | I can manage my repository tasks (like creating issues) without leaving the chat interface. |
| 2 | Developer | have the assistant understand the intent to use a tool from my message | the assistant can automatically trigger the correct GitHub function. |

### 1.3 Acceptance Criteria

- [ ] **AC1:** `ChatService` must be updated to include tool definitions for `GithubService` functions, making them available to the LLM.
- [ ] **AC2:** When a user's prompt implies a GitHub action, the LLM must correctly generate a `tool_call` with the appropriate function name and parameters.
- [ ] **AC3:** `ChatService` must correctly parse the `tool_call` from the LLM and invoke the corresponding method in `GithubService`.
- [ ] **AC4:** The result from the `GithubService` execution (e.g., success message or error) must be passed back to the LLM to formulate a final, user-facing response.

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    subgraph User
        A[Sends message e.g., "Create an issue about a login bug"]
    end

    subgraph Akasa Backend
        B[ChatService receives message] --> C{Send to LLM with GitHub tool definitions}
        C --> D[LLM detects intent and returns a `tool_call` for `github_service.create_issue`]
        D --> E[ChatService parses `tool_call`]
        E --> F[ChatService invokes `GithubService.create_issue(...)`]
        F --> G[GithubService executes action via API/CLI]
        G --> H{Return result to ChatService}
        H --> I[ChatService sends tool result back to LLM for summary]
        I --> J[LLM generates final response e.g., "Done! I've created issue #45"]
    end

    subgraph User
        J --> K[Receives final confirmation message]
    end
```

### 2.2 Screen/Page Requirements

| หน้าจอ | Actions | Components |
|--------|---------|------------|
| N/A | This is a backend-only feature. It enhances the existing chat interface's capabilities without changing the UI. | N/A |

### 2.3 Input/Output Specification

#### Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| User Message | string | ✅ | Natural Language text containing an intent to perform a GitHub action. |

#### Outputs

| Field | Type | Description |
|-------|------|-------------|
| Final Response | string | A natural language text response confirming the action's result (e.g., "Issue created successfully at [URL]") or reporting an error. |
| GitHub Action | N/A | The side-effect of the operation, such as a new issue or comment on GitHub. |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| `app/services/chat_service.py` | 🔴 High | Core logic for handling tool definitions, parsing LLM `tool_call` responses, and orchestrating calls to `GithubService` will be implemented here. |
| `tests/services/test_chat_service.py` | 🔴 High | New unit and integration tests are required to validate the new tool-calling workflow and its interaction with other services. |
| `app/services/github_service.py` | 🟡 Medium | May require method signature adjustments to align with the LLM tool definitions. Will be invoked by `ChatService`. |
| `app/services/llm_service.py` | 🟡 Medium | Might need modifications to consistently handle passing `tools` and parsing `tool_calls` in the request/response cycle with the OpenRouter API. |

### 3.2 Breaking Changes

- [ ] **BC1:** No breaking changes are anticipated. This is an additive feature that extends existing chat functionality. If a user's prompt does not contain a tool-related intent, the behavior should remain unchanged.

### 3.3 Backward Compatibility Plan

```
Not applicable as no breaking changes are expected. The system will fall back to standard chat behavior if the tool-use intent is not detected by the LLM.
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Modern LLMs (via OpenRouter) and FastAPI fully support the tool-calling paradigm. The existing architecture is well-suited for this extension. |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | The project already involves interactions between multiple services and external APIs, demonstrating the required expertise. |
| Infrastructure รองรับหรือไม่? | ✅ | No new infrastructure is required. The feature will run on the existing application server. |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 3-5 days | Includes implementation, comprehensive testing, and potential refactoring of related services for cleaner integration. |
| **Deadline** | N/A |
| **Buffer Time** | 2 days |
| **Feasible?** | ✅ | The effort is reasonable for a single sprint. |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| Internal Development | N/A | Costs are related to developer time. |
| API Usage | Negligible | OpenRouter and GitHub API costs are expected to be minimal for the projected usage. |
| **Total** | N/A | |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| GitHub API Token | 🔴 Critical | The token must be loaded from a secure environment variable (`.env`) and never be hardcoded, logged, or exposed in API responses. |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| Prompt Injection | 🔴 High | An attacker could craft a prompt to make the LLM call `GithubService` with malicious parameters. Mitigation includes: 1. Strict sanitization and validation of all parameters received from the LLM before execution. 2. Limiting the GitHub token's scope to the absolute minimum required permissions (e.g., `repo`, `write:discussion`). 3. Avoiding the implementation of destructive functions (e.g., `delete_repository`). |

### 5.3 Authentication & Authorization

```
Authentication for GitHub actions will be handled by `GithubService`, which uses a single, system-level GitHub API token. There is no per-user authentication. Therefore, authorization is critical: the bot operates with the full permissions granted to its token. Access to the chat bot itself should be considered access to its underlying GitHub permissions.
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Response Time (Tool Call) | < 8 seconds | N/A |
| Throughput | N/A | Limited by LLM and GitHub API rate limits. |
| Error Rate | < 1% | For tool-calling operations. |

### 6.2 Scalability Plan

| Scenario | Expected Users | Scaling Strategy |
|----------|---------------|------------------|
| Normal | 1-5 | The current single-instance deployment is sufficient. The primary bottleneck would be external API rate limits, not application performance. |
| Peak | 1-5 | Same as Normal. |
| Growth (1yr) | 5-10 | The application is stateless and can be scaled horizontally if needed, but external API rate limits remain the main constraint. |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| `ChatService` Logic | Processes a simple conversational loop: `User -> LLM -> User`. | Orchestrates a complex tool-calling flow: `User -> LLM -> Tool -> LLM -> User`. | The entire orchestration logic, including tool definition management, `tool_call` parsing, tool execution, and result handling, is missing. |
| Service Interaction | `ChatService` primarily interacts with `LLMService`. | `ChatService` interacts with both `LLMService` and `GithubService`. | A direct communication channel and contract between `ChatService` and `GithubService` needs to be established. |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| Security Breach via Prompt Injection | 🟡 Medium | 🔴 High | 6 | Implement a strict allowlist and validation for all parameters passed to `GithubService`. Restrict GitHub token permissions to the minimum necessary scope. Log all actions for auditing. |
| Increased Response Latency | 🔴 High | 🟡 Medium | 6 | Provide immediate user feedback (e.g., "Executing GitHub action...") to manage expectations. Optimize `GithubService` methods. Explore streaming responses where possible. |
| Incorrect Tool Usage by LLM | 🟡 Medium | 🟡 Medium | 4 | Implement robust error handling in `ChatService` to catch malformed `tool_call` data from the LLM. Add comprehensive unit tests covering various LLM response formats. |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|------|--------|--------------|
| Requirement | ✅ Clear | The goal is to enable the chat assistant to use GitHub tools via natural language commands. |
| Feature | ✅ Defined | The workflow involves `ChatService` orchestrating between the LLM and `GithubService`. |
| Impact | 🟡 Medium | Major changes are localized to `ChatService`, with medium impact on adjacent services. |
| Feasibility | ✅ Feasible | The feature is technically straightforward with the current tech stack and team skills. |
| Security | ⚠️ Needs Review | The risk of prompt injection is the most significant concern and requires careful mitigation. |
| Performance | ✅ Acceptable | A slight increase in latency is expected but acceptable for tool-based interactions. |
| Risk | ⚠️ Some Risks | The primary risks are security-related and can be mitigated with careful implementation. |

### 9.2 Recommendations

1. **Prioritize Security:** Implement aggressive sanitization and validation of all data coming from the LLM before it is used to invoke `GithubService`. The GitHub token must have the principle of least privilege applied.
2. **Adopt TDD:** Start by writing a failing test in `test_chat_service.py` that simulates a user prompt and asserts that the correct `GithubService` method is called. This will guide the implementation.
3. **Start Small:** Begin by implementing one or two non-destructive GitHub functions (e.g., `create_issue`, `list_prs`) to build and test the end-to-end workflow before expanding the toolset.

### 9.3 Next Steps

- [ ] Create a feature branch `feature/32-github-function-calling`.
- [ ] Write a failing test case in `tests/services/test_chat_service.py` for the tool-calling logic.
- [ ] Implement the tool definition and orchestration logic in `app/services/chat_service.py` to make the test pass.
- [ ] Refactor the implementation and add more tests for edge cases and error handling.

---

## 📎 Appendix

### Related Documents

- N/A
- N/A
- N/A

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Luma AI | March 10, 2026 | ✅ |
| Tech Lead | [Name] | [Date] | ⬜ |
| PM | [Name] | [Date] | ⬜ |