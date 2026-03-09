# Luma Code Review Report

**Date:** 2026-03-09 16:04:56
**Files Reviewed:** ['docs/features/11_issue-30_service-support-outbound-messaging-in-telegramservice/plan.md', 'tests/services/test_redis_service.py']

## 📝 Reviewer Feedback

PASS

## 🧪 Test Suggestions

### คู่มือการตรวจสอบด้วยตนเอง

คู่มือนี้จะช่วยให้คุณตรวจสอบการเปลี่ยนแปลงล่าสุดที่เกี่ยวข้องกับฟีเจอร์การเลือกโมเดล AI, การจัดการบริบทโปรเจกต์, และการส่งข้อความเชิงรุก (Proactive Messaging)

---

### 1. การเตรียมการ

1.  **ตั้งค่าสภาพแวดล้อม**: ตรวจสอบให้แน่ใจว่าคุณได้ติดตั้ง dependencies ที่จำเป็นทั้งหมดแล้ว (`pip install -r requirements.txt`)
2.  **รันแอปพลิเคชัน**: เริ่มต้น Akasa Backend Server ในโหมด Development:
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```
3.  **ตั้งค่า API Key (สำหรับการทดสอบ Proactive Messaging)**:
    *   สร้างไฟล์ `.env` (หากยังไม่มี) ใน root ของโปรเจกต์
    *   เพิ่ม Master API Key สำหรับการทดสอบ Endpoint การส่งข้อความ:
        ```env
        # .env
        # ... (Your other settings)
        AKASA_API_KEY=your_secret_master_api_key_for_testing
        ```
        *(แทนที่ `your_secret_master_api_key_for_testing` ด้วยคีย์ที่คุณต้องการ)*
4.  **Telegram User ID**: เตรียม Telegram User ID ของคุณ (หาได้จากบอทอย่าง `@userinfobot`)

---

### 2. ทดสอบการเลือกโมเดล AI (`/model` command)

1.  **เปิด Telegram**: ไปที่แชทกับ Akasa Bot ของคุณ
2.  **ส่งคำสั่ง `/model`**: พิมพ์ `/model` แล้วกด Enter
    *   **ผลลัพธ์ที่คาดหวัง**: บอทควรตอบกลับด้วยข้อความที่แสดงโมเดลปัจจุบันที่ใช้งานอยู่ (เช่น `Current model: Google Gemini 2.5 Flash (default)`) และรายการโมเดลอื่นๆ ที่สามารถเลือกใช้ได้ พร้อม Alias ของแต่ละโมเดล
3.  **เปลี่ยนโมเดล**: พิมพ์คำสั่งเพื่อเปลี่ยนโมเดล เช่น `/model claude` (หาก `claude` เป็น Alias ที่ถูกต้อง)
    *   **ผลลัพธ์ที่คาดหวัง**: บอทควรตอบกลับข้อความยืนยันการเปลี่ยนโมเดล เช่น `Model selection updated to: Claude 3.5 Sonnet (Paid)`
4.  **ทดสอบโมเดลที่ไม่ถูกต้อง**: พิมพ์คำสั่งด้วย Alias ที่ไม่มีอยู่จริง เช่น `/model invalid_model`
    *   **ผลลัพธ์ที่คาดหวัง**: บอทควรตอบกลับข้อความแจ้งข้อผิดพลาดที่ระบุว่า Alias ไม่ถูกต้อง พร้อมแสดงรายการ Alias ที่มีให้เลือก
5.  **ทดสอบการใช้งานโมเดลที่เลือก**: หลังจากเปลี่ยนโมเดลแล้ว ให้ลองส่งข้อความทั่วไป เช่น "What is Python?"
    *   **ผลลัพธ์ที่คาดหวัง**: คำตอบที่ได้รับควรจะมาจากโมเดลที่คุณเพิ่งเลือก (เช่น Claude)

---

### 3. ทดสอบการจัดการบริบทโปรเจกต์ (`/project` และ `/note` commands)

1.  **เตรียมข้อมูล**:
    *   ตรวจสอบให้แน่ใจว่าคุณมีโปรเจกต์อย่างน้อย 2 โปรเจกต์ที่ Akasa รู้จัก (เช่น `default` และ `akasa-api` จากการตั้งค่า หรือสร้างเพิ่มหากจำเป็น)
    *   คุณอาจต้องทดสอบด้วยโปรเจกต์ที่มี "Agent State" บันทึกไว้ และโปรเจกต์ที่ไม่มี
2.  **ทดสอบการสลับโปรเจกต์**:
    *   พิมพ์คำสั่ง `/project select <project_name>` เช่น `/project select akasa-api`
    *   **ผลลัพธ์ที่คาดหวัง**:
        *   หาก `akasa-api` มี Agent State ที่บันทึกไว้ (เช่น `current_task`, `focus_file`) บอทควรตอบกลับด้วยข้อความ "Welcome back..." ที่สรุปบริบทนั้นๆ เช่น `✅ Switched to project akasa-api. Welcome back! We were last working on: Fixing the Redis migration bug in app/services/redis_service.py.`
        *   หาก `akasa-api` ไม่มี Agent State บอทควรตอบกลับข้อความยืนยันการสลับโปรเจกต์ที่เรียบง่ายกว่า เช่น `✅ Switched to project akasa-api.`
3.  **ทดสอบการบันทึก Note (`/note`)**:
    *   พิมพ์คำสั่ง `/note <your task description>` เช่น `/note Working on the new notification endpoint.`
    *   **ผลลัพธ์ที่คาดหวัง**: บอทควรตอบกลับข้อความยืนยันว่า Note ถูกบันทึกแล้ว เช่น `✅ Note saved for project akasa-api.`
4.  **ทดสอบการกลับมายังโปรเจกต์ที่อัปเดต Note**:
    *   หลังจากบันทึก Note ด้วยคำสั่ง `/note` ให้ลองสลับกลับไปยังโปรเจกต์นั้นอีกครั้ง โดยใช้คำสั่ง `/project select <project_name>` เดิม
    *   **ผลลัพธ์ที่คาดหวัง**: เมื่อสลับกลับมา บอทควรแสดงข้อความ Welcome back พร้อมกับ Task ล่าสุดที่คุณบันทึกไว้ด้วยคำสั่ง `/note`

---

### 4. ทดสอบการส่งข้อความเชิงรุก (Proactive Messaging)

การทดสอบส่วนนี้จะทำผ่าน Endpoint API ชั่วคราวที่สร้างขึ้นมาเพื่อการทดสอบโดยเฉพาะ

1.  **เปิดไฟล์ `app/main.py`**: (หากยังไม่ได้ทำจากคู่มือก่อนหน้า)
2.  **เพิ่ม Endpoint ชั่วคราว**: ตรวจสอบให้แน่ใจว่าโค้ดสำหรับ Endpoint `/test_proactive/{user_id}` ถูกเพิ่มเข้าไปในไฟล์ `app/main.py` แล้ว (ตามที่ได้แนะนำไปในคู่มือการตรวจสอบก่อนหน้านี้)
3.  **ตรวจสอบการ Mapping ID**:
    *   ส่งข้อความใดๆ ไปหา Akasa Bot ใน Telegram ก่อน 1 ครั้ง เพื่อให้ระบบบันทึก `user_id` และ `chat_id` ของคุณลงใน Redis (ขั้นตอนนี้สำคัญมากเพื่อให้ `send_proactive_message` หา `chat_id` เจอ)
4.  **ทดสอบ Happy Path**:
    *   เปิด Terminal แล้วรันคำสั่ง `curl` โดยแทนที่ `{YOUR_USER_ID}` ด้วย Telegram User ID ของคุณ:
        ```bash
        curl -X POST http://localhost:8000/test_proactive/{YOUR_USER_ID} -H "X-Akasa-API-Key: your_secret_master_api_key_for_testing" -H "Content-Type: application/json" -d '{"user_id": "REPLACE_WITH_YOUR_USER_ID", "message": "This is a proactive test message via API.", "priority": "high", "metadata": {"source": "manual_test"}}'
        ```
        *(แทนที่ `REPLACE_WITH_YOUR_USER_ID` ด้วย User ID ของคุณอีกครั้งใน JSON payload)*
    *   **ผลลัพธ์ที่คาดหวัง**: คุณควรได้รับข้อความ "This is a proactive test message via API." ในแอป Telegram ของคุณทันที และ `curl` ควรแสดงผลลัพธ์เป็น:
        ```json
        {"status": "success", "message": "Notification queued for delivery."}
        ```
5.  **ทดสอบกรณีไม่พบผู้ใช้**:
    *   รันคำสั่ง `curl` อีกครั้ง แต่ใช้ `user_id` ที่ไม่มีการ Mapping ไว้ใน Redis (เช่น ID ปลอมที่ไม่เคยคุยกับบอท):
        ```bash
        curl -X POST http://localhost:8000/test_proactive/12345 -H "X-Akasa-API-Key: your_secret_master_api_key_for_testing" -H "Content-Type: application/json" -d '{"user_id": "12345", "message": "This should fail, user not found.", "priority": "normal"}'
        ```
    *   **ผลลัพธ์ที่คาดหวัง**: คุณต้อง **ไม่** ได้รับข้อความใดๆ ใน Telegram และ `curl` ควรแสดงผลลัพธ์เป็น:
        ```json
        {"status": "failed", "reason": "User not found in Redis."}
        ```
6.  **ทดสอบกรณี API Key ไม่ถูกต้อง**:
    *   รันคำสั่ง `curl` โดยใช้ API Key ที่ไม่ถูกต้อง:
        ```bash
        curl -X POST http://localhost:8000/test_proactive/{YOUR_USER_ID} -H "X-Akasa-API-Key: wrong-api-key" -H "Content-Type: application/json" -d '{"user_id": "{YOUR_USER_ID}", "message": "Test with wrong key", "priority": "normal"}'
        ```
    *   **ผลลัพธ์ที่คาดหวัง**: `curl` ควรแสดงผลลัพธ์เป็น:
        ```json
        {"detail": "Invalid or missing API key"}
        ```
        และควรได้รับ HTTP Status Code `401 Unauthorized`

7.  **ทดสอบกรณี Payload ไม่ถูกต้อง**:
    *   รันคำสั่ง `curl` โดยส่ง Payload ที่ขาดฟิลด์ที่จำเป็น เช่น ไม่ใส่ `user_id`:
        ```bash
        curl -X POST http://localhost:8000/test_proactive/{YOUR_USER_ID} -H "X-Akasa-API-Key: your_secret_master_api_key_for_testing" -H "Content-Type: application/json" -d '{"message": "Missing user_id", "priority": "normal"}'
        ```
    *   **ผลลัพธ์ที่คาดหวัง**: `curl` ควรแสดงผลลัพธ์เป็นข้อผิดพลาดเกี่ยวกับ Validation และควรได้รับ HTTP Status Code `400 Bad Request` เช่น:
        ```json
        {"detail": "user_id is required"}
        ```

---

### 5. การลบโค้ดทดสอบ (หลังจากเสร็จสิ้น)

เมื่อการทดสอบเสร็จสมบูรณ์และคุณพอใจกับผลลัพธ์แล้ว ให้ลบ Endpoint ชั่วคราว (`/test_proactive/{user_id}`) ที่เพิ่มเข้าไปใน `app/main.py` เพื่อรักษาความปลอดภัยและโครงสร้างโค้ดให้สะอาด

