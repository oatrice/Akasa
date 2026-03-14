# Specification

## Title
Asynchronous Deployment Service with Post-Build Notification and URL Verification

## Issue URL
https://github.com/oatrice/Akasa/issues/33
https://github.com/oatrice/Akasa/issues/34

## Goal
To enable developers to initiate service deployments (Web, Backend) asynchronously without blocking their workflow, provide real-time status updates, and automatically notify them via Telegram with a direct verification link upon deployment completion. This aims to improve developer productivity, reduce waiting times, and streamline the verification process of deployed services.

## User Story
As a developer, I want to initiate deployments for my services (Web, Backend) and receive immediate notifications with verification links once the deployment is complete, so I can quickly check the status and validate the deployed service without waiting for the process to finish.

## User Journey

1.  **Initiate Deployment:** The developer sends a request to deploy a specific service (e.g., "Web" or "Backend").
2.  **Immediate Acknowledgment:** The system immediately responds, confirming that the deployment process has been initiated and providing a unique identifier for tracking.
3.  **Background Processing:** The system starts the actual build and deployment commands (e.g., `vercel deploy`, `render-cli deploy`) in the background, allowing the developer to continue with other tasks.
4.  **Status Tracking (Optional):** The developer can, at any point, query the system using the unique identifier to check the current status of the ongoing deployment (e.g., "PENDING", "BUILDING", "DEPLOYING").
5.  **Deployment Completion:** Once the background build and deployment process finishes (either successfully or with a failure).
6.  **Telegram Notification:** The system automatically sends a notification message to the developer's Telegram chat.
7.  **Verification Link:** For successful deployments, the Telegram message includes a summary and an inline keyboard button with the direct URL to the newly deployed service. For failures, it includes an error summary.
8.  **Service Verification:** The developer clicks the provided URL in Telegram to quickly verify the deployed service.

## Functional Requirements

### 1. Asynchronous Deployment Initiation
*   **FR1.1:** The system SHALL accept requests to initiate deployments for specified services (e.g., "Web", "Backend").
*   **FR1.2:** The system SHALL immediately return a response to the user upon receiving a deployment request, indicating that the process has started asynchronously and providing a unique `deployment_id`.
*   **FR1.3:** The system SHALL execute the actual build and deployment commands (e.g., `vercel deploy`, `render-cli deploy`) as a background task, detached from the initial request-response cycle.

### 2. Deployment Status Management
*   **FR2.1:** The system SHALL store the current status of each deployment (e.g., "PENDING", "BUILDING", "DEPLOYING", "SUCCESS", "FAILED") in a persistent, fast-access store (e.g., Redis), associated with its `deployment_id`.
*   **FR2.2:** The system SHALL update the deployment status in the persistent store as the background task progresses through its lifecycle.
*   **FR2.3:** The system SHALL provide a mechanism (e.g., an API endpoint) for users to query the current status of a specific deployment using its `deployment_id`.

### 3. Post-Build Notification System
*   **FR3.1:** Upon the completion (success or failure) of a background deployment task, the system SHALL trigger a notification service.
*   **FR3.2:** The notification service SHALL send a message to the user via Telegram.
*   **FR3.3:** The Telegram notification message SHALL include a clear summary of the deployment outcome (e.g., "Deployment of [Service Name] Successful!", "Deployment of [Service Name] Failed!").
*   **FR3.4:** For successful deployments, the notification message SHALL include the final deployed URL.
*   **FR3.5:** The deployed URL SHALL be presented as a clickable inline keyboard button within the Telegram message, labeled appropriately (e.g., "View [Service Name]").
*   **FR3.6:** For failed deployments, the notification message SHALL include relevant error information or a link to detailed logs if available.

## Out of Scope
*   Authentication and authorization mechanisms for triggering deployments.
*   Detailed logging of the build/deploy process beyond status updates (e.g., full stdout/stderr of build commands).
*   Rollback functionality for failed deployments.
*   Support for notification channels other than Telegram.
*   Management of deployment configurations (e.g., environment variables, branch selection).

## Scenarios

### Scenario 1: Successful Web Service Deployment and Notification

**Description:** A user initiates a deployment for the "Web" service, which completes successfully, and receives a Telegram notification with a verification URL.

| Step | User Action / System Event | Expected System Behavior |
| :--- | :------------------------- | :----------------------- |
| 1    | User requests deployment for "Web" service. | System immediately responds with `{"status": "Deployment initiated", "deployment_id": "web-12345"}`. |
| 2    | (Background) Deployment process starts. | Redis status for `web-12345` is set to "PENDING". |
| 3    | (Background) Build phase begins. | Redis status for `web-12345` is updated to "BUILDING". |
| 4    | (Background) Deployment phase begins. | Redis status for `web-12345` is updated to "DEPLOYING". |
| 5    | (Background) Deployment completes successfully. | Redis status for `web-12345` is updated to "SUCCESS". |
| 6    | (System) Post-build notification triggered. | Telegram message is sent to the user. |
| 7    | User receives Telegram message. | Message content: "Deployment of Web Service Successful! Click below to view." with an inline keyboard button: `[View Web Service](https://web-service-12345.vercel.app)` |
| 8    | User clicks "View Web Service" button. | User's browser opens `https://web-service-12345.vercel.app`. |

### Scenario 2: Failed Backend Service Deployment and Notification

**Description:** A user initiates a deployment for the "Backend" service, which fails during the build phase, and receives a Telegram notification about the failure.

| Step | User Action / System Event | Expected System Behavior |
| :--- | :------------------------- | :----------------------- |
| 1    | User requests deployment for "Backend" service. | System immediately responds with `{"status": "Deployment initiated", "deployment_id": "backend-67890"}`. |
| 2    | (Background) Deployment process starts. | Redis status for `backend-67890` is set to "PENDING". |
| 3    | (Background) Build phase begins. | Redis status for `backend-67890` is updated to "BUILDING". |
| 4    | (Background) Build process encounters an error and fails. | Redis status for `backend-67890` is updated to "FAILED". |
| 5    | (System) Post-build notification triggered. | Telegram message is sent to the user. |
| 6    | User receives Telegram message. | Message content: "Deployment of Backend Service Failed! Error: Build process exited with code 1. Please check logs for details." (No URL button). |

### Scenario 3: Checking Deployment Status

**Description:** A user queries the status of an ongoing deployment.

| Step | User Action / System Event | Expected System Behavior |
| :--- | :------------------------- | :----------------------- |
| 1    | User initiates deployment for "Web" service. | System responds with `{"status": "Deployment initiated", "deployment_id": "web-12345"}`. (Status in Redis is "PENDING", then "BUILDING"). |
| 2    | User queries status for `web-12345`. | System responds with `{"deployment_id": "web-12345", "status": "BUILDING"}`. |
| 3    | (Background) Deployment completes successfully. | Redis status for `web-12345` is updated to "SUCCESS". |
| 4    | User queries status for `web-12345` again. | System responds with `{"deployment_id": "web-12345", "status": "SUCCESS"}`. |