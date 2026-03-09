# Specification: รองรับการส่งข้อความเชิงรุกใน TelegramService

## 1. ภาพรวม

เพิ่มความสามารถใหม่ให้กับระบบ (Akasa) ในการส่งข้อความไปยังผู้ใช้ Telegram ได้โดยตรง โดยไม่จำเป็นต้องรอให้ผู้ใช้ส่งข้อความเข้ามาหาบอทก่อน (Proactive Messaging) คุณสมบัตินี้จำเป็นสำหรับฟีเจอร์ในอนาคต เช่น การส่งการแจ้งเตือน, การรายงานผลลัพธ์ของงานที่ใช้เวลานาน, หรือการส่งข่าวสารไปยังผู้ใช้

หัวใจหลักของฟีเจอร์นี้คือการสร้าง method ใหม่ใน `TelegramService` ที่รับ `user_id` และข้อความ จากนั้นไปค้นหา `chat_id` ที่ผูกกับผู้ใช้นั้นๆ จากฐานข้อมูล (Redis) เพื่อส่งข้อความออกไป พร้อมทั้งจัดการข้อผิดพลาดที่อาจเกิดขึ้น เช่น หาผู้ใช้ไม่เจอ หรือบอทถูกบล็อก

## 2. เป้าหมายของผู้ใช้ (User Goal)

ในฐานะนักพัฒนาหรือผู้ดูแลระบบ (System Admin) ฉันต้องการส่งข้อความที่สำคัญไปยังผู้ใช้ Telegram ได้ทันที เพื่อแจ้งข้อมูลข่าวสาร, แจ้งเตือนสถานะ, หรือผลลัพธ์ของการดำเนินการบางอย่าง โดยไม่ต้องรอให้ผู้ใช้เป็นฝ่ายเริ่มต้นบทสนทนา

## 3. เส้นทางของผู้ใช้ / User Stories

- **Story 1: แจ้งเตือนเมื่อทำงานเสร็จ**
  - **As a** developer,
  - **I want** the system to send a message to a user
  - **So that** they are notified when their long-running task (e.g., "generate a project summary") is complete.

- **Story 2: ส่งข้อความแจ้งข่าวสาร**
  - **As a** system admin,
  - **I want** to be able to send a maintenance announcement to a specific user
  - **So that** they are aware of upcoming service downtime.

## 4. ข้อกำหนดเชิงฟังก์ชัน (Functional Requirements)

- **FR1:** `TelegramService` ต้องมี public method ใหม่ชื่อ `send_proactive_message(user_id: str, text: str)`
- **FR2:** Method นี้ต้องรับ `user_id` ของ Telegram (unique identifier ของผู้ใช้) และ `text` ที่เป็นข้อความที่ต้องการส่ง
- **FR3:** ระบบจะต้องใช้ `user_id` ที่ได้รับมาเพื่อค้นหา `chat_id` ที่สอดคล้องกันซึ่งถูกเก็บไว้ใน Redis
- **FR4:** **กรณีสำเร็จ:** หากพบ `chat_id` ที่ถูกต้อง ระบบจะต้องเรียกใช้ Telegram Bot API เพื่อส่งข้อความ (`text`) ไปยัง `chat_id` นั้น
- **FR5:** **กรณีไม่พบผู้ใช้:** หากไม่พบ `chat_id` ที่ผูกกับ `user_id` ใน Redis ระบบจะต้องล้มเหลวอย่างปลอดภัย (Graceful Failure) โดยอาจจะคืนค่าเป็น `False` หรือ raise exception ที่ระบุชัดเจน และต้องมีการบันทึก Log
- **FR6:** **กรณีบอทถูกบล็อก:** หาก Telegram API ตอบกลับมาด้วยข้อผิดพลาดที่บ่งชี้ว่าผู้ใช้ได้บล็อกบอทไปแล้ว (เช่น HTTP 403 Forbidden: "bot was blocked by the user") ระบบจะต้องจัดการกับข้อผิดพลาดนี้โดยเฉพาะ, บันทึก Log สาเหตุ, และไม่พยายามส่งซ้ำ

## 5. ข้อกำหนดที่ไม่ใช่เชิงฟังก์ชัน (Non-Functional Requirements)

- **NFR1 - การจัดการข้อผิดพลาด (Error Handling):** การจัดการข้อผิดพลาดต้องมีความชัดเจน สามารถแยกแยะระหว่าง "ไม่พบผู้ใช้" (User Not Found) และ "ส่งไม่สำเร็จเพราะบอทถูกบล็อก" (Send Failed/Blocked) ได้
- **NFR2 - การบันทึกข้อมูล (Logging):** ทุกความพยายามในการส่งข้อความ (ทั้งสำเร็จและล้มเหลว) จะต้องถูกบันทึกไว้ใน Log พร้อมระบุ `user_id` และสาเหตุของความล้มเหลวอย่างชัดเจน

## 6. ข้อกำหนดตามตัวอย่าง (Specification by Example - SBE)

### Scenario 1: ส่งข้อความสำเร็จ (Happy Path)

- **Given**
  - ผู้ใช้ที่มี `user_id` คือ `112233` ได้เคยพูดคุยกับบอทแล้ว
  - และระบบได้จัดเก็บ `chat_id` ของผู้ใช้คนนี้ (`998877`) ไว้ใน Redis เรียบร้อยแล้ว

- **When**
  - ระบบส่วนอื่น (เช่น background worker) เรียกใช้ `TelegramService.send_proactive_message`
  
  | Parameter | Value |
  |-----------|-------|
  | `user_id` | `"112233"` |
  | `text` | `"รายงานของคุณพร้อมให้ดาวน์โหลดแล้ว"` |

- **Then**
  - ระบบจะส่งข้อความ "รายงานของคุณพร้อมให้ดาวน์โหลดแล้ว" ไปยังผู้ใช้ที่มี `chat_id` คือ `998877` ผ่าน Telegram API ได้สำเร็จ
  - Method คืนค่า `True`

---

### Scenario 2: ส่งข้อความไม่สำเร็จเพราะไม่พบผู้ใช้ในระบบ

- **Given**
  - ไม่มีข้อมูล `chat_id` ของผู้ใช้ที่มี `user_id` `"555555"` ถูกเก็บไว้ใน Redis

- **When**
  - ระบบเรียกใช้ `TelegramService.send_proactive_message`

  | Parameter | Value |
  |-----------|-------|
  | `user_id` | `"555555"` |
  | `text` | `"Hello!"` |

- **Then**
  - ระบบค้นหา `chat_id` ใน Redis แล้วไม่พบ
  - ระบบ **ต้องไม่** เรียกใช้ Telegram API
  - ระบบบันทึก Log ข้อผิดพลาดว่า "User not found" หรือ "Chat ID not found for user_id: 555555"
  - Method คืนค่า `False` หรือ raise `UserNotFoundException`

---

### Scenario 3: ส่งข้อความไม่สำเร็จเพราะผู้ใช้บล็อกบอท

- **Given**
  - ผู้ใช้ที่มี `user_id` คือ `443322` มีข้อมูล `chat_id` (`123123`) ถูกต้องอยู่ใน Redis
  - แต่ผู้ใช้คนดังกล่าวได้ทำการบล็อกบอทในแอป Telegram ไปแล้ว

- **When**
  - ระบบเรียกใช้ `TelegramService.send_proactive_message`

  | Parameter | Value |
  |-----------|-------|
  | `user_id` | `"443322"` |
  | `text` | `"Maintenance notice"` |

- **Then**
  - ระบบค้นหา `chat_id` ใน Redis เจอ และเรียกใช้ Telegram API เพื่อส่งข้อความ
  - Telegram API ตอบกลับด้วยสถานะ Error (เช่น HTTP 403 Forbidden) พร้อมเหตุผลว่า "bot was blocked by the user"
  - ระบบจัดการกับ Error นี้และบันทึก Log ที่เฉพาะเจาะจงว่า "Failed to send message to user_id 443322: Bot was blocked"
  - Method คืนค่า `False` หรือ raise `BotBlockedException`

## 7. สิ่งที่ไม่อยู่ในขอบเขต (Out of Scope)

- กลไกการจัดเก็บ `chat_id` ของผู้ใช้ในครั้งแรก (ถือว่ามีอยู่แล้วในระบบ)
- การสร้างฟีเจอร์สำหรับ "กระจายข้อความ" (Broadcast) ไปยังผู้ใช้ทุกคนพร้อมกัน (สเปคนี้เน้นการส่งหาผู้ใช้ทีละคน)
- ส่วนติดต่อผู้ใช้ (UI) หรือตัวกระตุ้น (Trigger) ที่จะมาเรียกใช้ฟังก์ชันนี้ (สเปคนี้ครอบคลุมแค่การทำงานในระดับ Service เท่านั้น)