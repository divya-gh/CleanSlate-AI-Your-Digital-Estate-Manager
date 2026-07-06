# 📋 SPEC #2 — ADK AGENT GRAPH SPEC

## 🧹 CleanSlate AI – Your Digital Estate Manager
**AI Chief of Staff for Digital Organization and Storage Management.**

---
## 🎯 Goal – Provide Blueprint for implementing the agent.
**This document defines the agent architecture, nodes, transitions, inputs/outputs, HITL points, and safety boundaries for the ADK graph.**

## 1. ⚡ Purpose of This Document (Why This Spec Exists)
- The ADK Agent Graph Spec defines:  
        •	The nodes that make up CleanSlate AI  
        •	What each node does  
        •	What inputs/outputs each node expects  
        •	How nodes transition between each other  
        •	Where HITL (human in the loop) is required  
        •	How safety rules are enforced in the graph  

## 2. 🏛️ High Level Architecture Overview
- CleanSlate AI is a multi agent ADK graph composed of:

### 1.  Primary UI Entry Point
•	MyPCAssistantNode (all user interactions start here)

### 2.  Three main workflows
- 1.	Interactive Cleanup Workflow Triggered when user says “organize my PC”, “clean my laptop”, etc.  
- 2.	Search / Explain Workflow Triggered when user asks to find a file or explain something.  
- 3.	Automated Weekly Organizer Workflow Triggered by Pub/Sub, using pre approved folder scope.

### 3. Modes of Operation:

#### The graph supports two modes:
✔ Interactive Mode:  Triggered by user commands   
✔ Automated Mode -Ambient :  Triggered by Pub/Sub weekly event.

### 4. Node List (What Nodes Exist)
Below is the complete node list with purpose summaries.
|        **Node**	                 |                     **Purpose**                   |
|MyPCAssistantNode	                 |        Main UI, intent detection, routing         |
|FolderScopeNode	                 |        Ask user which folders are allowed/blocked |
|FileDiscoveryNode	                         Scan approved folders
ClassificationNode	                         Classify files
DuplicateDetectionNode	                         Detect duplicates
SensitiveDetectionNode	                         Detect sensitive files
OptimizationPlannerNode	                         Generate cleanup plan
HITLApprovalNode	                         Present plan for approval
ExecutionNode	                                 Execute approved actions
RollbackNode	                                 Undo last batch
SummaryNode	                                 Final report
WeeklyOrganizerNode	                         Automated weekly cleanup
 

## 4. Node by Node Specification (What Each Node Does + How It Works)

### 1. MyPCAssistantNode (ENTRY POINT)
#### Purpose
This is the main UI and the first node in every interactive session.
#### Responsibilities
•	Understand natural language  
•	Detect user intent  
•	Route to the correct workflow  
•	Never trigger cleanup automatically  
•	Only trigger FolderScopeNode when cleanup intent is detected
#### Inputs
```
#### user_query
```
#### Outputs
```
#### intent: {cleanup | search | explain | other}
```
#### Transitions
•	If cleanup → FolderScopeNode  
•	If search → FileDiscoveryNode (search mode)  
•	If explain → SummaryNode  
•	If other → respond conversationally  

### 2. FolderScopeNode (CONDITIONAL)
#### Purpose
- Ask user which folders are allowed or blocked.  
- Trigger -Only runs when MyPCAssistantNode detects cleanup intent.
#### Responsibilities
•	Ask user to select allowed folders    
•	Ask user to select blocked folders  
•	Save Folder Scope Policy  
•	Enforce safety boundaries
#### Inputs
cleanup_intent: true
#### Outputs
```
folder_scope_policy {
  allowed_paths[],
  blocked_paths[]
}
```
#### Transitions
→ FileDiscoveryNode

### 3. FileDiscoveryNode
**Purpose**:  
Scan only approved folders and Build inventory of files to analyze.
#### What it does
•	Scans only allowed_paths   
•	Ignores blocked_paths  
•	Collects metadata (size, type, path, last accessed, hash)
#### Inputs
```
folder_scope_policy
search_query (optional)
```
#### Outputs
```
file_inventory[]
```
#### Transitions
→ ClassificationNode → DuplicateDetectionNode → SensitiveDetectionNode

### 4. ClassificationNode
**Why**:  
LLM classification is required for intelligent cleanup.
#### What it does
•	Classifies each file into categories  
•	Uses metadata + size + description  
#### Inputs
```
file_inventory
```
#### Outputs
```
classified_files[]
```
#### Transitions
→ DuplicateDetectionNode → SensitiveDetectionNode

### 5. DuplicateDetectionNode
**Why**:  
Detect exact and near duplicates.
#### What it does
•	Computes hashes   
•	Detects exact duplicates  
•	Detects near duplicates
#### Inputs
```
file_inventory
```
#### Outputs
```
duplicate_groups[]
```
#### Transitions
→ SensitiveDetectionNode

### 6. SensitiveDetectionNode
**Purpose**:  
Detect sensitive files (PII, legal, financial). Sensitive files must never be deleted.
#### What it does
•	Detects PII    
•	Detects legal/financial/medical docs  
•	Flags sensitive files
#### Inputs
```
classified_files
duplicate_groups
```
#### Outputs
```
sensitive_files[]
```
#### Transitions
→ OptimizationPlannerNode

### 7. OptimizationPlannerNode
**Why**:   
Creates the cleanup plan.
#### Responsibilities
•	Suggests actions (move, archive, compress, delete safe items)   
•	Move sensitive files to authenticated folder  
•	Excludes blocked paths  
•	Estimates storage recovery  
•	Generates reasoning
#### Inputs
```
classified_files
duplicate_groups
sensitive_files
folder_scope_policy
```
#### Outputs
```
action_plan {
  actions[],
  reasoning[],
  estimated_recovery
}
```
#### Transitions
→ HITLApprovalNode

### 8. HITLApprovalNode
**Why**:  
Mandatory safety checkpoint.
#### What it does
•	Presents action plan to user  
•	Shows reasoning + confidence  
•	Waits for approval or rejection
#### Inputs
```
action_plan
```
#### Outputs
```
approved_actions[]
```
#### Transitions
If approved → ExecutionNode If rejected → SummaryNode

### 9. ExecutionNode
**Why**:  
Executes approved actions safely.
#### What it does
•	Move files  
•	Delete safe files  
•	Archive folders  
•	Compress large files  
•	Move sensitive files to authenticated folder  
•	Log all actions
#### Inputs
```
approved_actions
```
#### Outputs
```
execution_log[]
```
#### Transitions
→ SummaryNode

### 10. RollbackNode
**Why**
Allows undoing last cleanup batch.  
#### What it does
•	Reverses moves  
•	Restores deleted files (if possible)  
•	Reverses archives
#### Inputs
```
execution_log
```
#### Outputs
```
rollback_status
```
#### Transitions
→ SummaryNode

### 11. SummaryNode
**Purpose**:  
Provides final report.
#### What it does
•	Summarizes actions   
•	Shows storage recovered  
•	Shows sensitive files protected  
•	Logs results
#### Refinement
•	Include a human-readable report that the UI can display directly.  
•	SummaryNode must not attempt to re-execute or modify anything. It is a pure reporting node.  
#### Inputs
```
execution_log
```
#### Outputs
```
summary_report
```
#### Transitions
→ END


## 12. WeeklyOrganizerNode – AUTOMATED
Runs only If user enabled in MyPCAssistantNode
**Purpose**:  
✔Automated weekly cleanup.  
✔Pub/Sub automation rules  
✔ Safety model  
✔ Sensitive file protection:  
    o	✔ Sensitive files must be moved to the Authenticated folder  
    o	✔ Sensitive files must NOT be skipped  
    o	✔ Sensitive files must NOT be archived  
    o	✔ Sensitive files must NOT be deleted (safe mode already prevents this)  
    o	✔ Sensitive files must be included in the weekly summary as “protected”

✔ Blocked/system path protection  
✔ User enable/disable toggle  
✔ Safe mode execution (no deletes)  
✔ Proper graph transitions  
✔ Isolation from the main cleanup workflow

#### What it does
•	Triggered by Pub/Sub  
•	Uses pre approved folder scope  
•	Runs in safe mode (no deletes)  
•	Moves/archives only  
•	Generates summary
#### Inputs
```
Pub/Sub event
```
#### Outputs
```
Weekly summary
```
#### Transitions
→ FileDiscoveryNode (safe mode) → Classification → Planner → Execution → Summary

## 5. Graph Flow (How Nodes Connect)
#### Edges:
```
MyPCAssistantNode
    ↓ (if cleanup intent)
FolderScopeNode
    ↓
FileDiscoveryNode
    ↓
+----------------------------+
| ClassificationNode         |
| DuplicateDetectionNode     |
| SensitiveDetectionNode     |
+----------------------------+
    ↓
OptimizationPlannerNode
    ↓
HITLApprovalNode
    ↓
ExecutionNode
    ↓
SummaryNode

```
### Search Workflow
```
MyPCAssistantNode → FileDiscoveryNode (search mode) → MyPCAssistantNode
```
### Weekly Organizer Workflow
```
WeeklyOrganizerNode → FileDiscoveryNode (safe mode) → Classification → Planner → Execution → Summary
```
## 6. HITL Points (Where Human Approval Is Required)
Mandatory HITL:
•	FolderScopeNode  
•	HITLApprovalNode  
Optional HITL:
•	MyPCAssistantNode (when user asks for confirmation)  

## 7. Safety Enforcement in the Graph
#### ✔ Cleanup Intent Enforcement  
•	Cleanup workflows may only begin after MyPCAssistantNode detects explicit cleanup intent.  
•	FolderScopeNode must never run automatically.  
#### ✔ Folder Scope Policy enforced in:
•	FileDiscoveryNode  
•	DuplicateDetectionNode  
•	SensitiveDetectionNode  
•	OptimizationPlannerNode  
•	ExecutionNode  
#### ✔ Sensitive files protected in:
•	SensitiveDetectionNode  
•	OptimizationPlannerNode  
•	ExecutionNode  
#### ✔ No destructive actions without:
•	HITLApprovalNode  
#### ✔ WeeklyOrganizerNode runs in safe mode:
Runs only If user enabled in MyPCAssistantNode  
•	No deletions  
•	Moves/archives only  
•	Uses pre approved folder scope  

### Other safety Features to Note  
•	✔ No scanning outside allowed paths  
•	✔ No touching blocked paths  
•	✔ No deletion without approval  
•	✔ Sensitive files are never deleted 

## 8. Error Handling
•	If user intent unclear → return to MyPCAssistantNode  
•	If folder scope invalid → return to FolderScopeNode  
•	If MCP tool fails → retry or fallback   
•	If user rejects plan → SummaryNode  
•	If execution fails → RollbackNode  
•	If weekly organizer fails → skip action and log error  
This prevents accidental cleanup  

## Why Eror Handling?
### These are essential for:
•	Reliability
•	Predictability
•	User trust

