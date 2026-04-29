# Implementation Plan: Add model field to TaskNotificationRequest and display in notifications

> **Refers to**: [Spec](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
> [!IMPORTANT]
> **Platform Scope Policy:**
> - **Web**: Mock UI only for this phase.
> - **Android**: Full implementation with production-ready code and tests.
> - **iOS**: Full implementation with production-ready code and tests.
>
> **Development Order:** Web Mock UI FIRST → Android Full Implementation SECOND → iOS Full Implementation THIRD.

- **Modified Components**: app/models/notification.py, app/services/telegram_service.py, scripts/akasa_mcp_server.py
- **New Components**: None
- **Dependencies**: None

### Data Model Changes
```python
# In app/models/notification.py
class TaskNotificationRequest(BaseModel):
    # ... existing fields ...
    model: Optional[str] = None  # NEW: AI model identifier
```

---

## 2. Step-by-Step Implementation

### Step 1: Update TaskNotificationRequest model
- **Docs**: Update model documentation in app/models/notification.py
- **Code**: Add `model: Optional[str] = None` field to TaskNotificationRequest
- **Tests**: Add unit tests for the new field serialization/deserialization

### Step 2: Update telegram service notification display
- **Docs**: Document the model display logic in app/services/telegram_service.py
- **Code**: Modify `send_task_notification` to include model line when present
- **Tests**: Add integration tests for notification display with model

### Step 3: Update MCP server to support dual-usecase model handling
- **Docs**: Update notify_task_complete tool documentation to explain optional model parameter
- **Code**: Add optional `model` parameter to notify_task_complete function and tool schema
- **Code**: Backend logic: use model from payload if provided (External AI), otherwise retrieve from Redis (Local AI)
- **Tests**: Test model parameter in payload and Redis fallback behavior

### Step 4: Update test commands and other notification senders
- **Docs**: Document changes to test commands
- **Code**: Ensure all TaskNotificationRequest creations include model when available
- **Tests**: Update existing tests to handle the new optional field

---

## 3. Verification Plan
*How will we verify success?*

> [!IMPORTANT]
> **Android Build Policy**: MUST use scripts in `Android/scripts/` (e.g., `build_android.sh`) instead of direct `./gradlew` to ensure correct JDK version (Java 21).

### Automated Tests
- [ ] Unit Tests: test_notification_model_field.py for model field handling
- [ ] Integration Tests: test_telegram_notification_with_model.py for end-to-end notification flow
- [ ] MCP Server Tests: test_notify_task_complete_includes_model_when_provided
- [ ] MCP Server Tests: test_notify_task_complete_excludes_model_when_not_provided

### Manual Verification
- [ ] Local AI: Set model via `/model`, send notification without model, verify Redis model displayed
- [ ] External AI: Send notification with model parameter, verify payload model displayed
- [ ] No model: Send notification without model and no Redis preference, verify no model line
- [ ] Test with various model names including special characters