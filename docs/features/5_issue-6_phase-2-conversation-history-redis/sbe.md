# SBE: Conversation History with Redis

> 📅 Created: 2026-03-07
> 🔗 Issue: [#6](https://github.com/oatrice/Akasa/issues/6)

---

## Feature: Contextual Memory for Conversations

This feature gives the chatbot a "memory" by storing and retrieving conversation history for each user in Redis. Before calling the LLM, the system fetches recent messages to provide context, enabling the bot to understand follow-up questions and provide more relevant, human-like answers.

### Scenario: Successful Follow-up Question (Happy Path)

**Given** a user has started a conversation with the bot
**When** the user asks a follow-up question that relies on the previous context
**Then** the system must provide the LLM with the conversation history, allowing it to generate a contextually-aware response

#### Examples

| `chat_id` | Previous History in Redis | Follow-up Message | LLM Prompt (contains history) |
|---|---|---|---|
| 12345 | `[]` (empty) | "Tell me about Python." | `messages: [{"role": "user", "content": "Tell me about Python."}]` |
| 12345 | `[{"role": "user", "content": "Tell me about Python."}, {"role": "assistant", "content": "Python is a programming language."}]` | "What is it used for?" | `..., {"role": "user", "content": "What is it used for?"}]` |
| 67890 | `[{"role": "user", "content": "Compare FastAPI and Flask."}]` | "Which one is faster?" | `..., {"role": "user", "content": "Which one is faster?"}]` |

### Scenario: Edge Case - Conversation Isolation

**Given** User A and User B are having separate conversations with the bot
**When** User B asks a question that could relate to User A's context
**Then** the system must only use the history from User B's chat, ensuring conversations do not leak between users

#### Examples

| `chat_id` | User Message | History in Redis for `chat_id: 111` | History for `chat_id: 222` | LLM called with context from... |
|---|---|---|---|---|
| 111 | "Explain Docker." | `[]` | `[]` | `chat_id: 111` (new convo) |
| 222 | "Explain Kubernetes." | `[{"role": "user", ... "Docker"}]` | `[]` | `chat_id: 222` (new convo) |
| 111 | "How do containers work?" | `[{"role": "user", ... "Docker"}]` | `[{"role": "user", ... "Kubernetes"}]` | `chat_id: 111` (Docker context) |
| 222 | "What is a pod?" | `[{"role": "user", ... "Docker"}, ...]` | `[{"role": "user", ... "Kubernetes"}]`| `chat_id: 222` (Kubernetes context) |

### Scenario: Error Handling - Redis Connection Failure

**Given** the Redis service is unavailable or the connection fails
**When** a user sends a message to the bot
**Then** the system must handle the connection error gracefully, bypass the history retrieval step, and process the message in a stateless manner (without context)

#### Examples

| Redis Status | User Message | System Action | LLM called with history? |
|---|---|---|---|
| Unavailable | "What is Git?" | Catches `ConnectionError`, logs it. | No |
| Unavailable | "Tell me more about branching." | Catches `ConnectionError`, logs it. | No |
| Timeout | "What is a PR?" | Catches `TimeoutError`, logs it. | No |