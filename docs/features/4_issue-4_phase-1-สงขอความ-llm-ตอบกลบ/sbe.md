# SBE: Core Chat Loop

> 📅 Created: 2026-03-07
> 🔗 Issue: [#4](https://github.com/oatrice/Akasa/issues/4)

---

## Feature: LLM Chat Response

This feature enables the core functionality of the chatbot. It orchestrates the process of receiving a user's text message from the Telegram webhook, forwarding it to an LLM for processing, and sending the AI-generated response back to the user's chat. All processing must happen in the background to ensure the webhook responds to Telegram immediately.

### Scenario: Successful Chat Reply (Happy Path)

**Given** the backend receives a valid text message from a user via the Telegram webhook
**When** the system sends the text to the OpenRouter LLM service and successfully receives a generated reply
**Then** the system must send that reply back to the original user's chat via the Telegram Bot API

#### Examples

| incoming_text | `chat_id` | mock_llm_response | expected_reply_text |
|---|---|---|---|
| "Hello" | 12345 | "Hi there! How can I help you today?" | "Hi there! How can I help you today?" |
| "What is Python?" | 67890 | "Python is a high-level programming language." | "Python is a high-level programming language." |
| "1 + 1 = ?" | 11223 | "1 + 1 equals 2." | "1 + 1 equals 2." |
| "Tell me a joke" | 44556 | "Why don't scientists trust atoms? Because they make up everything!" | "Why don't scientists trust atoms? Because they make up everything!" |

### Scenario: Error Handling - LLM Service Fails

**Given** the backend receives a valid text message from a user
**When** the system attempts to call the OpenRouter LLM service, but the service fails (e.g., returns a 5xx error or times out)
**Then** the system must log the error and must not send any reply to the user

#### Examples

| incoming_text | mock_llm_api_status | expected_system_action | reply_sent_to_user |
|---|---|---|---|
| "What's new?" | `500 Internal Server Error` | Log the error from OpenRouter | No |
| "Any ideas?" | `503 Service Unavailable` | Log the error from OpenRouter | No |
| "Help me debug this" | `Request Timeout` | Log the timeout error | No |
| "Hello again" | `401 Unauthorized` (Bad Key) | Log the authentication error | No |

### Scenario: Edge Case - Non-Text Message Received

**Given** the backend receives a webhook update from Telegram
**When** the update does not contain a new, standard text message (e.g., it's a sticker, a photo, an edited message, or a user joining a group)
**Then** the system must ignore the update, not call the LLM, and not send any reply

#### Examples

| incoming_update_type | `update_payload` | llm_call_made | reply_sent_to_user |
|---|---|---|---|
| Sticker | `{"message": {"sticker": {...}}}` | No | No |
| Edited Message | `{"edited_message": {"text": "..."}}` | No | No |
| Photo | `{"message": {"photo": [...]}}` | No | No |
| User joins group | `{"message": {"new_chat_members": [...]}}` | No | No |