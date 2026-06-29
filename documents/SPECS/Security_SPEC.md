## 📘 SPEC #4 — SECURITY SPEC

### CleanSlate AI – My PC Assistant
#### Your AI Chief of Staff for Digital Organization and Storage Management

=====================================================================================

**This document defines the security model, permissions, constraints, safety boundaries, and LLM control rules for CleanSlate AI.**

**It ensures the agent is Predictable, trustworthy, non destructive, and fully human in the loop.**

## 1.Security Philosophy: 
### CleanSlate AI follows four core principles:

### 1. User Owned Data, User Controlled Actions
The agent never acts without explicit user intent.
### 2. Controlled Privilege
The agent only accesses folders the user approves.
### 3. No Irreversible Actions Without HITL
All destructive actions require human approval.
### 4. Privacy First Design
Sensitive files are never deleted, uploaded, or exposed.

## 2. Threat Model
### CleanSlate AI protects against:

### A) LLM Misinterpretation
•	Hallucinated file paths
•	Incorrect assumptions about user intent
•	Over broad cleanup actions

### B) Accidental Data Loss
•	Deleting important files
•	Deleting sensitive documents
•	Moving files to wrong locations

### C) Unauthorized Access
•	Accessing unapproved folders
•	Reading sensitive file contents
•	Writing to system directories

### D) Unsafe Automation
•	Weekly organizer running destructive actions
•	Auto cleanup without user review

## 3. Security Boundaries
### a. Boundary 1 — Folder Scope Policy (Hard Boundary)

#### The agent may only operate inside:
```
allowed_paths[]
```
#### The agent must never:
•	Scan
•	Read
•	Move
•	Delete
•	Hash
•	Compress

#### anything in:
```
blocked_paths[]
```
#### or system directories.

### This is enforced at:
•	MyPCAssistantNode (intent gating)
•	FolderScopeNode
•	FileDiscoveryNode
•	DuplicateDetectionNode
•	SensitiveDetectionNode
•	OptimizationPlannerNode
•	ExecutionNode
•	All MCP tools

### b. Boundary 2 — Sensitive File Protection
#### Sensitive files include:
•	Tax documents
•	Legal documents
•	Medical records
•	ID scans
•	Banking documents
•	Password files
•	API keys
•	Anything flagged by SensitiveDetectionNode

### Rules:
•	Sensitive files must never be deleted
•	Sensitive files must never be uploaded
•	Sensitive files must never be opened
•	Sensitive files may only be moved to authenticated folder

### c. Boundary 3 — HITL Approval Required
#### The following actions must go through HITLApprovalNode:
•	Delete
•	Move sensitive files
•	Compress
•	Archive
•	Bulk operations
•	Any action affecting > 10 files
•	Any action with < 90% confidence
No exceptions.

### d. Boundary 4 — No File Content Access
#### The agent must never:
•	Read file contents
•	Upload file contents
•	Send file contents to LLM
•	OCR files
•	Parse PDFs
Only metadata is allowed.

### Boundary 5 — No System Folder Access
#### The agent must never access:
•	C:\Windows
•	C:\Program Files
•	C:\Program Files (x86)
•	C:\Users\<user>\AppData
•	/usr
•	/etc
•	/bin
•	/var
These paths are automatically blocked.

## 4. LLM Safety Rules
### Rule 1 — LLM Cannot Execute Actions Directly
LLM may only propose actions. ExecutionNode performs them.
### Rule 2 — LLM Cannot Expand Folder Scope
LLM cannot add new allowed paths. Only user can.
### Rule 3 — LLM Cannot Override Sensitive Flags
If a file is flagged sensitive, LLM cannot unflag it.
### Rule 4 — LLM Cannot Trigger Cleanup Automatically
Only user intent can.
### Rule 5 — LLM Cannot Suggest Deleting Sensitive Files
Even if user asks, LLM must warn and require explicit override.

## 5. MCP Tool Permission Model
Each tool has strict permissions:

Tool	                  Allowed	                        Forbidden
list_files	            allowed_paths	              blocked_paths, system paths
read_file_metadata	    metadata only	              file contents
compute_hash	        allowed_paths	              sensitive files
move_file	            allowed_paths	              sensitive → non secure
delete_file	            HITL only	                  sensitive files
compress_files	        allowed_paths	              sensitive files
create_folder	        allowed_paths	              system paths
write_log	            safe entries	              sensitive data
read_log	            safe entries	              sensitive data
move_to_authenticated_folder	sensitive files	      non sensitive files


## 6. Weekly Organizer Security
### WeeklyOrganizerNode runs in safe mode:

### ✔ Allowed:
•	Move files
•	Archive files
•	Compress files
•	Generate summary

### ❌ Not Allowed:
•	Delete files
•	Modify sensitive files
•	Expand folder scope
•	Access blocked paths

### Weekly organizer must always:
•	Follow user enable feature – Run only if User Enables
•	Use pre approved folder scope
•	Log all actions
•	Skip any unsafe operation

## 7. Error Handling & Recovery
#### If user intent unclear → return to MyPCAssistantNode
-	Never assume cleanup intent.
#### If folder scope invalid → return to FolderScopeNode
-	User must re approve.
#### If MCP tool fails → retry or fallback
-	Never proceed with partial state.
#### If user rejects plan → SummaryNode
-	Abort cleanup safely.
#### If execution fails → RollbackNode
-	Undo all changes.
#### If weekly organizer fails → skip and log
-	Never retry destructive actions.

## 8. Audit Logging Requirements
### Every action must be logged:
•	Timestamp
•	Action type
•	File path (redacted if sensitive)
•	Node that triggered it
•	HITL approval status
•	Result (success/failure)
### Logs must:
•	Never contain file contents
•	Never contain sensitive data
•	Never leave the local machine

## 9. User Privacy Rules
### CleanSlate AI must:
•	Never upload files
•	Never upload metadata
•	Never upload logs
•	Never send file contents to LLM
•	Never store user data externally
All processing is local only.

## 10. Security Testing Requirements - Covered by STRIDE + Semgrep
### Before deployment, the agent must pass:
#### ✔ Folder Scope Penetration Test
Ensure no tool escapes allowed_paths.
#### ✔ Sensitive File Protection Test
Ensure sensitive files cannot be deleted.
#### ✔ HITL Enforcement Test
Ensure destructive actions require approval.
#### ✔ Rollback Test
Ensure undo works reliably.
#### ✔ Weekly Organizer Safety Test
Ensure no deletes occur in safe mode.

## 11. Future Security Enhancements
(Not included in current release- Check SDD)
-	Cloud storage permission scopes
-	Vision based sensitive image detection
-	Encrypted local backups
-	Multi device secure sync
-	Zero trust folder access tokens


================================================================================

#                       SemGrep Implimentation

## What Semgrep rules to Implement

### ✅ 1. Pre commit (local gate)

### ✅ 2. Antigravity remediation loop

## Status: FULLY IMPLEMENTED

### 1.	Hardcoded secrets
### 2. Unsafe file operations
### 3. Sensitive file mishandling
### 4. Path traversal
### 5. Subprocess execution
### 6. Weekly organizer safety
### 7. Rollback safety

#### Note: More rules will be added as we build our agent
