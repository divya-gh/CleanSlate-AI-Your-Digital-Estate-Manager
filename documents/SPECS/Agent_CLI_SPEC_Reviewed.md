# 📘 SPEC #6 — Agent CLI Spec SPEC 

## CleanSlate AI – My PC Assistant
#### AI Chief of Staff for Digital Organization and Storage Management.

==================================================================================
**Note: Full Compliance Check - complete**

## 1. Purpose
**The Agent CLI provides a command-line interface for interacting with CleanSlate AI – My PC Assistant.**
### Exposing:
•	User-facing commands for search and cleanup
•	Developer commands for graph and tools debugging
•	Safety commands for dry-runs and safe-mode
It is the primary way to run and test the agent locally.

## 2. CLI Overview
#### Executable name: cleanslate
#### Invocation pattern: cleanslate <command> [options]
#### Commands are grouped into:
•	User commands
•	Developer commands
•	Safety & control commands
-----------------------------------------------------------------------------------------
## SPEC REVIEW
#### Below is a structured checklist comparing:
•	Spec requirement
•	Implementation
•	Compliance status

-----------------------------------------------------------------------------------------
## 3. User Commands

### 3.1 cleanslate run
### Purpose: Start My PC Assistant in interactive mode.
### Behavior:
•	Launches the assistant UI (terminal or local app).
•	Routes user queries through MyPCAssistantNode.
### Example:
Bash
```
cleanslate run

```
## Implementation: 
✔ Implemented as “Interactive multi turn CLI session.” 
✔ Uses agent graph.

## Status: PASS


### 3.2 cleanslate search "<query>"
### Purpose: Run a one-off file search via the agent.
### Behavior:
•	Uses MyPCAssistantNode → FileDiscoveryNode (search mode).
•	Returns matching files in human-readable or JSON format.
### Options:
•	--json → output as JSON
•	--path <folder> → limit search to a specific allowed folder
### Example:
Bash:
```
cleanslate search "tax return 2023" –json
```
## Implementation: 
✔ Implemented 
✔ Restricted by policy 
✔ JSON output supported 

## Status: PASS

### 3.3 cleanslate cleanup
### Purpose: Start an interactive cleanup session.
### Behavior:
•	Triggers MyPCAssistantNode with cleanup intent.
•	Runs FolderScopeNode to collect allowed/blocked folders.
•	Executes full cleanup workflow with HITL approval.
### Example:
Bash
```
cleanslate cleanup
```
## Implementation:
✔ Implemented 
✔ --dry-run supported 
✔ HITL integrated 
✔ Full pipeline 

## Status: PASS

## 3.4 cleanslate weekly-run
### Purpose: Manually trigger the WeeklyOrganizerNode.
### Behavior:
•	Runs weekly organizer in safe mode (no deletes).
•	Uses pre-approved folder scope.
•	Produces a summary report.
### Example:
Bash
```
cleanslate weekly-run
```
## Implementation:
✔ Implemented 
✔ Weekly automation flag respected 
✔ Safe mode enforced 
✔ Early exit when disabled 

## Status: PASS

## 3.5 cleanslate logs
### Purpose: View recent agent logs.
### Behavior:
•	Reads from CLEANSLATE_LOG_PATH.
•	Redacts sensitive paths.
### Options:
•	--limit <n> → number of entries
•	--json → JSON output
### Example:
Bash
```
cleanslate logs --limit 50
```

## Implementation:
✔ Implemented 
✔ Redaction enforced 
✔ JSON + limit supported 

## Status: PASS

## 3.6 cleanslate rollback
### Purpose: Invoke RollbackNode to undo last cleanup batch.
### Behavior:
Uses execution_log to restore previous state.
### Example:
Bash
```
cleanslate rollback
```

## Implementation:
✔ Implemented 
✔ RollbackNode fully functional 

## Status: PASS

## 3.7 cleanslate scope reset
### Purpose: Reset the stored folder scope policy.
### Behavior:
•	Clears allowed_paths and blocked_paths.
•	Next cleanup requires re-approval via FolderScopeNode.
### Example:
Bash
```
cleanslate scope reset
```

 Implementation:
✔ Implemented via reset_policy() 
 Status: PASS

## 4. Developer Commands

### 4.1 cleanslate graph visualize
### Purpose: Visualize the ADK graph.
### Behavior:
•	Outputs a diagram or DOT file of nodes and transitions.
### Example:
Bash
```
cleanslate graph visualize
```

## Implementation:
✔ Implemented (graph visualization supported) 

## Status: PASS

### 4.2 cleanslate graph debug
### Purpose: Run the graph in debug mode.
### Behavior:
•	Logs node transitions verbosely.
•	Useful for testing workflows.
### Example:
Bash
```
cleanslate graph debug
```

## Implementation:
✔ Implemented 
✔ Debug logging integrated

## Status: PASS

### 4.3 cleanslate tools list
### Purpose: List all MCP tools and their contracts.
### Behavior:
•	Reads from MCP tool registry.
### Example:
Bash
```
cleanslate tools list
```
## Implementation: [⚠ NOT IMPLEMENTED YET] - Implemented

## Status: [PENDING ] COMPLETE

## 4.4 cleanslate tools test <tool_name>
### Purpose: Run a test call against a specific MCP tool.
### Behavior:
•	Validates connectivity and permissions.
### Example:
Bash
```
cleanslate tools test list_files --path ~/Documents
```

## Implementation: ⚠ NOT IMPLEMENTED YET - Implemented

## Status: [PENDING ] COMPLETE 

## 5. Safety & Control Commands

### 5.1 cleanslate dry-run
### Purpose: Run cleanup without executing actions.
### Behavior:
•	Runs full pipeline up to OptimizationPlannerNode.
•	Skips ExecutionNode.
•	Shows proposed plan only.
### Example:
Bash
```
cleanslate dry-run
```
## Implementation:
✔ Implemented 
✔ Verified in tests 

## Status: PASS


### 5.2 cleanslate safe-mode on
### Purpose: Force non-destructive behavior globally.
### Behavior:
•	Disables delete_file calls.
•	Restricts ExecutionNode to moves/archives only.
### Example:
Bash
```
cleanslate safe-mode on
```
## Implementation:

✔ Implemented 
✔ Safe-mode integrated into config 

## Status: PASS


## 6. Environment & Setup
### Requirements:
### Python: 3.11
### Virtual env: recommended
### Install:
Bash
```
pip install -r requirements.txt
```

### Required env vars:
•	CLEANSLATE_SECURE_FOLDER
•	CLEANSLATE_LOG_PATH
### Optional:
CLEANSLATE_WEEKLY_MODE (for scheduled runs)

## Implementation:
✔ Verified 
✔ Config auto-repair 
✔ Atomic writes 

## Status: PASS

## 7. Output Formats
•	Default: human-readable text
•	JSON mode: via --json flag
•	Verbose mode: via --verbose flag for detailed logs and node traces.

## Implementation:
✔ JSON supported 
✔ Verbose supported 

## Status: PASS

## 8. Error Handling
•	**Invalid folder scope:**
o	Commands that require cleanup will prompt re-run of FolderScopeNode.
•	**Missing env vars:**
o	CLI prints clear error and exits with non-zero status.
•	**MCP tool failure:**
o	CLI shows tool name, error, and suggests tools test.
•	**Graph failure:**
o	CLI suggests graph debug and logs details.

## Implementation :
✔ Folder scope errors handled 
✔ Config errors auto-repaired 
✔ Graph debug suggestion implemented 
⚠ MCP tool errors pending (expected) 

## Status: PASS (for implemented features)

## 9. Future CLI Extensions
•	Cloud sync commands (for future cloud storage integration).
•	Vision-based photo cleanup commands (once vision features are added).
•	Remote approval commands (mobile or web UI integration).
**Not required for capstone.**
