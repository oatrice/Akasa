# Specification

## Overview

This specification defines the requirements for adding an optional `model` field to the `TaskNotificationRequest` and displaying it in task notifications. The feature enhances transparency by showing users which AI model generated their task results.

## Goals

- **Primary Goal**: Enable users to see which AI model was used for task generation in notifications
- **User Journey**: User receives notification → User sees source and model information → User gains transparency for debugging and model selection

## Requirements

### Functional Requirements

1. **FR1**: The `TaskNotificationRequest` model SHALL include an optional `model` field of type `Optional[str] = None`
2. **FR2**: When a model is provided in the notification request, the Telegram notification SHALL display "*Model:* {escaped_model}" 
3. **FR3**: When no model is provided, the notification SHALL NOT include any model information
4. **FR4**: Model information SHALL be retrieved from user preferences stored in Redis using chat_id
5. **FR5**: Model display SHALL use `escape_markdown_v2_content` for safe MarkdownV2 rendering
6. **FR6**: All existing notification functionality SHALL remain unchanged (backward compatibility)

### Non-Functional Requirements

1. **NFR1**: Implementation SHALL maintain backward compatibility
2. **NFR2**: Model field SHALL be optional to avoid breaking changes
3. **NFR3**: Performance impact SHALL be minimal (< 100ms additional latency)

## Scenarios

### Scenario 1: Successful Model Display
**Given** a user has a model preference set in Redis  
**When** a task completes and notification is sent  
**Then** the notification includes the model information

### Scenario 2: No Model Available  
**Given** a user has no model preference or retrieval fails  
**When** a task completes and notification is sent  
**Then** the notification does not include model information

### Scenario 3: Model with Special Characters
**Given** a model name contains Markdown-special characters  
**When** the notification is displayed  
**Then** the model name is properly escaped

## Acceptance Criteria

- [ ] TaskNotificationRequest includes optional model field
- [ ] Notifications display model when present
- [ ] No model displayed when None/absent
- [ ] Model safely escaped in Markdown
- [ ] Backward compatibility maintained
- [ ] Integration tests pass
- [ ] Manual verification successful