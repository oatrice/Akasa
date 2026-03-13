# SBE: Antigravity IDE Action Confirmation via Akasa Bot

> 📅 Created: 2026-03-13
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/58

---

## Feature: Remote Action Confirmation for Antigravity IDE

Enable the Antigravity IDE to request explicit user approval for executing commands. The request is sent to the Akasa backend, which triggers a confirmation message with "Allow" and "Deny" options on Telegram. The system then long-polls for the user's decision and returns it to the IDE.

### Scenario: User Responds to Action Confirmation Request

**Given** the Akasa MCP server is running and connected to a user's Telegram account
**When** the Antigravity IDE calls the `request_remote_approval` tool with a command, working directory, and description
**And** the user receives the confirmation on Telegram and presses either "Allow" or "Deny"
**Then** the `request_remote_approval` tool returns a JSON object indicating the user's choice

#### Examples

| command | cwd | description | user_action | expected_output |
|-------------------------------------|-----------------------|-------------------------------------------|---------------|-----------------------------|
| `git push --force` | `/home/user/project-x` | Force push to the 'main' branch. | Allow | `{"status": "allowed"}` |
| `rm -rf build/` | `/home/user/project-x` | Delete the build directory. | Allow | `{"status": "allowed"}` |
| `docker system prune -a -f` | `/` | Force remove all unused Docker data. | Deny | `{"status": "denied"}` |
| `terraform apply -auto-approve` | `/infra/production` | Apply changes to production infrastructure. | Deny | `{"status": "denied"}` |
| `npm install` | `/home/user/new-app` | Install project dependencies | Allow | `{"status": "allowed"}` |

### Scenario: Action Request Times Out

**Given** the Akasa MCP server is running with a 60-second long-poll timeout
**When** the Antigravity IDE calls the `request_remote_approval` tool
**And** the user does not respond to the Telegram confirmation message within 60 seconds
**Then** the `request_remote_approval` tool returns a JSON object indicating a timeout

#### Examples

| command | cwd | description | timeout_seconds | expected_output |
|-----------------------------|---------------------|--------------------------------|-----------------|---------------------------|
| `kubectl delete pod my-pod` | `/k8s/configs` | Delete a Kubernetes pod. | 60 | `{"status": "timeout"}` |
| `git rebase -i HEAD~10` | `/home/user/my-repo` | Rebase last 10 commits. | 60 | `{"status": "timeout"}` |
| `ansible-playbook deploy.yml` | `/etc/ansible` | Run production deployment playbook. | 60 | `{"status": "timeout"}` |


### Scenario: Invalid Parameters Sent to Server

**Given** the Akasa MCP server is running
**When** the