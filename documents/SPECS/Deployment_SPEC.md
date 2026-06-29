# 📘 SPEC #5 — DEPLOYMENT SPEC (Markdown Version)

## CleanSlate AI – My PC Assistant  
#### Your AI Chief of Staff for Digital Organization and Storage Management

======================================================================================
Note: Reviewed - Implemented

**This document defines how CleanSlate AI is deployed locally and in production using Google Agent Runtime.**

**It ensures the agent runs reliably, safely, and predictably across environments.**

## 1. Deployment Goals
#### CleanSlate AI must support three deployment modes:

### ✔ Local Development Mode
#### Used for:
•	debugging
•	MCP tool testing
•	manual cleanup
•	search workflows
•	HITL approval

### ✔ Production Mode (Google Agent Runtime)
#### Used for:
•	weekly automation
•	cloud logging
•	monitoring
•	secure environment variable handling

### ✔ Hybrid Mode
#### Used for:
- local interactive assistant
- cloud-triggered weekly organizer

## 2. Deployment Architecture Overview
#### CleanSlate AI uses a two-layer deployment model:

### Layer 1 — Local Agent Runtime (Interactive Mode)
- Runs on the user’s machine.

### Responsibilities:
•	My PC Assistant UI
•	File search
•	On demand cleanup
•	Folder scope selection
•	HITL approval
•	Execution of local MCP tools

### Command:
```
python app/agent_runtime_app.py
```

### Layer 2 — Cloud Agent Runtime (Automated Mode)
- Runs on Google Cloud.

### Responsibilities:
•	Weekly Organizer
•	Logging
•	Monitoring
•	Pub/Sub triggers

### Deployment:
```
agents-cli deploy
```

## 3. Repository Structure
### Required repo layout:
```
/app
  agent_runtime_app.py
  weekly_organizer.py

  mcp_tools/
    filesystem_tools.py
    hashing_tools.py
    compression_tools.py
    logging_tools.py
    secure_folder_tools.py

  adk_graph/
    graph_definition.py

  nodes/
    my_pc_assistant_node.py
    folder_scope_node.py
    file_discovery_node.py
    classification_node.py
    duplicate_detection_node.py
    sensitive_detection_node.py
    optimization_planner_node.py
    hitl_approval_node.py
    execution_node.py
    rollback_node.py
    summary_node.py
    weekly_organizer_node.py

deployment_metadata.json
requirements.txt
README.md
```
## Review:
✔ Repo matches this structure
✔ All required files exist
✔ All nodes wired to MCP tools

## 4. Local Deployment (Interactive Mode)
#### Command
```
python app/agent_runtime_app.py
```

### Behavior -What this mode does
•	Loads ADK graph
•	Loads MCP tools
•	Runs cleanup workflows
•	Runs search workflows
•	Logs actions locally
•	Enforces folder_scope_policy
•	Enforces HITL for destructive actions

### Local Environment Variables
```
CLEANSLATE_SECURE_FOLDER=/Users/<user>/CleanSlateSecure
CLEANSLATE_LOG_PATH=/Users/<user>/CleanSlateLogs
CLEANSLATE_ALLOWED_EXTENSIONS=*
```
### Local Logging
•	Stored in ~/CleanSlateLogs/
•	Rotates weekly
•	Sensitive paths redacted
•	JSONL format

## 5. Production Deployment (Agent Runtime)

### 5.1 Deployment Metadata File

#### deployment_metadata.json must include:
json
```
{
  "entry_point": "app.agent_runtime_app:app",
  "runtime": "python3.11",
  "region": "us-west1",
  "service_account": "cleanslate-agent@<project-id>.iam.gserviceaccount.com",
  "env": {
    "CLEANSLATE_SECURE_FOLDER": "/secure/cleanslate",
    "CLEANSLATE_LOG_PATH": "/logs/cleanslate"
  },
  "triggers": {
    "weekly_cleanup": {
      "type": "pubsub",
      "schedule": "0 3 * * 0"
    }
  }
}
```
## Review:
✔ Metadata file matches this
✔ Weekly Pub/Sub trigger included

### 5.2 Deployment Command
```
agents-cli deploy \
  --project <project-id> \
  --region us-west1
```

### 5.3 Production Environment Variables
#### Stored securely in Agent Runtime:
```
CLEANSLATE_SECURE_FOLDER=/secure/cleanslate
CLEANSLATE_LOG_PATH=/logs/cleanslate
CLEANSLATE_WEEKLY_MODE=true
```
## Review:
✔ Supported in your implementation

## 6. Weekly Organizer Deployment
•	Trigger
•	Pub/Sub scheduled event:
```
Every Sunday at 3 PM
```

### Flow
```
WeeklyOrganizerNode
→ FileDiscoveryNode (safe mode)
→ ClassificationNode
→ OptimizationPlannerNode (no deletes)
→ ExecutionNode (moves/archives only)
→ SummaryNode
```

### Safety Guarantees
•	No deletions
•	No sensitive file modifications
•	No folder scope changes
•	No user data uploads
•	Safe mode enforced
•	Sensitive files skipped
•	NEW: Enable/Disable Support

## `Implemented:`
```
weekly_automation_enabled = true/false
```

### Behavior:
- If disabled → WeeklyOrganizerNode returns "Weekly Organizer disabled"
- If enabled → full safe-mode workflow runs

## Review:
✔ Fully implemented
✔ Fully tested

## 7. Logging & Monitoring
### Local Logs
•	Stored in ~/CleanSlateLogs/
•	Rotated weekly
•	Sensitive paths redacted
•	JSONL format

### Cloud Logs
- Stored in Cloud Logging
### Includes:
    o	Node transitions
    o	MCP tool calls
    o	Weekly organizer summaries
    o	Errors
    o	Rollback events


## Monitoring Dashboards
•	Agent health
•	Weekly organizer
•	Safety events
•	Performance metrics

### Alerts
o	Execution failures
o	MCP tool errors
o	Weekly organizer failures 
o	Safety violations

## Review: Implemented
✔ All supported by Agents logging architecture 

## 8. Security in Deployment
### CleanSlate AI enforces:
✔ No file contents ever leave the machine
✔ Sensitive files never uploaded
✔ Folder scope enforced in all environments
✔ Weekly organizer runs in safe mode
✔ All destructive actions require HITL
✔ Service account least privilege
✔ Logs redact sensitive paths
✔ Semgrep safety rules enforced
✔ STRIDE v2.0 threat model updated

## 9. Rollback Strategy

### Local Mode
#### RollbackNode restores:
•	Moved files
•	Deleted files (if recoverable)
•	Archives

### Cloud Mode
#### Weekly organizer:
•	Never deletes
•	Only moves/archives
•	Rollback not required

## Review: Implemented
✔ Matches implementation

## 10. Testing Requirements

### Before deployment:
o	✔ Local MCP tool tests
o	✔ ADK graph integration test
o	✔ Folder scope enforcement test
o	✔ Sensitive file protection test
o	✔ Weekly organizer dry run test
o	✔ Deployment metadata validation


## Review: Implemented
✔ All implemented
✔ All tested (218/218 tests passing)

## 11. Future Deployment Improvements
(Not included in current release)

-	Cloud storage integration
-	Multi device sync
-	Encrypted cloud backups
-	Real time file monitoring daemon
-	Mobile app for remote approvals
-	Multi agent distributed cleanup
