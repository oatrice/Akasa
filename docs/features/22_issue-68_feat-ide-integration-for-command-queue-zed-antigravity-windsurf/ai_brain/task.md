# Issues #68 & #94 Tracker

## 1. Issue #68: Admin CRUD for Library & Courses (Backend)
- [x] Setup `admin_content_handler.go` structure
- [x] TDD: Implement Library Category CRUD repository & handler
- [x] TDD: Implement Course CRUD repository & handler
- [x] TDD: Implement Lesson CRUD repository & handler
- [x] Register new routes in `main.go` (under `/api/v1/admin`)

## 2. Issue #68: Admin CRUD (Web Admin UI)
- [x] Create Content Management Dashboard
- [x] Implement Category Management Table & Form
- [x] Implement Course Management Table & Form
- [x] Implement Lesson Management Table & Form

## 3. Issue #94: Auto-Complete Lesson (Web UI)
- [ ] Implement `IntersectionObserver` logic to detect when user reaches the end of the content
- [ ] Integrate auto-complete logic into the Lesson View page
- [ ] Automatically trigger `POST /api/v1/progress/course` upon completion
- [ ] Add visual feedback (e.g., a toast or status change) when auto-completed
