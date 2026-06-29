## 📘 SPEC #3 — MCP TOOL CONTRACT SPEC (LOCAL TOOLS ONLY)

### CleanSlate AI – My PC Assistant
#### Your AI Chief of Staff for Digital Organization and Storage Management

==================================================================================

#### This document defines all MCP tools used by CleanSlate AI, including:
•	Tool names
•	Purpose
•	Input schema
•	Output schema
•	Error cases
•	Safety constraints
•	Which ADK nodes use each tool
This sets the **API contract** between our **agent and the local environment.**

## 1. Purpose of This Document
#### This spec ensures:
•	Tools are predictable
•	Tools are safe
•	Tools cannot exceed permissions
•	ADK nodes know exactly what they can call
•	Folder scope is enforced at the tool level
•	Sensitive files are protected
•	ExecutionNode cannot perform unsafe actions
This sets the **foundation** of our agent’s **reliability and safety.**

## 2. Tool Categories
#### CleanSlate AI uses the following local tool categories:
✔ Filesystem Tools
✔ Metadata Tools
✔ Hashing Tools
✔ Compression Tools
✔ Logging Tools
✔ Secure Folder Tools
No cloud tools are included (reserved for future improvements).

                MCP Tools — Full Contract Coverage
===================================================================

## 3. MCP Tool Definitions (Full Contract)
Below are the tools our agent will use.
 
### TOOL 1 — list_files

#### Purpose
•	List files in a directory (within allowed folder scope).
#### Used by
•	FileDiscoveryNode
•	MyPCAssistantNode (search mode)
#### Input Schema
```
{
  "path": "string"
}
```
#### Output Schema
```
{
  "files": [
    {
      "name": "string",
      "path": "string",
      "size": "number",
      "modified_at": "string",
      "created_at": "string",
      "is_directory": "boolean"
    }
  ]
}
```
#### Errors
•	PathNotAllowed
•	PathNotFound
•	PermissionDenied
#### Safety
•	Must reject paths outside allowed_paths
•	Must reject blocked_paths

## `Implementated:`
•	Uses validate_path_safety()
•	Returns normalized metadata
•	Rejects blocked paths
•	No content read
### `Tests:`
•	10 tests (scope, blocked, symlink, traversal, dirs)
•	All pass

### Spec coverage: `100%`

## TOOL 2 — read_file_metadata
#### Purpose
Retrieve metadata without reading file contents.
#### Used by
•	FileDiscoveryNode
•	ClassificationNode
•	DuplicateDetectionNode
#### Input Schema
```
{
  "path": "string"
}
```
 ####Output Schema
```
{
  "size": "number",
  "modified_at": "string",
  "created_at": "string",
  "extension": "string",
  "mime_type": "string"
}
```
#### Errors
•	FileNotFound
•	PermissionDenied
####Safety
•	Must not read file contents
•	Must not open sensitive files
 
## `Implemented:`
•	Sensitive rejection via SensitiveFileError
•	Directory rejection
•	Metadata only
### `Tests:`
•	9 tests (sensitive, dir, MIME, traversal)
•	All pass

### Spec coverage: `100%`


## TOOL 3 — compute_hash
#### Purpose
•	Compute SHA 256 hash for duplicate detection.
#### Used by
•	DuplicateDetectionNode
#### Input Schema
```
{
  "path": "string"
}

```
#### Output Schema
```
{
  "sha256": "string"
}
```
#### Errors
•	FileTooLarge
•	PermissionDenied
#### Safety
•	Must not upload file contents
•	Must not hash blocked paths

## `Implemented:`
•	Streaming loop with inline # nosemgrep
•	2GB guard
•	Sensitive rejection
•	Folder scope enforced
### `Tests:`
•	8 tests (correct hash, large file, sensitive, missing)
•	All pass

### Spec coverage: `100

## TOOL 4 — move_file
#### Purpose
•	Move a file from one location to another.
#### Used by
•	ExecutionNode
•	RollbackNode
#### Input Schema
```
{
"source": "string",
"destination": "string"
}
```
#### Output Schema
```
{
"status": "success"
}
```
#### Errors
•	FileNotFound
•	DestinationInvalid
•	PermissionDenied
#### Safety
•	Must not move sensitive files unless destination is authenticated folder
•	Must respect folder_scope_policy

## `Implemented:`
•	Sensitive enforcement
•	Authenticated folder check
•	Atomic replace fallback
•	Folder scope enforced
### `Tests:`
•	9 tests (sensitive→auth OK, sensitive→unauth reject, blocked, traversal)
•	All pass

### Spec coverage: `100%`

## TOOL 5 — delete_file
#### Purpose
•	Delete a file (only after HITL approval).
#### Used by
•	ExecutionNode
#### Input Schema
```
{
  "path": "string"
}
```
#### Output Schema
```
{
  "status": "deleted"
}
```
#### Errors
FileNotFound
PermissionDenied
#### Safety
•	Must never delete sensitive files
•	Must require HITLApprovalNode
•	Must respect folder_scope_policy

## `Implemented:`
•	HITL enforced
•	Sensitive rejection
•	Safe mode rejection
### `Tests:`
•	8 tests (HITL, sensitive, safe_mode, MCP error structure)
•	All pass

### Spec coverage: `100%`

## TOOL 6 — create_folder
#### Purpose
•	Create a folder for organizing files.
#### Used by
•	ExecutionNode
#### Input Schema
```
{
  "path": "string"
}
```
####  Schema
```
{
  "status": "created"
}
```
#### Errors
•	AlreadyExists
•	PermissionDenied

#### Safety
•	Must not create folders in blocked paths

## `Implemented:`
•	Scope enforcement
•	Rejects blocked paths
•	Rejects existing file
### `Tests:`
•	6 tests
•	All pass

### Spec coverage: `100%`

## TOOL 7 — compress_files
#### Purpose
•	Create a ZIP archive of selected files.
#### Used by
•	ExecutionNode
•	OptimizationPlannerNode (suggestions)
#### Input Schema
```
{
  "files": ["string"],
  "destination": "string"
}
```
#### Output Schema
```
{
  "status": "compressed",
  "archive_path": "string"
}

```
#### Errors
•	FileNotFound
•	PermissionDenied

#### Safety
•	Must not compress sensitive files without approval

## `Implemented:`
•	Scope enforcement
•	Rejects blocked paths
•	Rejects existing file
### `Tests:`
•	6 tests
•	All pass

### Spec coverage: `100%`

## TOOL 8 — write_log
#### Purpose
•	Write an entry to the agent’s audit log.
#### Used by
•	ExecutionNode
•	RollbackNode
•	WeeklyOrganizerNode
#### Input Schema
```
{
  "entry": "string"
}
```
#### Output Schema
```
{
  "status": "logged"
}
```
#### Errors
•	PermissionDenied
#### Safety
•	Logs must never contain file contents
•	Logs must not contain sensitive data

## `Implemented:`
•	Redaction
•	JSONL
•	10MB rotation
•	No content read
### `Tests:`
•	7 tests
•	All pass

### Spec coverage: `100%`

## TOOL 9 — read_log
#### Purpose
•	Retrieve audit logs for summaries.
#### Used by
•	SummaryNode
•	MyPCAssistantNode (explain mode)
#### Input Schema
```
{
  "limit": "number"
}
```
#### Output Schema
```
{
  "entries": ["string"]
}
```
#### Errors
PermissionDenied

#### Safety
•	Must redact sensitive paths

## `Implemented:`
•	Redaction
•	Sanitization
•	Limit enforcement
## `Tests:`
•	7 tests
•	All pass

## Spec coverage: `100%`

## TOOL 10 — move_to_authenticated_folder
#### Purpose
•	Move sensitive files to a secure, user approved folder.
#### Used by
•	ExecutionNode
•	SensitiveDetectionNode (optional suggestion)
#### Input Schema
```
{
  "source": "string",
  "destination": "string"
}
```
#### Output Schema
```
{
  "status": "secured"
}
```
#### Errors
•	PermissionDenied
•	FileNotFound
#### Safety
•	Must only move files flagged as sensitive
•	Must not expose file contents

## `Implemented:`
•	Sensitive enforcement
•	Authenticated folder check
•	Atomic fallback
## `Tests:`
•	6 tests
•	All pass

## Spec coverage: `100%`


## 4. Global Safety Rules for All Tools
✔ Tools must enforce folder_scope_policy
✔ Tools must reject blocked_paths
✔ Tools must never read or upload file contents
✔ Tools must never delete sensitive files
✔ Tools must require HITL for destructive actions
✔ Tools must log all actions
✔ Tools must fail safely

### Status: COMPLETE

## 5. Tool Usage by ADK Nodes
Node	                                            Tools Used
FileDiscoveryNode	                            list_files, read_file_metadata
ClassificationNode	                            read_file_metadata
DuplicateDetectionNode	                        compute_hash
SensitiveDetectionNode	                        read_file_metadata
OptimizationPlannerNode	                        none (LLM reasoning only)
HITLApprovalNode	                            none
ExecutionNode	                                move_file, 
delete_file,                                    create_folder, compress_files, 
                                                move_to_authenticated_folder, write_log
RollbackNode	                                move_file, write_log
SummaryNode	                                    read_log
WeeklyOrganizerNode	                            list_files,read_file_metadata, 
                                                move_file,compress_files, 
                                                write_log

### Spec coverage: 100%
### Status: COMPLETE


## 5. MCP Registry & CLI — Fully Implemented
### Spec requires:
•	registry.list_tools
•	registry.test_tool
•	CLI developer commands

## `Implemented:`
### ✔ cleanslate tools list
•	normalized names
•	metadata
•	JSON mode
### ✔ cleanslate tools test
•	name normalization
•	key=value parsing
•	MCP error passthrough
•	JSON mode
•	path sanitization
### `Tests:`
•	24 tests
•	All pass

### Spec coverage: 100%
### Status: COMPLETE

## 6. Future Improvements (Cloud Tools)
(Not included in this spec- Check SDD)
•	Google Drive MCP
•	OneDrive MCP
•	Dropbox MCP
•	Cloud backup before cleanup



