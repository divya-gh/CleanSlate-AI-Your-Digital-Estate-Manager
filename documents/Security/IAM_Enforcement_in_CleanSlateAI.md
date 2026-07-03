# IAM Enforcement in CleanSlate AI (Implementation)

## CleanSlate AI – My PC Assistant
#### AI Chief of Staff for Digital Organization and Storage Management.

==================================================================================

## 1. HITLApprovalNode = Human Identity Gate
**This is the core IAM mechanism.**

#### ✔ Destructive actions require human identity approval
•	delete_file
•	bulk deletes
•	sensitive moves
•	irreversible actions

### ExecutionNode checks:
```
if not hitl_approved:
    reject destructive action
```
**This is identity-based access control.**

## 2. Sensitive File Rules = Access Control

### SensitiveDetectionNode flags:
•	tax documents
•	passports
•	SSNs
•	financial statements
•	medical records

### ExecutionNode enforces:

#### ✔ Sensitive files cannot be:
•	deleted
•	compressed
•	moved to non-secure folders
•	hashed (if >2GB or flagged)

**This is resource-level IAM.**

## 3. Authenticated Folder = Secure Access Boundary

### MCP tool move_to_authenticated_folder enforces:

### ✔ Sensitive files may only be moved to:
```
CLEANSLATE_SECURE_FOLDER
```
### ExecutionNode checks:
```
if sensitive and destination != authenticated_folder:
    reject
```

**This is destination-level IAM.**

## 4. Folder Scope Policy = Path-Level IAM

### FolderScopeNode defines:
•	allowed_paths
•	blocked_paths
•	system_paths

### Every MCP tool calls:
```
validate_path_safety()
```

### Which enforces: 
#### ✔ No access to:
•	blocked directories
•	outside allowed scope
•	traversal (../)
•	symlinks
•	junctions

**This is filesystem IAM.**

## 5. Weekly Organizer Safe Mode = Role-Based IAM

### WeeklyOrganizerNode runs with a restricted role:

### ✔ Allowed:
- move_file
- compress_files
- write_log

### ❌ Not allowed:
- delete_file
- sensitive modifications
- folder scope changes

**This is role-based IAM (RBAC).**

## 6. Semgrep Safety Contract = Policy Enforcement IAM

### 26-rule Semgrep contract enforces:
•	no direct FS access
•	no content read
•	no unsafe shutil
•	no traversal
•	no symlink following
•	no sensitive deletes
•	no absolute paths

**This is policy-level IAM.**

## 7. STRIDE v2.0 = Governance IAM

### Your STRIDE threat model documents:
•	identity threats
•	access threats
•	privilege escalation
•	sensitive data exposure
•	residual risks

**This is governance IAM.**

## Summary — IAM Enforcement in CleanSlate AI


IAM Principle	                                      Implementation
Identity approval	                              HITLApprovalNode
Access control	                                  SensitiveDetectionNode + ExecutionNode
Secure destination	                              Authenticated folder enforcement
Path-level IAM	                                  folder_scope_policy + validate_path_safety
Role-based IAM	                                  WeeklyOrganizer safe mode
Policy IAM	                                      Semgrep safety contract
Governance IAM	                                  STRIDE v2.0


## Review: 
✔ All 7 IAM principles implemented
✔ All tested
✔ All documented
✔ All enforced at runtime