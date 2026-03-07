# Specification: [Phase 2] Code Formatting in Chat

| | |
|---|---|
| **Feature Name** | [Phase 2] Code formatting ใน chat |
| **Issue URL** | [#7](https://github.com/oatrice/Akasa/issues/7) |
| **Status** | **Draft** |
| **Date** | 2026-03-07 |

## 1. เป้าหมาย (The 'Why')

เพื่อปรับปรุงประสบการณ์การใช้งาน (User Experience) ของ Akasa Chatbot โดยทำให้ Code Snippet ที่บอทส่งกลับมาแสดงผลได้อย่างสวยงามและอ่านง่ายบนหน้าจอแชท การจัดรูปแบบโค้ดที่ถูกต้อง (Code Formatting) และการเน้นสีของ Syntax (Syntax Highlighting) เป็นสิ่งจำเป็นสำหรับเครื่องมือที่เกี่ยวข้องกับการเขียนโค้ด

## 2. ผู้ใช้งาน (User Persona)

| Persona | ลักษณะ |
|---|---|
| **End User** | ผู้ใช้งานที่สนทนากับบอทและได้รับ Code Snippet เป็นส่วนหนึ่งของคำตอบ และต้องการอ่านโค้ดนั้นได้ง่ายๆ บนมือถือ |

## 3. เส้นทางของผู้ใช้ (User Journey)

**ในฐานะ**ผู้ใช้งาน
**ฉันต้องการ** ให้โค้ดที่บอทส่งมาถูกจัดรูปแบบเป็น Code Block ที่ชัดเจน
**เพื่อที่ฉันจะ** สามารถอ่าน, ทำความเข้าใจ, และคัดลอกโค้ดไปใช้งานต่อได้อย่างสะดวก

## 4. เกณฑ์การยอมรับ (Acceptance Criteria)

- [ ] เมื่อข้อความที่บอทจะส่งกลับมี Markdown code block (เช่น ```python...```), ข้อความนั้นจะต้องถูกส่งไปหา Telegram API โดยตั้งค่า `parse_mode` เป็น `MarkdownV2`
- [ ] ข้อความที่อยู่นอก Code Block จะต้องถูก "escape" อย่างถูกต้อง เพื่อป้องกันไม่ให้อักขระพิเศษ (เช่น `.`, `-`, `*`) ทำให้การแสดงผลผิดพลาดหรือทำให้ Telegram API ส่ง Error กลับมา
- [ ] ข้อความที่อยู่ **ภายใน** Code Block จะต้อง **ไม่ถูก** escape เพื่อให้โค้ดแสดงผลได้ถูกต้องตามต้นฉบับ
- [ ] หากข้อความจาก LLM ไม่มี Code Block, ระบบควรจะยังทำงานได้ปกติ (อาจส่งเป็น Plain Text หรือ Markdown ที่ผ่านการ escape แล้ว)

## 5. กรณีตัวอย่าง (Specification by Example - SBE)

### **Scenario 1: การส่ง Code Block สำเร็จ (Happy Path)**

**GIVEN** LLM สร้างคำตอบที่มี Python code block
**WHEN** บอทส่งคำตอบนั้นกลับไปยังผู้ใช้
**THEN** ผู้ใช้จะเห็นข้อความปกติ และเห็น Code Block ที่มีการจัดรูปแบบและเน้นสี Syntax อย่างสวยงามในแอป Telegram

**ตัวอย่าง:**

| Input from LLM | Action: Call Telegram `sendMessage` | Expected Result in Chat |
|---|---|---|
| `Here's a simple function:\n\`\`\`python\ndef hello():\n  print("world")\n\`\`\`` | **`text`**: (escaped text) + code block<br>**`parse_mode`**: `MarkdownV2` | ข้อความ "Here's a simple function:"<br>ตามด้วย Code Block ที่แสดงโค้ด Python |

---

### **Scenario 2: ข้อความมีอักขระพิเศษที่ต้อง Escape**

**GIVEN** LLM สร้างคำตอบที่มีอักขระพิเศษที่อาจขัดกับ Markdown (เช่น `.` หรือ `-`) ปนอยู่กับ Code Block
**WHEN** บอทส่งคำตอบนั้นกลับไปยังผู้ใช้
**THEN** อักขระพิเศษที่อยู่นอก Code Block จะต้องถูก escape เพื่อให้แสดงผลเป็นตัวอักษรธรรมดา และไม่ทำให้ API call ล้มเหลว

**ตัวอย่าง:**

| Input from LLM | `text` sent to Telegram API (Example) | Expected Result in Chat |
|---|---|---|
| `The IP is 127.0.0.1. Use this code:\n\`\`\`bash\nping 127.0.0.1\n\`\`\`` | `The IP is 127\\.0\\.0\\.1\\. Use this code:\n\`\`\`bash\nping 127.0.0.1\n\`\`\`` | ข้อความ "The IP is 127.0.0.1. Use this code:"<br>ตามด้วย Code Block ที่แสดงโค้ด Bash |

## 6. สิ่งที่ไม่ได้ทำใน Scope นี้ (Out of Scope)

- การแปลงโค้ดเป็นรูปภาพเพื่อส่งกลับ
- การเพิ่มปุ่ม "Copy" บน Code Block (เป็นฟีเจอร์ของแอป Telegram เอง)
- การรองรับ Formatting ภาษาอื่นนอกเหนือจากที่ Telegram Bot API รองรับ (เช่น `HTML`)