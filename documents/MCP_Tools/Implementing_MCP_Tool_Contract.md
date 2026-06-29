# Implement MCP Tools — the Local Tool Layer of CleanSlate AI-My PC Assistant according to the MCP Tool Spec and Security Spec
=======================================================================================
## MCP Tools — the Local Tool Layer of CleanSlate AI

**This is the layer that makes our agent actually capable of interacting with the filesystem safely and securely. Sets the API contract between our agent and the local environment.**

## Implement All MCP Tools(Local Tools Only) defined in MCP TOOL SPEC #3:

**In the antigravity cleanslate-pc-assistant directory,**

## Step1: — Create MCP Tool Package

### • Prompt:
```
Using MCP TOOL SPEC as a reference, implement all MCP tools defined in “Spec #3 — MCP Tool Spec (Local Tools Only)” for CleanSlate AI – My PC Assistant. These tools must be safe, deterministic, metadata-only, and fully compliant with Semgrep safety rules.

====================================================
1. Create MCP Tool Package
====================================================

Create directory:
app/mcp_tools/

Create __init__.py and individual tool modules:
- list_files.py
- read_file_metadata.py
- compute_hash.py
- move_file.py
- delete_file.py
- create_folder.py
- compress_files.py
- write_log.py
- read_log.py
- move_to_authenticated_folder.py

Each tool must:
- Follow the exact input/output schema in Spec #3
- Enforce folder_scope_policy
- Reject blocked_paths
- Never read file contents
- Never upload file contents
- Never delete sensitive files
- Require HITL for destructive actions
- Log all actions via write_log tool
- Fail safely with descriptive errors

Once done, I will provide instructions for step 2. Implement Tool Registry. Follow semgrep and git-mini skills to commit at every step.

```
### • Confirm: 
- MCP Tool Package Implemented
- Tests Passed


## Step2: — Implement Tool Registry

### • Prompt:
```
Using MCP TOOL SPEC in documents/MCP_Tools folder as a reference, implement all MCP tools defined in “Spec #3 — MCP Tool Spec (Local Tools Only)” for CleanSlate AI – My PC Assistant. These tools must be safe, deterministic, metadata-only, and fully compliant with Semgrep safety rules.

====================================================
2. Implement Tool Registry
====================================================

Create:
app/mcp_tools/registry.py

Registry must:
- Register all tools by name
- Provide get_tool(name)
- Provide list_tools()
- Provide test_tool(name, **kwargs)

CLI commands “cleanslate tools list” and “cleanslate tools test” will use this registry.

Optional: 
1. Use a clean registry dictionary
python
TOOLS = {
    "list_files": list_files.run,
    "read_file_metadata": read_file_metadata.run,
    ...
}
2. Add structured error handling
•	Unknown tool → return a structured MCP error object
•	Missing args → return a descriptive error
•	Policy violations → bubble up tool-level errors cleanly
3. Add a safety wrapper
Every tool call inside test_tool() should:
•	enforce folder_scope_policy
•	catch exceptions
•	redact sensitive paths
•	log the test call
4. Add a simple schema validator
Optional but helpful:
•	Validate input schema before calling tool
•	Validate output schema before returning
This keeps MCP tools predictable.

	```
### Confirm: Link - walkthrough_ MCP Tool Registry

## Step3: — Tool Implementations (Exact Spec Compliance)

### • Prompt:
```
Using MCP TOOL SPEC in documents/MCP_Tools folder as a reference, implement all MCP tools defined in “Spec #3 — MCP Tool Spec (Local Tools Only)” for CleanSlate AI – My PC Assistant. These tools must be safe, deterministic, metadata-only, and fully compliant with Semgrep safety rules.

====================================================
3. Tool Implementations (Exact Spec Compliance)
====================================================

General Requirements (All Tools)
- Use app/mcp_tools/utils.py for:
  - is_path_allowed_by_policy(path)
  - is_sensitive(path)
  - is_authenticated_folder(path)
- Never read or upload file contents (metadata-only), except streaming reads in compute_hash.
- Enforce folder_scope_policy and blocked_paths inside each tool (not in registry).
- Return structured MCP outputs or MCP error objects:
  {
    "error": {
      "type": "ToolError" | "SchemaError" | "ToolNotFound",
      "message": "...",
      "details": { ... }
    }
  }
- Comply with all Semgrep safety rules (no-file-content-reading, no-sensitive-data-in-logs, etc.).

----------------------------------------------------
TOOL 1 — list_files
----------------------------------------------------
- Must list files in allowed paths only.
- Must reject blocked/system paths.
- Must return metadata only:
  - name, path (sanitized), size, timestamps, is_directory.

----------------------------------------------------
TOOL 2 — read_file_metadata
----------------------------------------------------
- Must NOT open file contents.
- Must return:
  - size, created_at, modified_at, extension, mime_type.
- Must reject blocked/system/sensitive paths when required by spec.

----------------------------------------------------
TOOL 3 — compute_hash
----------------------------------------------------
- Must compute SHA256 using streaming chunk hashing.
- Must reject sensitive or blocked paths before opening.
- Must use a small, clearly scoped streaming read loop with # nosemegrep on that loop only.
- Must not log or expose raw file bytes.

----------------------------------------------------
TOOL 4 — move_file
----------------------------------------------------
- Must respect folder_scope_policy and blocked_paths.
- Must not move sensitive files unless destination is an authenticated folder (is_authenticated_folder).
- Must fail safely with MCP error if policy or sensitivity checks fail.
- Must log action via write_log tool (no absolute paths in logs).

----------------------------------------------------
TOOL 5 — delete_file
----------------------------------------------------
- Must require hitl_approved=True (HITLApprovalNode).
- Must reject sensitive files outright.
- Must respect safe_mode (no deletes when safe_mode=True).
- Must log action via write_log.
- Must never delete files in blocked/system paths.

----------------------------------------------------
TOOL 6 — create_folder
----------------------------------------------------
- Must not create folders in blocked/system paths.
- Must auto-create parent directories only if allowed by policy.
- Must return sanitized path metadata.

----------------------------------------------------
TOOL 7 — compress_files
----------------------------------------------------
- Must not compress sensitive files without explicit approval.
- Must skip sensitive items and report them in output.
- Must create ZIP archive safely in allowed paths.
- Must log action via write_log.

----------------------------------------------------
TOOL 8 — write_log
----------------------------------------------------
- Must redact sensitive paths and absolute filesystem locations.
- Must be append-only.
- Must write JSONL entries with structured fields (action, path, result, timestamp).
- Must never include file contents or raw data.

----------------------------------------------------
TOOL 9 — read_log
----------------------------------------------------
- Must redact sensitive paths on read.
- Must support a limit parameter.
- Must return entries as List[str] or structured objects per Spec #3.
- Must avoid loading excessively large logs into memory.

----------------------------------------------------
TOOL 10 — move_to_authenticated_folder
----------------------------------------------------
- Must only move files flagged as sensitive (is_sensitive(path)=True).
- Destination must be authenticated (is_authenticated_folder) and allowed by policy.
- Must not expose file contents.
- Must log action via write_log.

====================================================
Verification
====================================================
- Add/extend tests in tests/unit/test_mcp_tools.py for:
  - Allowed vs blocked paths.
  - Sensitive vs non-sensitive behavior.
  - HITL and safe_mode enforcement.
  - Streaming hash behavior.
  - Logging redaction.
- Run:
  - uv run pytest
  - uv run semgrep scan --config=.semgrep/sdd-safety-rules.yaml --error
- Commit:
  - Subject: "mcp-tools"
  - Body: "Refine MCP tool implementations to match Spec #3, policy enforcement, and Semgrep safety rules."

```
###	Confirm: MCP layer is Built

## Step4: — Integrate Tools with ADK Nodes

### • Prompt: 
```
Using the MCP TOOL SPEC and the completed MCP tool implementations, integrate all MCP tools into the ADK 2.0 agent graph nodes for CleanSlate AI – My PC Assistant.

====================================================
4. Integrate Tools with ADK Nodes
====================================================

Goal:
Wire each ADK node to call the correct MCP tools, ensuring:
- deterministic behavior
- safe-mode enforcement
- HITL enforcement
- sensitive-file protections
- folder_scope_policy enforcement
- MCP error format compliance
- Semgrep safety compliance

Update the following nodes:

----------------------------------------------------
FileDiscoveryNode
----------------------------------------------------
Use:
- list_files
- read_file_metadata

Behavior:
- Discover files only within allowed scope.
- Return sanitized metadata inventory.

----------------------------------------------------
ClassificationNode
----------------------------------------------------
Use:
- read_file_metadata

Behavior:
- Fetch metadata for classification.
- Never read file contents.

----------------------------------------------------
DuplicateDetectionNode
----------------------------------------------------
Use:
- compute_hash

Behavior:
- Compute streaming SHA256 hashes.
- Skip sensitive or oversized files.

----------------------------------------------------
SensitiveDetectionNode
----------------------------------------------------
Use:
- read_file_metadata

Behavior:
- Inspect metadata for sensitivity heuristics.
- Never open file contents.

----------------------------------------------------
ExecutionNode
----------------------------------------------------
Use:
- move_file
- delete_file
- create_folder
- compress_files
- move_to_authenticated_folder
- write_log

Behavior:
- Execute safe operations only.
- Enforce HITL for deletes.
- Enforce safe_mode.
- Log all actions via write_log.

----------------------------------------------------
RollbackNode
----------------------------------------------------
Use:
- move_file
- write_log

Behavior:
- Reverse previous actions safely.
- Log rollback operations.

----------------------------------------------------
SummaryNode
----------------------------------------------------
Use:
- read_log

Behavior:
- Return sanitized audit logs.
- Redact sensitive paths.

----------------------------------------------------
WeeklyOrganizerNode
----------------------------------------------------
Use:
- list_files
- read_file_metadata
- move_file
- compress_files
- write_log

Behavior:
- Perform weekly cleanup tasks.
- Enforce folder_scope_policy.
- Log all weekly actions.

====================================================
Verification
====================================================
- Extend node tests to validate MCP tool calls.
- Ensure nodes return MCP-compliant error formats.
- Run:
  - uv run pytest
  - uv run semgrep scan --config=.semgrep/sdd-safety-rules.yaml --error
- Commit:
  - Subject: "node-mcp-integration"
  - Body: "Integrate MCP tools with ADK nodes following Spec #3 and safety contract."

```
### Confirm: Integrated with ADK Node. Tests Passed 

## Step5: — Update CLI (Developer Commands)

### • Prompt: Complete
```
Using the MCP TOOL SPEC and the completed MCP tool implementations, update the CLI (Developer Commands) for CleanSlate AI – My PC Assistant.

====================================================
5. Update CLI (Developer Commands)
====================================================

Goal:
Extend the CleanSlate CLI with developer-facing commands that expose MCP tool registry functionality for debugging, validation, and inspection.

Implement the following commands:

----------------------------------------------------
cleanslate tools list
----------------------------------------------------
Description:
Display all registered MCP tools from app/mcp_tools/registry.py.

Requirements:
- Call registry.list_tools()
- Print each tool name in normalized form
- Include short metadata (description, input schema keys)
- No filesystem access; registry-only

----------------------------------------------------
cleanslate tools test <tool_name> [args]
----------------------------------------------------
Description:
Execute a single MCP tool through registry.test_tool() for developer debugging.

Requirements:
- Normalize <tool_name> using registry normalization rules
- Parse optional key=value arguments from CLI
- Call registry.test_tool(normalized_name, **parsed_args)
- Print either:
  - Success result (JSON)
  - MCP error object (JSON) exactly as returned by the registry
- Must not bypass MCP safety or policy checks
- Must not perform direct file operations

----------------------------------------------------
Verification
----------------------------------------------------
- Add tests in tests/unit/test_cli_tools.py:
  - tools list prints all registry tools
  - tools test executes tools and prints MCP error formats correctly
  - invalid tool names return ToolNotFound MCP errors
- Run:
  - uv run pytest
  - uv run semgrep scan --config=.semgrep/sdd-safety-rules.yaml --error
- Commit:
  - Subject: "cli-tools"
  - Body: "Add developer CLI commands for MCP tool listing and testing."
```
### Confirm: Agent CLI wired to MCP

## Step6: — Semgrep Safety Enforcement

### • Prompt:
```
====================================================
6. Semgrep Safety Enforcement
====================================================

Goal:
Ensure all MCP tools, nodes, and CLI commands comply with the full Semgrep safety contract for CleanSlate AI – My PC Assistant.

Enforce the following rules across the codebase:

----------------------------------------------------
no-file-content-reading
----------------------------------------------------
- MCP tools must never read file contents.
- Only compute_hash may open files, and only in a narrow streaming loop with # nosemegrep.

----------------------------------------------------
no-content-upload-to-llm
----------------------------------------------------
- No MCP tool or node may send file contents, previews, or raw bytes to any LLM client.
- Only metadata is allowed.

----------------------------------------------------
no-sensitive-data-in-logs
----------------------------------------------------
- write_log must redact sensitive paths.
- read_log must return redacted entries.
- No absolute paths or raw data in logs.

----------------------------------------------------
file-ops-must-use-folder-scope
----------------------------------------------------
- All file operations must respect folder_scope_policy.
- No direct os operations in nodes; only MCP tools may touch the filesystem.

----------------------------------------------------
no-direct-config-paths
----------------------------------------------------
- Nodes and tools must not hardcode config paths.
- Only load_policy() may read configuration files (with # nosemegrep).

----------------------------------------------------
no-absolute-paths-in-cli-output
----------------------------------------------------
- CLI commands must never print absolute filesystem paths.
- All tool results must be sanitized before printing.

----------------------------------------------------
# nosemegrep usage
----------------------------------------------------
- Add # nosemegrep only where required:
  - load_policy() config reads
  - compute_hash streaming loop
  - rollback copy2 operation (delete rollback)
- No other bypasses allowed.

====================================================
Verification
====================================================
- Run Semgrep:
  uv run semgrep scan --config=.semgrep/sdd-safety-rules.yaml --error
- Confirm:
  - 0 violations
  - All MCP tools, nodes, and CLI commands comply with safety rules
- Commit:
  - Subject: "semgrep-safety"
  - Body: "Apply full Semgrep safety enforcement across MCP tools, nodes, and CLI."

```
### Confirm: Semgrep is Implemented

## Step7: — Tests (tests/test_mcp_tools.py)

### • Prompt:
```
====================================================
7. Tests (tests/test_mcp_tools.py)
====================================================

Goal:
Ensure every MCP tool and registry function is fully covered by deterministic, metadata-only, policy-compliant unit tests.

Add tests for each MCP tool:

----------------------------------------------------
list_files
----------------------------------------------------
- Lists files and directories within allowed scope
- Rejects symlinks, junctions, and traversal attempts
- Normalizes returned paths

----------------------------------------------------
read_file_metadata
----------------------------------------------------
- Returns metadata only (size, timestamps, extension)
- Rejects sensitive files
- Rejects directories
- Enforces folder_scope_policy

----------------------------------------------------
compute_hash
----------------------------------------------------
- Computes SHA256 via streaming
- Rejects files > 2GB
- Rejects sensitive files
- Returns correct hash for small files

----------------------------------------------------
move_file
----------------------------------------------------
- Moves files within allowed scope
- Rejects sensitive → non-authenticated moves
- Rejects blocked paths
- Enforces safe_mode

----------------------------------------------------
delete_file
----------------------------------------------------
- Requires hitl_approved=True
- Rejects sensitive files
- Rejects safe_mode
- Returns correct MCP error structure

----------------------------------------------------
create_folder
----------------------------------------------------
- Creates folder inside allowed scope
- Rejects traversal and blocked paths

----------------------------------------------------
compress_files
----------------------------------------------------
- Creates ZIP archive
- Skips sensitive files
- Rejects blocked paths

----------------------------------------------------
write_log
----------------------------------------------------
- Writes redacted audit entries
- Rotates logs >10MB
- Enforces metadata-only logging

----------------------------------------------------
read_log
----------------------------------------------------
- Returns sanitized audit entries
- Rejects absolute paths
- Enforces max entry limits

----------------------------------------------------
move_to_authenticated_folder
----------------------------------------------------
- Moves sensitive files to authenticated destination
- Rejects non-sensitive files
- Enforces folder_scope_policy

----------------------------------------------------
Registry Tests
----------------------------------------------------
registry.list_tools
- Returns all registered tools
- Names normalized

registry.test_tool
- Executes tools with parsed kwargs
- Returns MCP error objects verbatim
- Rejects unknown tools
- Rejects schema violations

====================================================
Verification
====================================================
- Add tests in tests/test_mcp_tools.py
- Run:
  uv run pytest
  uv run semgrep scan --config=.semgrep/sdd-safety-rules.yaml --error
- Commit:
  Subject: "mcp-tools-tests"
  Body: "Add full MCP tool and registry test coverage."

```
### Confirm: MCP Tools Tests Complete

## Step8: — STRIDE Threat Model Update

### • Prompt:
```
Using the updated MCP tools, ADK 2.0 node wiring, Semgrep safety rules, and audit logging, update the STRIDE threat model for CleanSlate AI – My PC Assistant.

====================================================
8. STRIDE Threat Model Update
====================================================

Goal:
Refresh the STRIDE threat model to reflect:
- MCP-only filesystem access
- metadata-only processing
- Semgrep safety enforcement
- structured audit logging
- HITL + safe_mode controls
- folder_scope_policy

Update the threat model document (threat_model.md) with:

----------------------------------------------------
System Boundaries & Entry Points
----------------------------------------------------
- ADK 2.0 nodes (FileDiscovery, Classification, SensitiveDetection, DuplicateDetection, Execution, Rollback, Summary, WeeklyOrganizer)
- MCP tools layer (list_files, read_file_metadata, compute_hash, move_file, delete_file, create_folder, compress_files, write_log, read_log, move_to_authenticated_folder)
- CLI developer commands (cleanslate tools list/test)
- Policy loader (folder_scope_policy, safe_mode, HITL flags)
- Audit logger (write_log/read_log)

----------------------------------------------------
STRIDE Analysis (Updated for MCP + Semgrep)
----------------------------------------------------
For each category, document threats, mitigations, and residual risk:

Spoofing:
- Tool name spoofing, node misuse
- Mitigations: registry normalization, ToolNotFound errors, HITL for destructive ops

Tampering:
- Unauthorized file changes, rollback misuse
- Mitigations: folder_scope_policy, safe_mode, HITL, rollback copy2, Semgrep file-ops-must-use-folder-scope

Repudiation:
- User denies actions taken by agent
- Mitigations: structured JSONL audit logs, UTC timestamps, append-only, write_log/read_log, rotation with atomic replace

Information Disclosure:
- Sensitive file leakage, path leakage
- Mitigations: metadata-only tools, sensitive rejection, path redaction in logs and CLI, no-file-content-reading, no-content-upload-to-llm

Denial of Service:
- Large file hashing, log growth, excessive scans
- Mitigations: 2GB hashing limit, 10MB log rotation, folder_scope_policy limits, safe_mode

Elevation of Privilege:
- Bypassing HITL/safe_mode, escaping folder scope
- Mitigations: HITL required for delete, safe_mode blocking, validate_path_safety, symlink/junction guards, Semgrep no-unsafe-realpath/no-direct-config-paths

----------------------------------------------------
STRIDE Updates Section
----------------------------------------------------
Add a dedicated “STRIDE Updates” section summarizing:

- MCP-only filesystem boundary
- metadata-only architecture
- Semgrep safety enforcement (list key rules)
- audit logging guarantees
- CLI safety (no absolute paths, registry-only)
- residual risks and future improvements

====================================================
Verification
====================================================
- Ensure threat_model.md is consistent with:
  - current MCP tools
  - node wiring
  - Semgrep rules
  - audit logging behavior
- Commit:
  - Subject: "stride-update"
  - Body: "Refresh STRIDE threat model for MCP tools, ADK nodes, Semgrep safety, and audit logging."
```

### Confirm: STRIDE TEst PAssed

## Step9: —  Final Steps

### • Prompt:
```
====================================================
9. Final Steps
====================================================

Goal:
Run the full test suite, apply all pre-commit checks, and finalize the MCP integration work.

Commands:
- uv run pytest
- pre-commit run --all-files

Verification:
- All tests must pass (nodes, MCP tools, registry, CLI, planner, rollback, weekly organizer)
- Semgrep must report 0 findings
- No absolute paths, no unsafe file access, no policy violations
- CLI developer commands must operate correctly (tools list/test)
- STRIDE threat model must reflect MCP-only boundaries

Commit:
Subject: "mcp"
Body: "Implement all MCP tools, registry, node integration, CLI developer commands, Semgrep safety enforcement, and STRIDE threat model updates."

```
### Confirm: MCP_Final_Steps Test Passed






