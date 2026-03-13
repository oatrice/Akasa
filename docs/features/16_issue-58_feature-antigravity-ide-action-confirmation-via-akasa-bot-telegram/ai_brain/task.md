# Task Checklist: Lock UI สำหรับ Wisdom Garden

## งานก่อนหน้า (เสร็จแล้ว)
- [x] เพิ่ม nav link "Practice Config" ใน `layout.tsx`
- [x] เขียน 3 unit tests สำหรับ Admin Practice Config handler
- [x] `go test ./...` ผ่านทั้งหมด

## Lock UI Implementation
- [x] อัปเดต `WeekSelector.tsx` — รับ `weekStatuses`, แสดง lock/passed icon
- [x] อัปเดต `AppHeader.tsx` — ส่งผ่าน `weekStatuses`
## 2. Frontend: Wisdom Garden Home Page (app/page.tsx)
- [x] Fetch `eightWeekProgress` via `useWisdomGarden`
- [x] Pass `weekStatuses` to `AppHeader` to show lock icons in the week selector
- [x] Determine if the current selected week is locked
- [x] Display a Lock Banner when the selected week is locked (Reason & Unlock Date)
- [x] Pass `readOnly` state and warning handler to `PracticeChecklist`
🔒
- [x] อัปเดต `weekly-practices/page.tsx` — ใช้ `eightWeekProgress`, แสดง lock banner, ส่ง `readOnly`
- [x] Browser test: ✅ Lock UI แสดงผลถูกต้อง — week 1 active, week 2-8 locked 🔒

## Bug Fix: Free Mode ยังแสดง Lock
- [x] ค้นหาสาเหตุ — `CalculateStatus()` ใน `progress_service.go` override ค่าที่ repo คืนมา
- [x] แก้ไข `CalculateStatus()` ให้เคารพ status จาก `GetUser8WeekStats()`
- [x] เทสต์ทั้งหมดผ่าน
- [x] Restart Backend Server
- [/] ตรวจสอบผล Browser — รอผู้ใช้ทดสอบ

## Bug Fix 2: Progress Only ไม่ Lock สัปดาห์ก่อนหน้า
- [x] ค้นหาสาเหตุ — `highWatermark` จาก Free mode ค้างอยู่ ทำให้ bypass เงื่อนไข Lock ของโหมด Progress / Time
- [x] แก้ไข `practice_repo.go` ให้ตรวจสอบเงื่อนไข Progress และ Time แบบคร่าวครัดโดยไม่สนใจ `highWatermark` 
- [x] รัน Unit Test ตรวจสอบ (`go test ./...`)
- [x] Restart Backend Server
- [/] ตรวจสอบผล Browser — รอผู้ใช้ทดสอบ
