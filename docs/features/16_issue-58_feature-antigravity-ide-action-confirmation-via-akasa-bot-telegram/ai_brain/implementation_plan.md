# Lock UI สำหรับ Wisdom Garden & Practice Room

## สรุปปัญหา
Backend ส่ง `status`, `lockReason`, `unlockDate` ผ่าน `/progress/8-weeks` แล้ว แต่ Frontend **ไม่ได้ใช้ข้อมูลนั้น** — ทุกสัปดาห์แสดงและ editable เท่ากันหมด

## Proposed Changes

### 1. Week Selector — แสดง Lock/Status Icon

#### [MODIFY] [WeekSelector.tsx](file:///Users/oatrice/Software-projects/The%20Middle%20Way%20-Metadata/Platforms/Web/components/features/wisdom-garden/WeekSelector.tsx)
- รับ props `weekStatuses?: WeekStatus[]` จาก `eightWeekProgress.weeks`
- สัปดาห์ที่ `status === "Locked"` → แสดง 🔒 icon + disabled + opacity + ไม่ให้คลิก
- สัปดาห์ที่ `status === "Passed"` → แสดง ✅ badge + สีเขียว
- สัปดาห์ `"In Progress"` → behaviour ปกติ (สี primary)

---

### 2. Weekly Practices Page — ใช้ Lock Data

#### [MODIFY] [page.tsx (weekly-practices)](file:///Users/oatrice/Software-projects/The%20Middle%20Way%20-Metadata/Platforms/Web/app/weekly-practices/page.tsx)
- ดึง `eightWeekProgress` จาก `useWisdomGarden()` hook (มีอยู่แล้ว แค่ไม่ได้ใช้)
- ส่ง `weekStatuses` ให้ `WeekSelector`
- คำนวณ `isLocked` จาก `eightWeekProgress.weeks[selectedWeek-1].status === "Locked"`
- เมื่อ `isLocked`:
  - แสดง **Lock Banner** (🔒 สัปดาห์นี้ยังล็อคอยู่ + lockReason + unlockDate)
  - ส่ง `readOnly={true}` ให้ `PracticeChecklist`

---

### 3. AppHeader — ส่งผ่าน weekStatuses

#### [MODIFY] [AppHeader.tsx](file:///Users/oatrice/Software-projects/The%20Middle%20Way%20-Metadata/Platforms/Web/components/features/wisdom-garden/AppHeader.tsx)
- รับ `weekStatuses` prop แล้วส่งต่อให้ `WeekSelector`

## Verification Plan

### Browser Testing
1. ตั้ง mode เป็น `PROGRESS_ONLY` ผ่าน Admin Practice Config
2. เปิดหน้า Weekly Practices → Week 2+ ควรแสดง 🔒 ใน selector
3. คลิก week ที่ locked → ควรไม่สามารถคลิกได้ หรือแสดง lock banner
4. ทำ Week 1 ครบ → Week 2 ควร unlock
