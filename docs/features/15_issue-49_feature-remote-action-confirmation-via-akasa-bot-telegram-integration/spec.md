# Specification: Remote Action Confirmation via Akasa Bot

## 1. ภาพรวม (Overview)

เอกสารนี้ระบุคุณสมบัติ (Feature) และพฤติกรรมของระบบสำหรับการยืนยันการกระทำ (Action) ระยะไกลผ่าน Telegram Bot (Akasa Bot) ซึ่งเป็นส่วนหนึ่งของการทำงานของ Gemini CLI

- **Feature:** Remote Action Confirmation via Akasa Bot (Telegram Integration)
- **Issue:** [#49](https://github.com/oatrice/Akasa/issues/49)

## 2. เป้าหมายและคุณค่า (Goal & Value)

**Goal:** เพิ่มความสามารถให้ Gemini CLI สามารถส่งคำขออนุมัติการกระทำที่ละเอียดอ่อน (เช่น การรัน Shell Command) ไปยังผู้ใช้ผ่าน Telegram ได้ เพื่อให้ผู้ใช้สามารถตรวจสอบและตัดสินใจ "อนุญาต" (Allow) หรือ "ปฏิเสธ" (Deny) จากระยะไกลได้แบบ Real-time

**User Story:** ในฐานะนักพัฒนาที่ใช้ Gemini CLI สำหรับงานที่ใช้เวลานาน (Long-running task) หรือรันบนเซิร์ฟเวอร์ ฉันต้องการได้รับการแจ้งเตือนบน Telegram เมื่อ CLI ต้องการสิทธิ์ในการรันคำสั่งที่อาจมีความเสี่ยง เพื่อให้ฉันสามารถควบคุมความปลอดภัยของระบบและอนุมัติการทำงานได้จากทุกที่ ทุกเวลา โดยไม่จำเป็นต้องอยู่หน้าจอเทอร์มินัลตลอดเวลา

## 3. ผู้เกี่ยวข้องและระบบ (Actors & Systems)

- **Developer:** ผู้ใช้งาน Gemini CLI และเป็นผู้รับการแจ้งเตือนและตัดสินใจผ่านแอปพลิเคชัน Telegram
- **Gemini CLI:** แอปพลิเคชัน Command-Line ที่เป็นผู้ริเริ่มคำสั่ง และจะเข้าสู่สถานะรอ (Waiting) การยืนยันจากผู้ใช้
- **Akasa Backend:** เซิร์ฟเวอร์ตัวกลาง (FastAPI) ที่ทำหน้าที่:
    1.  รับคำขอยืนยันจาก Gemini CLI
    2.  ส่งการแจ้งเตือนไปยังผู้ใช้ผ่าน Telegram Bot
    3.  จัดการสถานะของคำขอ (Pending, Allowed, Denied)
    4.  ส่งผลลัพธ์การตัดสินใจกลับไปยัง Gemini CLI
- **Telegram Bot (Akasa Bot):** Bot ที่แสดงข้อความและปุ่ม Inline Keyboard (Allow/Deny) ให้ผู้ใช้โต้ตอบ

## 4. ข้อกำหนดการทำงาน (Functional Requirements)

- **FR1: Initiation from Gemini CLI**
    - Gemini CLI ต้องมีโหมดการทำงาน "Remote Confirmation"
    - เมื่อมีการเรียกใช้เครื่องมือที่กำหนดค่าว่าเป็น "Sensitive" (เช่น `run_shell_command`) และเปิดใช้งานโหมด Remote Confirmation, CLI จะต้องไม่แสดง Prompt ในเทอร์มินัล
    - CLI จะต้องส่ง HTTP POST request ไปยัง Endpoint ของ Akasa Backend (`/api/v1/notifications/send`) พร้อมข้อมูลของ Action ที่ต้องการยืนยัน
    - หลังจากส่งคำขอแล้ว CLI จะต้องเข้าสู่สถานะ "Polling" เพื่อรอผลการยืนยันจาก Akasa Backend

- **FR2: Akasa Backend Request Handling & Notification**
    - Akasa Backend ต้องมี Endpoint (`/api/v1/notifications/send`) สำหรับรับคำขอยืนยัน
    - เมื่อได้รับคำขอ Backend จะต้อง:
        1.  สร้าง `request_id` ที่ไม่ซ้ำกันสำหรับแต่ละคำขอ
        2.  จัดเก็บข้อมูลคำขอและสถานะเริ่มต้น (`pending`) ใน Redis โดยใช้ `request_id` เป็น Key
        3.  ส่งข้อความไปยัง Telegram Chat ID ที่กำหนดไว้ พร้อมรายละเอียดของ Action และปุ่ม Inline Keyboard (`✅ Allow`, `❌ Deny`)

- **FR3: User Interaction on Telegram**
    - ผู้ใช้จะได้รับข้อความแจ้งเตือนบน Telegram ที่แสดงรายละเอียดของคำสั่งที่รอการอนุมัติ
    - ผู้ใช้สามารถกดปุ่ม `✅ Allow` หรือ `❌ Deny` ได้เพียงครั้งเดียว
    - เมื่อผู้ใช้กดปุ่ม Telegram จะส่ง Callback Query ไปยัง Akasa Backend

- **FR4: Akasa Backend Callback Handling & State Update**
    - Akasa Backend จะต้องรับ Callback Query จาก Telegram
    - Backend จะต้องอัปเดตสถานะของคำขอใน Redis ตามที่ผู้ใช้ตัดสินใจ (`allowed` หรือ `denied`)
    - ข้อความใน Telegram ควรได้รับการอัปเดตเพื่อแสดงผลการตัดสินใจ (เช่น "✅ Allowed by [Username]") และปิดการใช้งานปุ่ม

- **FR5: Resolution for Gemini CLI**
    - Gemini CLI ที่กำลัง Polling จะต้องได้รับสถานะใหม่ (`allowed` หรือ `denied`) จาก Akasa Backend
    - หากสถานะเป็น `allowed`, CLI จะต้องดำเนินการรันคำสั่งเดิมต่อไป
    - หากสถานะเป็น `denied`, CLI จะต้องยกเลิกการกระทำนั้นและแสดงข้อความแจ้งว่า "Action denied by user" ในเทอร์มินัล

## 5. ข้อกำหนดด้านข้อมูล (Data Specification)

- **Notification Request Payload (CLI -> Akasa)**
    ```json
    {
      "chat_id": "YOUR_TELEGRAM_CHAT_ID",
      "message": "Action Required: Execute Shell Command",
      "metadata": {
        "request_id": "uuid-for-this-request",
        "command": "gh pr create --title \"My New Feature\" --body \"...\"",
        "cwd": "/path/to/project",
        "type": "shell_command_confirmation"
      }
    }
    ```
- **State Data in Redis**
    ```json
    // Key: "action_request:<request_id>"
    // Value (JSON String):
    {
      "status": "pending", // pending | allowed | denied
      "command": "gh pr create --title \"My New Feature\" --body \"...\"",
      "cwd": "/path/to/project",
      "requested_at": "2024-08-01T10:00:00Z",
      "decided_by": null, // Telegram Username after decision
      "decided_at": null
    }
    ```

## 6. Specification by Example (SBE)

### **Scenario 1: ผู้ใช้อนุญาต (Happy Path)**

| Actor         | Action                                                                                                                                              |
| :------------ | :------------------------------------------------------------------------------------------------------------------------------------------------