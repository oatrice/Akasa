# Specification

## Overview

This specification defines the requirements for adding an optional `model` field to the `TaskNotificationRequest` and displaying it in task notifications. The feature enhances transparency by showing users which AI model generated their task results.

## Use Cases

This feature supports two distinct use cases:

1. **Local AI (User Preference)**: User sets model preference via `/model` command in Telegram. Local AI agents use this preference, and notifications display the user-selected model.

2. **External AI (Direct Model)**: User works in external AI editors (Windsurf, Kilo, etc.). These editors send notifications with their own model identifiers (e.g., "SWE-1.6", "grok"). Notifications display the external AI's model directly, overriding user preference.

## Goals

- **Primary Goal**: Enable users to see which AI model was used for task generation in notifications
- **User Journey**: User receives notification → User sees source and model information → User gains transparency for debugging and model selection

## Requirements

### Functional Requirements

1. **FR1**: The `TaskNotificationRequest` model SHALL include an optional `model` field of type `Optional[str] = None`
2. **FR2**: When a model is provided in the notification request (External AI use case), the Telegram notification SHALL display "*Model:* {escaped_model}"
3. **FR3**: When no model is provided in the request (Local AI use case), model information SHALL be retrieved from user preferences stored in Redis using chat_id
4. **FR4**: When no model is provided and no preference exists in Redis, the notification SHALL NOT include any model information
5. **FR5**: Model display SHALL use `escape_markdown_v2_content` for safe MarkdownV2 rendering
6. **FR6**: All existing notification functionality SHALL remain unchanged (backward compatibility)
7. **FR7**: MCP server `notify_task_complete` tool SHALL accept optional `model` parameter for External AI use case

### Non-Functional Requirements

1. **NFR1**: Implementation SHALL maintain backward compatibility
2. **NFR2**: Model field SHALL be optional to avoid breaking changes
3. **NFR3**: Performance impact SHALL be minimal (< 100ms additional latency)

## Scenarios

### Scenario 1: Local AI - Model from User Preference
**Given** a user has set model preference via `/model gpt-4o` in Telegram (stored in Redis)  
**When** a local AI task completes and notification is sent without model in payload  
**Then** the notification includes the model information from Redis

### Scenario 2: External AI - Model from Payload
**Given** a user is working in Windsurf IDE  
**When** Windsurf sends a notification with `model="SWE-1.6"` and `source="Windsurf"`  
**Then** the notification displays the model from the payload (not from Redis)

### Scenario 3: No Model Available  
**Given** a user has no model preference in Redis and no model in payload  
**When** a task completes and notification is sent  
**Then** the notification does not include model information

### Scenario 4: Model with Special Characters
**Given** a model name contains Markdown-special characters  
**When** the notification is displayed  
**Then** the model name is properly escaped

## Acceptance Criteria

- [ ] TaskNotificationRequest includes optional model field
- [ ] Notifications display model from payload when provided (External AI)
- [ ] Notifications display model from Redis when payload has no model (Local AI)
- [ ] No model displayed when None/absent in both payload and Redis
- [ ] Model safely escaped in Markdown
- [ ] MCP server accepts optional model parameter
- [ ] Backward compatibility maintained
- [ ] Integration tests pass
- [ ] Manual verification successful