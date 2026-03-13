# Fix Luma Code Review Prompt & Analyze `code_review.md`

## 1. การวิเคราะห์ความถูกต้องของ `code_review.md`
เนื้อหาใน `code_review.md` ปัจจุบัน **"ไม่ถูกต้อง"** และมีสาเหตุมาจากบั๊กใน Luma CLI ครับ:
- Luma CLI อ่าน **ไฟล์เต็มทั้งหมด** แทนที่จะอ่านเฉพาะ **git diff** (บรรทัดที่ที่มีการเปลี่ยนแปลง)
- แถมยังมีการตัดข้อความ (truncate) เหลือแค่ 3000 ตัวอักษร
- ทำให้ AI มองไม่เห็นว่าโค้ดมีการแก้ไขอะไรไปบ้าง จึงตอบกลับมาว่า "ผมต้องการข้อมูลเกี่ยวกับการเปลี่ยนแปลงโค้ดที่คุณต้องการให้ผมวิเคราะห์ก่อนครับ"

## 2. แผนการแก้ไข `code_review_prompt.txt`
เราจะปรับปรุง Luma CLI ให้สร้าง prompt ที่ชี้เป้าไปที่ git diff ตรงๆ โดยอาศัยฟังก์ชัน `generate_draft_code_review` ที่มีอยู่แล้วใน Luma CLI เพื่อสร้างไฟล์ `draft_code_review.md` (ซึ่งรวม git diff เอาไว้) แล้วให้ prompt อ้างอิงไฟล์นั้น

### `luma_core/actions.py`
#### [MODIFY] `luma_core/actions.py`
เพิ่มการเรียก `generate_draft_code_review` ก่อนสร้างข้อความ Prompt และแก้ไขโครงสร้าง prompt ให้ชัดเจน:
```python
            # สร้าง draft_code_review.md (ซึ่งมี git diff)
            from luma_core.tools import generate_draft_code_review
            draft_path = generate_draft_code_review(target_dir=target_dir)

            # Print the prompt for the user to copy and paste to the AI assistant
            print("\n" + "="*60)
            print("💡 COPY THIS PROMPT FOR THE AI ASSISTANT:")
            print("="*60)
            
            prompt_text = f"โปรดอ่านผลการรีวิวจาก {report_path} และรายละเอียด Code Changes (git diff) จาก {draft_path} มาอธิบาย สรุปประเด็นสำคัญ ถามเพื่อ clarify และให้ทำตาม Test suggestion ทั้งหมดด้วยกระบวนการ TDD"
            
            print(prompt_text)
            print("="*60)
```

## 3. (Optional) แผนแก้ไข `luma_core/agents/reviewer.py` ให้วิเคราะห์ชี้ตรงจุด
ถ้าต้องการให้ผลลัพธ์ใน `code_review.md` แนะนำ Test Suggestion ได้ถูกต้อง เราควรส่ง `git diff` ไปให้ `reviewer_agent` ด้วยแทนที่จะส่งโครงสร้างไฟล์เต็มแบบปัจจุบัน หากเห็นด้วยสามารถแจ้งให้แก้ไขเพิ่มได้เลยครับ

## Verification Plan
### Automated Tests
- ไม่มี automated tests สำหรับส่วนนี้
### Manual Verification
- รัน CLI Luma เลือกทำ code review และตรวจสอบไฟล์ `code_review_prompt.txt` ว่ามีข้อความที่ครอบคลุมถึง file `draft_code_review.md` ตามที่ตั้งใจหรือไม่
- ตรวจสอบ `code_review.md` และ `draft_code_review.md` ว่าสร้างสำเร็จและอยู่ใน path ที่ถูกต้อง
