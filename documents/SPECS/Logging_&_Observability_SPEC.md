# 📘 SPEC #8 — LOGGING & OBSERVABILITY SPEC

## CleanSlate AI – My PC Assistant
#### Your AI Chief of Staff for Digital Organization and Storage Management

========================================================================================

**This document defines the logging architecture, observability signals, monitoring dashboards, alerting rules, and redaction policies for CleanSlate AI.**

**It ensures the agent is traceable, safe, and debuggable across both local and cloud environments.**

## 1. Logging Philosophy
CleanSlate AI follows four logging principles:
### 1. Safety First
             Logs must never contain sensitive data or file contents.
### 2. Full Traceability
              Every action must be traceable from intent → plan → execution → summary.
### 3. Human Readable + Machine Readable
              Logs must support both debugging and automated monitoring.
### 4. Zero Leakage
                Logs must never leave the local machine unless running in Agent Runtime.

## 2. Logging Architecture

### CleanSlate AI uses a two tier logging system:
     
## Tier 1 — Local Logs (User Machine)
### Stored at:
```
$CLEANSLATE_LOG_PATH/
    actions.log
    errors.log
    weekly.log
```
### Local logs include:

    o  Node transitions
    o	MCP tool calls
    o	HITL approvals
    o	Execution results
    o	Rollback events
    o	Weekly organizer summaries

### Local logs exclude:
    o	File contents
    o	Sensitive file names
    o	Sensitive paths
    o	User personal data
     
## Tier 2 — Cloud Logs (Agent Runtime)

### Stored in Cloud Logging.
### Cloud logs include:
o	Weekly organizer runs
o	MCP tool errors
o	Execution failures
o	Rollback events
o	Node transition traces

### Cloud logs exclude:
o	File contents
o	Sensitive file names
o	Sensitive paths
o	User personal data

## 3. Log Format Specification
### All logs follow a structured JSON format:
```
{
  "timestamp": "2026-06-23T23:09:00Z",
  "node": "ExecutionNode",
  "action": "move_file",
  "status": "success",
  "source_path": "/Users/.../Documents/file.txt",
  "destination_path": "/Users/.../Archive/file.txt",
  "hitl_approved": true,
  "sensitive": false,
  "duration_ms": 42
}
```
### Required fields
•	timestamp
•	node
•	action
•	status

### Optional fields
•	hitl_approved
•	duration_ms
•	error_message

## 4. Redaction Rules

### 4.1 Sensitive Paths
#### Paths containing sensitive files must be redacted:
```
/Users/divya/Documents/tax_2023.pdf
→ [REDACTED_SENSITIVE_PATH]
```
### 4.2 Sensitive Filenames
#### Sensitive filenames must be replaced:
```
passport_scan.png → [SENSITIVE_FILE]
```
### 4.3 User Personal Data
#### Never logged:
•	Email
•	Address
•	API keys
•	Tokens
•	Browser history

### 4.4 File Contents
#### Never logged under any circumstances.

## 5. Node-Level Logging Requirements
#### MyPCAssistantNode
•	Intent detected
•	Confidence score
#### FolderScopeNode
•	Allowed paths
•	Blocked paths
•	Validation results
#### FileDiscoveryNode
•	Number of files scanned
•	Time taken
#### ClassificationNode
•	Classification summary
#### DuplicateDetectionNode
•	Duplicate groups found
#### SensitiveDetectionNode
•	Sensitive files flagged
#### OptimizationPlannerNode
•	Proposed plan
•	Safety checks
#### HITLApprovalNode
•	User approval decision
•	Rejected actions
#### ExecutionNode
•	Every action executed
•	Success/failure
•	Duration
#### RollbackNode
•	Actions reversed
#### SummaryNode
•	Final summary
#### WeeklyOrganizerNode
•	Safe-mode actions
•	Summary

## 6. Observability Signals
#### CleanSlate AI emits the following signals:

### 6.1 Node Transition Events
•	node.enter
•	node.exit
•	node.error

### 6.2 MCP Tool Events
•	tool.call
•	tool.success
•	tool.failure

### 6.3 Safety Events
•	sensitive.detected
•	scope.violation
•	hitl.required
•	hitl.rejected

### 6.4 Weekly Organizer Events
•	weekly.start
•	weekly.complete
•	weekly.error

## 7. Monitoring Dashboards (Cloud)
### Dashboard 1 — Agent Health
•	Node transition counts
•	Execution success rate
•	MCP tool error rate
•	Average execution time
### Dashboard 2 — Weekly Organizer
•	Runs per week
•	Files moved
•	Archives created
•	Errors
### Dashboard 3 — Safety Dashboard
•	Sensitive detections
•	HITL approvals
•	HITL rejections
•	Scope violations
### Dashboard 4 — Performance
•	Latency per node
•	Latency per MCP tool
•	Memory usage
•	CPU usage

## 8. Alerting Rules (Cloud)

### 8.1 Execution Failures
#### Trigger when:
•	5 failures in 10 minutes
•	Any failure in ExecutionNode

### 8.2 MCP Tool Errors
#### Trigger when:
•	Any tool returns PermissionDenied
•	Any tool returns PathNotAllowed
•	Error rate > 10%

### 8.3 Weekly Organizer Failures
#### Trigger when:
•	Weekly organizer fails to complete
•	Weekly organizer attempts a delete (should never happen)

### 8.4 Safety Alerts
#### Trigger when:
•	Sensitive file deletion attempted
•	Folder scope violation detected
•	HITL bypass attempted

## 9. Log Retention Policy
### Local Logs
•	Retained for 30 days
•	Rotated weekly
•	User can delete anytime
### Cloud Logs
•	Retained for 14 days
•	Rotated automatically

## 10. Testing Requirements for Logging
o	✔ Log redaction tests
o	✔ Log format validation
o	✔ Node transition logging tests
o	✔ MCP tool logging tests
o	✔ Weekly organizer logging tests
o	✔ Error logging tests
o	✔ Rollback logging tests

## 11. Future Observability Improvements
-	Vision-based image quality metrics
-	Cloud storage sync logs
-	Real-time event streaming
-	User behavior analytics (opt in)
-	Multi-device observability

