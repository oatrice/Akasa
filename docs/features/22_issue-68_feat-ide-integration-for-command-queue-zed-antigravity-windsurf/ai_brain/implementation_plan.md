# Plan: Content Management (#68) & Auto-Complete (#94)

## Overview
This plan outlines the implementation for two features:
1. **Admin CRUD for Library & Courses (Issue #68):** Building the backend APIs and Web Admin interfaces to create, update, and delete Library categories, courses, and lessons.
2. **Auto-Complete Lesson (Issue #94):** Enhancing the user experience by automatically marking lessons as completed when the user scrolls to the end of the content, removing the need for a manual button click.

## User Review Required
> [!IMPORTANT]
> **Clarification for Issue #94 (Auto-Complete):**
> 1. What is the precise criteria for "completion"? Is scrolling to the bottom of the article (using Intersection Observer) sufficient? 
> 2. Should we start implementing Issue #68 (Admin CRUD) first, or Issue #94 (Auto-Complete)? Admin CRUD is a foundational backend task, while Auto-Complete is a quick frontend win.

## Proposed Changes

### Issue #68: Admin CRUD (Backend)
We will introduce a new handler `admin_content_handler.go` under the admin routes.
- **Library Categories:** Implement `POST`, `PUT`, `DELETE` at `/api/v1/admin/library/categories`
- **Courses:** Implement `POST`, `PUT`, `DELETE` at `/api/v1/admin/courses`
- **Lessons:** Implement `POST`, `PUT`, `DELETE` at `/api/v1/admin/courses/:courseId/lessons`

*These will be built using the TDD cycle (Red -> Green -> Refactor) and integrated into the existing `library_repo` and `course_repo`.*

### Issue #68: Admin CRUD (Web Frontend)
Build a Content Management portal on the Next.js Web Admin. We will utilize table components and form modals to perform the CRUD operations on the newly created backend APIs.

---

### Issue #94: Auto-Complete Lesson (Web Frontend)
- Create a reusable React hook `useIntersectionObserver` or utilize a dedicated component to detect when an element (e.g., the bottom of the article) enters the viewport.
- Modifying `app/courses/[id]/page.tsx` and related Lesson viewing components to auto-trigger the `markAsCompleted` action.
- Ensure the user gets visual feedback (e.g., a small toast notification or the checkmark automatically turning green) to acknowledge the auto-completion.

## Verification Plan
### Automated Tests
- **Backend:** Write unit tests for all new `admin_content_handler` methods (Categories, Courses, Lessons CRUD).
- **Frontend:** Verify the auto-complete trigger fires correctly in mock browser setups.

### Manual Verification
- **Admin CRUD:** Use Postman/curl and the Web Admin UI to verify data is correctly created, updated, and deleted in the database.
- **Auto-Complete:** Open a lesson on the Web app, scroll to the bottom, and verify that the backend API is called and the UI updates to "Completed" without clicking the button.
