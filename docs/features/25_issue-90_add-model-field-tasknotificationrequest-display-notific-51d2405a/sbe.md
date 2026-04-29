# SBE: Add model field to TaskNotificationRequest and display in notifications

> 📅 Created: 2026-04-29
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/90

---

## Feature: Add model field to TaskNotificationRequest and display in notifications

This feature enhances task notifications by displaying the AI model used to generate the response, providing users with better transparency and debugging capabilities. Users will see the model information alongside the source in notifications, making it easier to track which AI model produced specific results.

### Scenario: Happy Path - Model displayed when provided

**Given** a TaskNotificationRequest contains a valid model identifier (e.g., "gpt-4o")
**When** the notification is sent via Telegram
**Then** the notification message includes "*Model:* gpt-4o" in the message content

#### Examples

| model | expected_display |
|-------|------------------|
| gpt-4o | *Model:* gpt-4o |
| claude-3-sonnet | *Model:* claude-3-sonnet |
| gemini-pro | *Model:* gemini-pro |

### Scenario: Edge Cases - Model not provided

**Given** a TaskNotificationRequest has model set to None
**When** the notification is sent via Telegram
**Then** the notification message does not include any model information

#### Examples

| model | expected_display |
|-------|------------------|
| None | (no model line) |
|  | (no model line) |

### Scenario: Error Handling - Invalid model format

**Given** a TaskNotificationRequest contains an invalid model identifier (e.g., "invalid@model!")
**When** the notification is sent via Telegram
**Then** the model is safely escaped and displayed as "*Model:* invalid\@model\!"

#### Examples

| invalid_model | escaped_display |
|---------------|-----------------|
| invalid@model! | *Model:* invalid\@model\! |
| model_with*stars* | *Model:* model\_with\*stars\* |