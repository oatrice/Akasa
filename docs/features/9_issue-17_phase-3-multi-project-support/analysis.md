# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Chat-based Multi-Project Context Switching |
| **Issue URL** | [#17](https://github.com/oatrice/Luma/issues/17) |
| **Date** | March 8, 2026 |
| **Analyst** | Luma AI (Senior Technical Analyst) |
| **Priority** | 🔴 High |
| **Status** | 📝 Draft |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

```
The current system does not support managing multiple software projects through the chat interface. A user can only interact with one project at a time. This forces users to have separate, complex setups or manually reconfigure the tool to switch projects, which is inefficient and error-prone. The goal is to allow users to seamlessly switch between different project contexts within a single chat conversation.
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | Developer | switch the active project context directly within the chat | I can efficiently manage and issue commands for multiple projects without leaving the conversation. |
| 2 | Developer | clearly see which project is currently active | I can be confident that my commands are being sent to the correct project, preventing errors. |
| 3 | System | maintain a separate state for each project | I can prevent data collisions and ensure context integrity between different projects. |

### 1.3 Acceptance Criteria

- [ ] **AC1:** The user must be able to switch the active project using a slash command (e.g., `/project <project_name>`).
- [ ] **AC2:** After a successful switch, the system must send a confirmation message indicating the new active project (e.g., "Active project is now `my-other-project`.").
- [ ] **AC3:** If the specified project does not exist or the user lacks permission, the system must return an informative error message.
- [ ] **AC4:** All subsequent commands must be executed within the context of the newly activated project.

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[User wants to switch project] --> B{Enters `/project <project_name>` in chat}
    B --> C[System receives command]
    C --> D{Validate project name and user permissions}
    D -->|✅ Valid| E[Update session state to new project context]
    E --> F[Send confirmation message: "Active project is now <project_name>"]
    F --> G[End]
    D -->|❌ Invalid| H[Send error message: "Project not found or access denied."]
    H --> G
```

### 2.2 Screen/Page Requirements

| หน้าจอ | Actions | Components |
|--------|---------|------------|
| Chat Interface | - Type `/project <project_name>`<br>- View confirmation message<br>- View error message | - Text Input Field<br>- Message Display Area |

### 2.3 Input/Output Specification

#### Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `project_name` | string | ✅ | Must correspond to a valid, configured project alias. Must not be empty. |

#### Outputs

| Field | Type | Description |
|-------|------|-------------|
| `statusMessage` | string | A confirmation message on successful context switch. |
| `errorMessage` | string | An error message if the project is not found or access is denied. |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| **State Management** (`state_manager.py`) | 🔴 High | Core logic must be refactored to handle a dictionary of states, keyed by project ID, instead of a single global state. |
| **Command Parser** (`gemini_cli.py`) | 🔴 High | Must be updated to intercept and handle the new `/project` command before routing other commands. |
| **Backend API Clients** (`github_client.py`, etc.) | 🟡 Medium | All function calls that interact with external services must be modified to use the credentials and context of the currently active project. |
| **Configuration** (`config.py`) | 🟡 Medium | A new section may be required to define the list of available projects, their aliases, and associated credentials or paths. |
| **Authentication/Authorization Layer** | 🔴 High | Needs to be introduced or enhanced to check if a user is authorized to access a specific project upon switching. |

### 3.2 Breaking Changes

- [x] **BC1:** The on-disk state file format will be changed to support multiple projects. Old state files will become incompatible.
- [x] **BC2:** Functions and methods that previously operated on a global state will now require a `project_id` or `project_context` argument, causing a ripple effect across the codebase.

### 3.3 Backward Compatibility Plan

```
For a transition period, the system will support a migration path. On first run, if an old-format state file is detected, the application will automatically migrate it into the new multi-project structure, placing the existing state under a 'default' project. Users will be notified of the one-time migration. All API changes will be versioned to avoid breaking existing integrations.
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | State management and command parsing are standard programming tasks. No new technology is needed. |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | The required skills (Python, architectural design) are assumed to be present in the team. |
| Infrastructure รองรับหรือไม่? | ✅ | No changes to the existing infrastructure are required. |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 10-15 person-days |
| **Deadline** | N/A |
| **Buffer Time** | 3 days |
| **Feasible?** | ✅ | The effort is substantial but manageable within a typical development sprint. |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| Development Hours | Internal Cost | This is a core feature; budget is allocated from the main project development fund. |
| **Total** | Internal Cost | |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| Project-specific API Tokens | 🔴 Critical | Encrypt at rest in the state file. Inject into memory only when the project is active. Use strict access control. |
| Project configurations | 🟡 Sensitive | Access control on the configuration files and within the state management system. |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| Unauthorized Project Access | 🔴 High | Implement a robust authorization check that verifies user permissions against a project access control list (ACL) before allowing a context switch. |
| State File Tampering | 🟡 Medium | Use checksums or signatures to ensure the integrity of the state file. Encrypt sensitive values within the file. |

### 5.3 Authentication & Authorization

```
Authentication is handled by the chat platform (e.g., Telegram user ID). Authorization must be implemented on our backend. A mapping of `user_id` to a list of `authorized_project_ids` must be maintained. Every time a user attempts to switch to a project, the system must check if their `user_id` is in the authorized list for the target `project_id`. All subsequent commands must re-verify this authorization.
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Project Switch Time | < 500ms | N/A |
| Command Response Time | No degradation | ~200ms |
| Memory Usage | < +10% increase per project | N/A |

### 6.2 Scalability Plan

| Scenario | Expected Projects | Scaling Strategy |
|----------|---------------|------------------|
| Normal | 1-10 per user | A dictionary-based state manager provides O(1) lookup and will be sufficient. |
| Peak | 50+ per user | Continue with dictionary-based approach. Ensure state is loaded lazily if it becomes very large. |
| Growth (1yr) | 100+ per user | Same as peak. If state files become excessively large, consider a more robust storage solution like a local SQLite database. |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| State Management | Global, single-project state. | Per-project, namespaced state. | The entire state management system needs to be refactored to support a multi-tenant data structure. |
| Command Flow | All commands are processed directly. | A pre-processing step must identify and handle the `project` command. | Logic must be added to the main command loop to intercept context-switching commands. |
| Authorization | Implicit; access to the bot implies access to the project. | Explicit; user must be authorized for a specific project. | An access control layer needs to be designed and built. |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| State Corruption | 🟡 Medium | 🔴 High | 6 | Implement comprehensive unit and integration tests for the new state manager. Create atomic write operations for state changes. |
| Incorrect Command Routing | 🟡 Medium | 🔴 High | 6 | Ensure the active project context is clearly and persistently displayed to the user. Implement rigorous testing for the command router. |
| Poor User Experience | 🟡 Medium | 🟡 Medium | 4 | Choose the most intuitive interaction model (slash command is a good start). Provide clear, unambiguous feedback messages for all actions. |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|------|--------|--------------|
| Requirement | ✅ Clear | The need is to switch project contexts within a single chat. |
| Feature | ✅ Defined | A slash-command approach (`/project`) is well-defined and feasible. |
| Impact | 🔴 High | This is a foundational change affecting core architecture, especially state management and auth. |
| Feasibility | ✅ Feasible | The feature is technically feasible with existing team skills and poses no infrastructure challenges. |
| Security | ⚠️ Needs Review | Requires careful implementation of a new authorization layer to prevent data leakage between projects. |
| Performance | ✅ Acceptable | The proposed design should not introduce significant performance overhead. |
| Risk | ⚠️ Some Risks | Key risks are state corruption and incorrect command routing, which must be mitigated with thorough testing. |

### 9.2 Recommendations

1. **Adopt Approach 2 (Unified Channel):** Proceed with the unified channel approach using a `/project <name>` slash command. This is more scalable and provides a better UX than managing multiple chat channels.
2. **Prioritize State Manager Refactoring:** The first implementation step should be to redesign and refactor the `StateManager` to be project-aware. This is the most critical and impactful piece of work.
3. **Implement Strict Authorization:** A non-negotiable part of this feature is building an authorization layer. Do not allow project switching without verifying the user's permissions for the target project on the backend.

### 9.3 Next Steps

- [ ] Obtain stakeholder approval for the recommended approach and analysis.
- [ ] Create detailed technical tasks for refactoring `StateManager` and `Command Parser`.
- [ ] Design the data schema for the new configuration and state files.
- [ ] Develop a prototype for the `/project` command and the authorization check.

---

## 📎 Appendix

### Related Documents

- [Link to PRD]
- [Link to Design Docs]
- [Link to API Specs]

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Luma AI | March 8, 2026 | ✅ |
| Tech Lead | [Name] | [Date] | ⬜ |
| PM | [Name] | [Date] | ⬜ |