# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Antigravity IDE Action Confirmation via Akasa Bot (Telegram) |
| **Issue URL** | [#58](https://github.com/oatrice/Akasa/issues/58) |
| **Date** | 2026-03-13 |
| **Analyst** | Luma AI (Senior Technical Analyst) |
| **Priority** | 🔴 High |
| **Status** | 📝 Draft |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

```
นักพัฒนาที่ใช้ Antigravity AI coding IDE ต้องการกลไกในการยืนยัน action ที่มีความเสี่ยงที่ AI แนะนำก่อนที่จะ thực thi คำสั่งนั้นๆ คล้ายกับฟังก์ชันที่มีอยู่แล้วสำหรับ Gemini CLI แต่ปัจจุบันยังไม่มีช่องทางสำหรับ Antigravity IDE ในการร้องขอและรับการยืนยันจากผู้ใช้
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | Developer using Antigravity IDE | receive a confirmation request on my Telegram for actions proposed by the AI | I can securely review and approve or deny them before execution. |
| 2 | Akasa System | distinguish between action requests from Antigravity IDE and Gemini CLI | I can process them correctly and maintain a clear audit trail. |

### 1.3 Acceptance Criteria

- [ ] **AC1:** สร้าง MCP Server (`scripts/akasa_mcp_server.py`) ที่ expose tool `request_remote_approval` ได้
- [ ] **AC2:** Tool `request_remote_approval` ต้องรับ parameters: `command`, `cwd`, และ `description` (optional)
- [ ] **AC3:** เมื่อ tool ถูกเรียก, ระบบต้องส่ง action confirmation request ไปยัง Akasa Backend ซึ่งจะส่งต่อไปยัง Telegram พร้อมปุ่ม "Allow" และ "Deny"
- [ ] **AC4:** MCP Server ต้องใช้เทคนิค long-polling เพื่อรอผลการตอบกลับจากผู้ใช้ และคืนค่า 'allow' หรือ 'deny' กลับไปยัง Antigravity IDE
- [ ] **AC5:** Model `ActionRequestState` ใน Backend ต้องถูกแก้ไขเพื่อเพิ่ม field `source` (สำหรับแยก 'antigravity' vs 'gemini-cli') และ `description`

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    subgraph Antigravity IDE
        A[IDE triggers an action] --> B[Call request_remote_approval on MCP Server]
    end

    subgraph MCP Server (Local)
        B --> C[Send HTTP POST to Akasa Backend]
        C --> D[Long-poll Akasa Backend for status]
    end

    subgraph Akasa Backend
        C --> E{Create ActionRequestState}
        E --> F[Send notification via Telegram Service]
        F --> G((Wait for User))
        J[Telegram Callback updates ActionRequestState] --> K{State: Approved/Denied}
        D -- Polls --> K
    end

    subgraph User on Telegram
        F --> H[User receives confirmation message]
        H --> I{Clicks Allow/Deny}
        I --> J[Telegram sends callback to Akasa Backend]
    end

    subgraph MCP Server (Local)
        K -- Returns result --> L[Return result to Antigravity IDE]
    end
    
    subgraph Antigravity IDE
        L --> M{Execute or Abort Action}
        M --> N[End]
    end
```

### 2.2 Screen/Page Requirements

| หน้าจอ | Actions | Components |
|--------|---------|------------|
| Telegram Chat | - Review confirmation details<br>- Click "Allow"<br>- Click "Deny" | - Message text showing `command`, `cwd`, and `description`<br>- Inline keyboard with "Allow" and "Deny" buttons |

### 2.3 Input/Output Specification

#### Inputs

(To `request_remote_approval` tool)

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `command` | string | ✅ | Non-empty string |
| `cwd` | string | ✅ | Non-empty string, valid path format |
| `description` | string | ❌ | |

#### Outputs

(From `request_remote_approval` tool)

| Field | Type | Description |
|-------|------|-------------|
| `result` | string | The user's decision, either `"allow"` or `"deny"`. |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| `scripts/akasa_mcp_server.py` | 🔴 High | **New file.** เป็นหัวใจหลักของ feature นี้ ทำหน้าที่เป็น bridge ระหว่าง IDE และ Backend |
| `app/models/agent_state.py` | 🔴 High | **Model change.** ต้องแก้ไข `ActionRequestState` เพื่อเพิ่ม `source` และ `description` |
| `tests/` | 🟡 Medium | ต้องสร้าง test case ใหม่สำหรับ MCP server และอัปเดต test ที่เกี่ยวข้องกับ `ActionRequestState` |
| `app/routers/actions.py` | 🟡 Medium | อาจต้องมีการปรับ logic เพื่อรองรับ `source` และ `description` ที่เพิ่มเข้ามา |
| `app/services/telegram_service.py` | 🟢 Low | อาจมีการปรับเล็กน้อยเพื่อแสดง `description` ในข้อความที่ส่งไป Telegram |

### 3.2 Breaking Changes

- [ ] **BC1:** ไม่มีการเปลี่ยนแปลงที่เป็น Breaking Change การเพิ่ม field และ endpoint ใหม่ถูกออกแบบมาให้ backward compatible

### 3.3 Backward Compatibility Plan

```
การเพิ่ม `source` และ `description` ใน `ActionRequestState` จะเป็น field ที่ optional หรือมีค่า default เพื่อให้ request เดิมจาก Gemini CLI (Issue #49) ยังคงทำงานได้ตามปกติโดยไม่จำเป็นต้องแก้ไขฝั่ง client เดิม
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Project ใช้ Python/FastAPI ซึ่งรองรับการสร้าง HTTP server และ long-polling ได้ดีอยู่แล้ว |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | ทีมเคยพัฒนา feature ที่คล้ายกัน (Issue #49) มาแล้ว มีความเข้าใจใน flow เป็นอย่างดี |
| Infrastructure รองรับหรือไม่? | ✅ | ไม่ต้องการ infrastructure ใหม่ MCP server ถูกออกแบบมาให้ run บนเครื่อง local ของนักพัฒนา |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 2-3 days |
| **Deadline** | N/A |
| **Buffer Time** | 1 day |
| **Feasible?** | ✅ | |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| Development Time | N/A | ใช้ทรัพยากรภายใน |
| **Total** | N/A | |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| `command` to execute | 🔴 Critical | End-to-end encryption (HTTPS), user confirmation required |
| `cwd` (Current working directory) | 🟡 Sensitive | End-to-end encryption (HTTPS) |
| User Telegram ID | 🔴 Critical | Stored securely in database, access control |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| Unauthorized access to MCP Server | 🔴 High | - MCP Server ต้อง bind กับ `localhost` เป็น default<br>- แนะนำในเอกสารให้ระวังการ expose port นี้<br>- พิจารณาเพิ่ม token-based authentication สำหรับ MCP server |
| Request Forgery to Akasa Backend | 🟡 Medium | Endpoint ที่รับ request จาก MCP server ต้องใช้ Authentication (เช่น API Key) แบบเดียวกับ endpoint อื่นๆ |
| Malicious command in description | 🟢 Low | `description` field ควรถูก sanitize ก่อนแสดงผลใน Telegram เพื่อป้องกัน injection attack |

### 5.3 Authentication & Authorization

```
- **Antigravity IDE -> MCP Server:** ไม่มีการยืนยันตัวตนในเบื้องต้น เนื่องจากทำงานบนเครื่องเดียวกัน (localhost)
- **MCP Server -> Akasa Backend:** MCP Server ต้องใช้ API Key ในการยืนยันตัวตนกับ Akasa Backend
- **User -> Akasa Backend:** ผู้ใช้ยืนยันตัวตนผ่าน Telegram session ของตนเองเมื่อกดปุ่ม Allow/Deny
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| End-to-end confirmation time | < 30s (user-dependent) | N/A |
| Backend response (after user action) | < 500ms | N/A |
| Throughput | Low (not a critical metric) | N/A |

### 6.2 Scalability Plan

| Scenario | Expected Users | Scaling Strategy |
|----------|---------------|------------------|
| Normal | ~1-10 concurrent requests | Long-polling เป็นวิธีที่ยอมรับได้สำหรับ use case นี้ |
| Growth (1yr) | ~10-50 concurrent requests | หากมีผู้ใช้มากขึ้น อาจพิจารณาเปลี่ยนจาก long-polling เป็น WebSockets หรือ Server-Sent Events เพื่อลดภาระของ server |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| Client Support | รองรับ Gemini CLI | รองรับ Antigravity IDE เพิ่มเติม | ต้องสร้าง `akasa_mcp_server.py` เพื่อเป็น bridge ให้ Antigravity IDE |
| Data Model | `ActionRequestState` ไม่มีข้อมูล source | `ActionRequestState` มี `source` และ `description` | ต้องแก้ไข Pydantic model ใน `app/models/agent_state.py` |
| Entrypoint | รับ request ผ่าน API ปกติ | รับ request ผ่าน MCP Server | ต้องมี script ที่ run เป็น server แยกต่างหาก |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| Security flaw in MCP server allows remote code execution | 🟡 Medium | 🔴 High | 6 | - Bind server to localhost by default.<br>- Add clear security warnings in documentation.<br>- Implement a simple secret token auth between IDE and MCP server. |
| Long-polling timeouts or instability | 🟢 Low | 🟡 Medium | 2 | - Implement robust error handling and reasonable timeout values.<br>- Add logging to monitor polling status.<br>- Have a fallback plan to switch to WebSockets if needed. |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|------|--------|--------------|
| Requirement | ✅ Clear | Requirement ชัดเจนและต่อยอดจาก feature เดิม |
| Feature | ✅ Defined | Flow การทำงานและส่วนประกอบต่างๆ ถูกกำหนดไว้ครบถ้วน |
| Impact | 🟡 Medium | กระทบหลายส่วน แต่ส่วนใหญ่เป็นการเพิ่มของใหม่ ไม่ใช่การแก้ไขของเก่า |
| Feasibility | ✅ Feasible | สามารถทำได้จริงด้วยเทคโนโลยีและ skill ที่มีอยู่ |
| Security | ⚠️ Needs Review | มีความเสี่ยงด้านความปลอดภัยที่ MCP server ซึ่งต้องจัดการอย่างรัดกุม |
| Performance | ✅ Acceptable | Long-polling เหมาะสมกับภาระงานที่คาดการณ์ไว้ |
| Risk | 🟡 Medium | ความเสี่ยงหลักอยู่ที่ความปลอดภัยของ endpoint ใหม่ ซึ่งมีแผนลดความเสี่ยงแล้ว |

### 9.2 Recommendations

1. **Implement with Security First:** ให้ความสำคัญสูงสุดกับการป้องกัน MCP Server โดยการ bind กับ localhost เป็น default และพิจารณาเพิ่ม token auth
2. **Ensure Backward Compatibility:** แก้ไข data model โดยให้ field ใหม่เป็น optional เพื่อไม่ให้กระทบ client เดิม
3. **Develop Comprehensive Tests:** สร้าง Unit test และ Integration test สำหรับ MCP server workflow ทั้งหมด ตั้งแต่การรับ request, polling, จนถึงการคืนค่า

### 9.3 Next Steps

- [ ] สร้าง feature branch ใหม่ใน Git
- [ ] แก้ไข `app/models/agent_state.py` และ test ที่เกี่ยวข้อง
- [ ] สร้างและพัฒสนา `scripts/akasa_mcp_server.py`
- [ ] สร้าง test case ใหม่สำหรับ `akasa_mcp_server.py`
- [ ] ทดสอบ integration ทั้งระบบ

---

## 📎 Appendix

### Related Documents

- [Issue #49: Remote Action Confirmation via Akasa Bot](https://github.com/oatrice/Akasa/issues/49)

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Luma AI | 2026-03-13 | ✅ |
| Tech Lead | [Name] | [Date] | ⬜ |
| PM | [Name] | [Date] | ⬜ |