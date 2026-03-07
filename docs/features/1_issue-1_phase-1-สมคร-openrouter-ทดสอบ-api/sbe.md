# SBE: ทดสอบการเชื่อมต่อ OpenRouter API

> 📅 Created: 2026-03-07
> 🔗 Issue: [#1](https://github.com/oatrice/Akasa/issues/1)

---

## Feature: Test OpenRouter API Connection

This feature involves creating a script to test the connection to the OpenRouter API. The script will use a valid API key to send a request to a free LLM model and verify that a successful response is received, confirming that the authentication and API endpoint are working correctly.

### Scenario: Successful API Call (Happy Path)

**Given** the user has a valid and active OpenRouter API key
**When** the user runs the test script with a prompt for a free model
**Then** the script receives an `HTTP 200 OK` status and a valid JSON response containing the AI-generated text

#### Examples

| model | prompt | expected_response_content (contains) |
|---|---|---|
| `mistralai/mistral-7b-instruct:free` | "What is 1+1?" | "2" |
| `mistralai/mistral-7b-instruct:free` | "Translate 'hello' to French" | "Bonjour" |
| `nousresearch/nous-hermes-2-mixtral-8x7b-dpo:free` | "Who is the first man on the moon?" | "Neil Armstrong" |
| `openchat/openchat-7b:free` | "What is the largest planet in our solar system?" | "Jupiter" |
| `huggingfaceh4/zephyr-7b-beta:free` | "Write a haiku about coding" | "Pixels glow so bright,<br>Logic flows from mind to screen,<br>New worlds come to life." |

### Scenario: Error Handling - Invalid API Key

**Given** the user has an invalid or expired OpenRouter API key
**When** the user runs the test script
**Then** the script receives an `HTTP 401 Unauthorized` status and an error message indicating an issue with the key

#### Examples

| api_key_provided | expected_status_code | error_message |
|---|---|---|
| `sk-or-invalid-key-1234` | 401 | "Incorrect API key provided..." |
| ` ` (empty string) | 401 | "Incorrect API key provided..." |
| `null` (or not provided) | 401 | "You didn't provide an API key..." |
| `sk-or-revoked-key-5678` | 401 | "Incorrect API key provided..." |

### Scenario: Edge Case - Invalid Model Name

**Given** the user has a valid OpenRouter API key
**When** the user runs the test script requesting a model that does not exist or is not available on the free tier
**Then** the script receives an `HTTP 404 Not Found` or `HTTP 400 Bad Request` status and a relevant error message

#### Examples

| model_requested | expected_status_code | error_message (contains) |
|---|---|---|
| `gpt-4` | 400 | "This model requires a paid account." |
| `invalid/model-name` | 404 | "Model not found" |
| `mistralai/mistral-7b-instruct:paid` | 400 | "This model requires a paid account." |
| ` ` (empty string) | 400 | "model is a required property" |