# Specification

**Title:** [Phase 2] Rate Limiting & Error Handling + [Feature] Unified User Session & Multi-Platform Context Sync (Telegram + macOS)

**Version:** 1.0
**Status:** Draft

## 1. Objective

This specification outlines a unified system to enhance user experience, ensure stability, and enable seamless cross-platform context synchronization. The primary goals are:
1.  **Protect the system** from abuse and unexpected failures by implementing rate limiting and robust error handling.
2.  **Create a unified user identity** that links a user's Telegram account with their local macOS environment.
3.  **Enable context synchronization**, specifically the 'active project', so that changes made on one platform (e.g., macOS CLI) are instantly reflected on another (e.g., Telegram bot), providing a fluid and uninterrupted workflow for the developer.

## 2. User Personas & Goals

*   **Persona:** A software developer who uses both Telegram for quick interactions with the Akasa AI assistant and their local macOS terminal/IDE for development tasks.
*   **Goal:** To have a consistent and reliable experience where the AI assistant always knows which project they are working on, regardless of the interface they are using, and to be protected from accidental spam or confusing LLM errors.

## 3. User Journey

1.  **First-Time Setup:** Alex, a developer, decides to link their local development environment to their Akasa Telegram bot. They run a command `akasa login` in their terminal. The CLI generates a unique, one-time token and asks Alex to send it to the Akasa bot on Telegram.
2.  **Account Linking:** Alex sends the token to the bot. The bot validates the token, securely links their Telegram account to their macOS user profile, and confirms the successful connection. A `Unified User ID` is created for Alex.
3.  **Setting Context:** In their terminal, Alex navigates to a new project directory, `/Users/alex/Projects/Phoenix`, and runs `akasa set-project Phoenix`. The system updates Alex's global state in Redis, setting 'Phoenix' as the active project for their `Unified User ID`.
4.  **Cross-Platform Interaction:** Later, while on the move, Alex uses their phone to send a command `/git status` to the Akasa bot via Telegram. The bot, accessing Alex's global state via their `Unified User ID`, correctly executes the command within the 'Phoenix' project context on the designated machine.
5.  **Handling Rapid Inputs:** While debugging, Alex accidentally sends a burst of 7 commands in 10 seconds to the bot. The system processes the first few commands but then sends a polite message: "You are sending messages too quickly. Please wait a moment."
6.  **Graceful Error Handling:** Alex asks the bot a complex question that causes the underlying LLM to time out. Instead of silence or a cryptic error, the bot responds: "Sorry, the request timed out. Please try simplifying your question or try again in a few moments."

## 4. Key Features & Requirements

### 4.1. Unified User Identity
*   **R1.1:** The system must be able to generate a unique, secure, and short-lived token on a local machine via a CLI command (e.g., `akasa login`).
*   **R1.2:** The Telegram bot must be able to receive this token and associate the sending `telegram_user_id` with the `local_user_id` that generated the token.
*   **R1.3:** This association must be stored securely, creating a persistent `Unified User ID`.
*   **R1.4:** All user-specific data, such as active project context, will be stored under this `Unified User ID`.

### 4.2. Cross-Platform State Synchronization
*   **R2.1:** A global state for each `Unified User ID` must be maintained in Redis. This state must include the `active_project`.
*   **R2.2:** A secure API endpoint must be created (e.g., `PUT /api/v1/user/state`) that allows an authenticated local client to update the user's global state (e.g., change the `active_project`).
*   **R2.3:** Another endpoint (e.g., `GET /api/v1/user/state`) must be available for clients to retrieve the current state.
*   **R2.4:** When the Akasa bot receives a command, it must first check the `Unified User ID` to retrieve the `active_project` context before executing the command.

### 4.3. Rate Limiting & Error Handling
*   **R3.1:** The system must enforce a configurable rate limit on incoming messages from all sources (e.g., per user, per chat).
*   **R3.2:** When the rate limit is exceeded, the system must discard the message and send a standardized, user-friendly warning.
*   **R3.3:** The system must gracefully handle common errors from the LLM service (e.g., API errors, timeouts, content filtering).
*   **R3.4:** Instead of failing silently or showing a raw error, the system must provide a clear, helpful message to the user, guiding them on what to do next.

## 5. Specification by Example (SBE)

### Scenario 1: User links their macOS account to Telegram

| GIVEN | A developer, 'Alex', has not yet linked their local machine to their Telegram account. |
|---|---|
| **WHEN** | Alex runs the command `akasa login` in their macOS terminal. |
| **THEN** | The system generates a unique 8-character alphanumeric token (e.g., `A4B1X9Z3`). |
| **AND** | The CLI displays: `To link your account, send this one-time token to your Akasa bot on Telegram: A4B1X9Z3` |
| **WHEN** | Alex sends the message `A4B1X9Z3` to the Akasa bot. |
| **THEN** | The system validates the token, finds the pending local user association, and creates a `Unified User ID` linking the Telegram user and local user. |
| **AND** | The token `A4B1X9Z3` is invalidated immediately. |
| **AND** | The bot replies to Alex on Telegram: `✅ Your macOS account has been successfully linked!` |

### Scenario 2: Active project context is synced from macOS to Telegram

| GIVEN | User 'Alex' has a linked account. The current active project for their `Unified User ID` is `Project-A`. |
|---|---|
| **WHEN** | Alex runs the command `akasa set-project Project-B` in their macOS terminal. |
| **THEN** | The CLI makes an authenticated API call to `PUT /api/v1/user/state` with the payload `{"active_project": "Project-B"}`. |
| **AND** | The backend service updates the `active_project` for Alex's `Unified User ID` to `Project-B` in Redis. |
| **AND** | The CLI prints a confirmation: `Active project switched to Project-B.` |
| **WHEN** | Alex sends the command `/run_tests` to the Akasa bot on Telegram. |
| **THEN** | The bot identifies Alex's `Unified User ID`, retrieves the state from Redis, and sees that the active project is `Project-B`. |
| **AND** | The system executes the test suite for `Project-B`. |

### Scenario 3: User exceeds the message rate limit

| GIVEN | The rate limit is configured to 5 messages per 60 seconds per user. User 'Sam' has sent 4 messages in the last 30 seconds. |
|---|---|
| **WHEN** | Sam sends their 5th message, "What's the capital of Thailand?". |
| **THEN** | The message is processed and sent to the LLM. |
| **WHEN** | 2 seconds later, Sam sends their 6th message, "And what's the weather?". |
| **THEN** | The system identifies that the rate limit has been exceeded for Sam's user ID. |
| **AND** | The system discards the 6th message. |
| **AND** | The bot sends a reply to Sam: `You are sending messages too quickly. Please wait a moment before trying again.` |