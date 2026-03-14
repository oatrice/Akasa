# SBE: Asynchronous Deployment and Post-Build Notification System

> 📅 Created: 2026-03-14
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/33

---

## Feature: Asynchronous Deployment and Post-Build Notification System

This system enables asynchronous initiation of web and backend application deployments using FastAPI BackgroundTasks. It tracks the deployment status in Redis and, upon successful completion, sends a notification via Telegram, including the deployed URL for verification. In case of failure, it also notifies the user.

### Scenario: Happy Path - Successful Deployment and Notification

**Given** a valid deployment request for a project and a successful build/deploy command execution
**When** the asynchronous deployment process completes successfully
**Then** the deployment status in Redis is updated to 'completed', and a Telegram notification with the deployed URL and a verification button is sent

#### Examples

| project_id | deploy_command                                | expected_url                          | telegram_chat_id | redis_status_after | telegram_message_contains                               | telegram_button_url |
|------------|-----------------------------------------------|---------------------------------------|------------------|--------------------|---------------------------------------------------------|---------------------|
| akasa-web  | `vercel deploy --prod --project akasa-web`    | `https://akasa-web.vercel.app`        | `123456789`      | `completed`        | `Deployment for akasa-web completed successfully!`      | `https://akasa-web.vercel.app` |
| akasa-api  | `render-cli deploy --service akasa-api`       | `https://akasa-api.onrender.com`      | `987654321`      | `completed`        | `Deployment for akasa-api completed successfully!`      | `https://akasa-api.onrender.com` |
| blog-app   | `gcloud app deploy --project blog-app-prod`   | `https://blog-app-prod.appspot.com`   | `112233445`      | `completed`        | `Deployment for blog-app completed successfully!`       | `https://blog-app-prod.appspot.com` |
| portal-cms | `aws s3 sync build/ s3://portal-cms-bucket` | `https://portal-cms-bucket.s3.aws.com` | `554433221`      | `completed`        | `Deployment for portal-cms completed successfully!`     | `https://portal-cms-bucket.s3.aws.com` |

### Scenario: Error Handling - Deployment Failure

**Given** a valid deployment request for a project and a build/deploy command that fails during execution
**When** the asynchronous deployment process encounters an error
**Then** the deployment status in Redis is updated to 'failed', and a Telegram notification indicating the failure (without a valid URL) is sent

#### Examples

| project_id | deploy_command_that_fails                     | telegram_chat_id | redis_status_after | telegram_message_contains                               |
|------------|-----------------------------------------------|------------------|--------------------|---------------------------------------------------------|
| akasa-web  | `vercel deploy --invalid-flag`                | `123456789`      | `failed`           | `Deployment for akasa-web failed.`                      |
| akasa-api  | `render-cli deploy --non-existent-service`    | `987654321`      | `failed`           | `Deployment for akasa-api failed.`                      |
| blog-app   | `gcloud app deploy --invalid-project-id`      | `112233445`      | `failed`           | `Deployment for blog-app failed.`                       |
| portal-cms | `aws s3 sync build/ s3://non-existent-bucket` | `554433221`      | `failed`           | `Deployment for portal-cms failed.`                     |

### Scenario: Edge Case - Long-running Deployment

**Given** a valid deployment request for a project and a build/deploy command that takes an extended period to complete
**When** the asynchronous deployment process is still running after a significant duration (e.g., 5 minutes)
**Then** the deployment status in Redis remains 'in_progress', and no completion or failure notification is sent yet

#### Examples

| project_id | deploy_command                                | initial_redis_status | time_elapsed_minutes | redis_status_after | telegram_notification_sent |
|------------|-----------------------------------------------|----------------------|----------------------|--------------------|----------------------------|
| akasa-web  | `vercel deploy --prod --project akasa-web`    | `in_progress`        | `5`                  | `in_progress`      | `No`                       |
| akasa-api  | `render-cli deploy --service akasa-api`       | `in_progress`        | `10`                 | `in_progress`      | `No`                       |
| blog-app   | `gcloud app deploy --project blog-app-prod`   | `in_progress`        | `7`                  | `in_progress`      | `No`                       |
| portal-cms | `aws s3 sync build/ s3://portal-cms-bucket` | `in_progress`        | `12`                 | `in_progress`      | `No`                       |