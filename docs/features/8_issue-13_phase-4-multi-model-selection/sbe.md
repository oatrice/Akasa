# SBE: Multi-Model Selection via Chat Command

> 📅 Created: 2026-03-08
> 🔗 Issue: [#13](https://github.com/oatrice/Akasa/issues/13)

---

## Feature: Multi-Model Selection Command

This feature allows users to dynamically switch the underlying Large Language Model (LLM) for their conversation using a `/model` command. The user's choice is persisted in Redis, so their preferred model is used for all subsequent messages until they change it again.

### Scenario: Successfully Switching the Active Model (Happy Path)

**Given** a user wants to change the LLM from the default setting
**When** the user sends a `/model` command with a valid, supported model alias
**Then** the system must update the user's preference in storage and send a confirmation message back to the chat

#### Examples

| command_sent | expected_confirmation_reply (contains) | subsequent_llm_call_uses |
|---|---|---|
| `/model claude` | "✅ Model selection updated to: Claude" | `anthropic/claude-3.5-sonnet` |
| `/model gemini-flash` | "✅ Model selection updated to: Gemini Flash" | `google/gemini-flash` |
| `/model gpt4o` | "✅ Model selection updated to: GPT-4o" | `openai/gpt-4o` |

### Scenario: Error Handling - Invalid Model Alias

**Given** the bot supports a predefined list of model aliases
**When** the user sends the `/model` command with an alias that is not in the supported list
**Then** the system must reject the change and reply with an error message that lists the available, valid aliases

#### Examples

| command_sent | current_preference | expected_error_reply (contains) | preference_changed |
|---|---|---|---|
| `/model gpt5` | `google/gemini-flash` | "❌ Invalid model 'gpt5'. Available models: `claude`, `gemini-flash`, `gpt4o`" | No |
| `/model llama` | `google/gemini-flash` | "❌ Invalid model 'llama'. Available models: `claude`, `gemini-flash`, `gpt4o`" | No |
| `/model Claude` | `google/gemini-flash` | "❌ Invalid model 'Claude'. Available models: `claude`, `gemini-flash`, `gpt4o`" | No |

### Scenario: Checking the Current Model Configuration

**Given** a user has a model preference set (either default or user-selected)
**When** the user sends the `/model` command with no arguments
**Then** the system must reply with the currently active model for their session and a list of all available aliases

#### Examples

| current_preference_in_redis | command_sent | expected_reply |
|---|---|---|
| `anthropic/claude-3.5-sonnet` | `/model` | "❇️ Current model: `Claude 3.5 Sonnet`\n\nTo switch, use `/model <alias>`:\n- `claude`\n- `gemini-flash`\n- `gpt4o`" |
| `null` (using default) | `/model` | "❇️ Current model: `Gemini Flash` (default)\n\nTo switch, use `/model <alias>`:\n- `claude`\n- `gemini-flash`\n- `gpt4o`" |