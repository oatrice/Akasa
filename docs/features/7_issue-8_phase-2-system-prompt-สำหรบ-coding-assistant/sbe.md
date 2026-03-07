# SBE: System Prompt for Coding Assistant

> 📅 Created: 2026-03-08
> 🔗 Issue: [#8](https://github.com/oatrice/Akasa/issues/8)

---

## Feature: System Prompt Injection

This feature establishes a consistent personality and behavior for the chatbot by prepending a predefined "system prompt" to every request sent to the LLM. This ensures the bot's responses are always aligned with its designated role as an expert coding assistant, without polluting the user-specific conversation history stored in Redis.

### Scenario: First Message with System Prompt (Happy Path)

**Given** the system has a defined system prompt
**When** a user sends their first message in a new conversation
**Then** the payload sent to the LLM must begin with the system message, followed by the user's message

#### Examples

| user_message | system_prompt | llm_payload_sent |
|---|---|---|
| "What is FastAPI?" | "You are a coding assistant." | `[{"role": "system", "content": "You are a coding assistant."}, {"role": "user", "content": "What is FastAPI?"}]` |
| "Hello" | "Be concise." | `[{"role": "system", "content": "Be concise."}, {"role": "user", "content": "Hello"}]` |

### Scenario: Follow-up Message with System Prompt and History

**Given** the system has a defined system prompt and an existing conversation history for a user
**When** the user sends a new message
**Then** the payload sent to the LLM must be ordered correctly: 1. System Prompt, 2. Conversation History, 3. New User Message

#### Examples

| system_prompt | existing_history | new_user_message | llm_payload_sent |
|---|---|---|---|
| "You are Akasa." | `[{"role": "user", "content": "What is Python?"}]` | "Is it fast?" | `[{"role": "system", ...}, {"role": "user", ...}, {"role": "user", "content": "Is it fast?"}]` |
| "You are Akasa." | `[{"role": "user", "content": "A"}, {"role": "assistant", "content": "B"}]` | "C" | `[{"role": "system", ...}, {"role": "user", "content": "A"}, {"role": "assistant", "content": "B"}, {"role": "user", "content": "C"}]` |

### Scenario: Verification - System Prompt Not Saved in History

**Given** the system uses a system prompt for a conversation turn
**When** the user's message and the bot's reply are saved to the Redis history
**Then** the Redis history must contain only the user and assistant messages, and must NOT include the system prompt

#### Examples

| user_message | bot_reply | llm_payload_sent (contains system prompt) | expected_history_saved_to_redis |
|---|---|---|---|
| "Hi" | "Hello!" | `[{"role":"system",...}, {"role":"user",...}]` | `[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]` |
| "Test" | "Acknowledged" | `[{"role":"system",...}, {"role":"user",...}]` | `[{"role": "user", "content": "Test"}, {"role": "assistant", "content": "Acknowledged"}]`|