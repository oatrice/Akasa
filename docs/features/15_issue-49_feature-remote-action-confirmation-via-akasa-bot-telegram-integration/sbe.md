# SBE: Remote Action Confirmation via Telegram

> 📅 Created: 2026-03-10
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/49

---

## Feature: Remote Action Confirmation via Telegram

As a developer using Gemini CLI for long-running or remote tasks, I want to receive security-sensitive action requests on Telegram, so that I can approve or deny them remotely and securely.

### Scenario: Successful Command Approval (Happy Path)

**Given** The Gemini CLI is configured for "Remote Confirmation" and needs to run a sensitive command.
**When** The user receives the confirmation request on Telegram and presses the "✅ Allow Once" button.
**Then** The Akasa backend signals approval, and the Gemini CLI executes the command.

#### Examples

| command_to_run | user_decision | cli_outcome |
|--------------------------------------|---------------|-----------------------|
| `rm -rf /tmp/test-data` | ✅ Allow Once | Command executed |
| `docker push my-private-repo:latest` | ✅ Allow Once | Command executed |
| `kubectl scale deployment --replicas=0`| ✅ Allow Once | Command executed |
| `git push --force origin main` | ✅ Allow Once | Command executed |

### Scenario: Command Denial by User

**Given** The Gemini CLI has sent a sensitive command for remote confirmation via the Akasa bot.
**When** The user receives the confirmation request on Telegram and presses the "❌ Deny" button.
**Then** The Akasa backend signals denial, and the Gemini CLI aborts the command, reporting that it was denied.

#### Examples

| command_to_run | user_decision | cli_outcome |
|------------------------------------|---------------|--------------------------------|
| `rm -rf /` | ❌ Deny | Command aborted: Denied by user. |
| `sudo reboot` | ❌ Deny | Command aborted: Denied by user. |
| `terraform apply -auto-approve` | ❌ Deny | Command aborted: Denied by user. |

### Scenario: Request Timeout (Edge Case)

**Given** The Gemini CLI has sent a sensitive command for remote confirmation and is waiting.
**When** The user does not respond to the Telegram message within the configured timeout period.
**Then** The request is automatically cancelled, the command is not executed, and the CLI reports a timeout error.

#### Examples

| command_to_run | timeout_seconds | cli_outcome |
|--------------------------------|-----------------|------------------------------------------|
| `aws s3 sync ./build s3://my-prod-bucket` | 300 | Command aborted: Action timed out. |
| `npm publish --access public` | 120 | Command aborted: Action timed out. |
| `gcloud app deploy` | 600 | Command aborted: Action timed out. |