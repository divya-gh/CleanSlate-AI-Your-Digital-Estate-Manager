# 📘 SPEC #1 — SDD MASTER SPEC

## CleanSlate AI – My PC Assistant (Autonomous Digital Clutter Management Agent)
#### Tagline: “Your AI Chief of Staff for digital organization and storage management.” 

**This is the master specification — the source of truth for everything the system must do.**

**All other specs (ADK, MCP, Security, Deployment, CLI, Skills) follow this document.**

## 1. Purpose of This Document (Why This Spec Exists)
### This spec defines:
•	What CleanSlate AI- My PC Assistant must do
•	What problems it solves
•	What behaviors it supports
•	What safety rules it must follow
•	What the user experience looks like
•	What constraints the system must respect

It does not describe implementation details — those belong in the ADK, MCP, and Deployment specs.

**Note:** This is the contract for the entire system.

## 2. Project Identity
### Product Name: CleanSlate AI – My PC Assistant
### Tagline: Your AI Chief of Staff for Digital Organization and Storage Management
### Repository: cleanslate-ai-my-pc-assistant
### Description:
CleanSlate AI is an autonomous, multi agent system that intelligently manages digital clutter, protects sensitive files, organizes storage, and provides a conversational PC assistant — all with strict human in the loop safety.

## 3. Problem Definition (Why This Agent Matters)
### Modern computers accumulate massive digital clutter:
•	Downloads folders with thousands of files
•	Duplicate documents and photos
•	Old screenshots
•	Large forgotten videos
•	Unorganized project folders
•	Cloud storage limits
•	Sensitive files stored in unsafe locations

**This clutter wastes time, increases cognitive load, and creates privacy risks.**

**The problem is universal. Everyone experiences it, and no existing tool solves it intelligently.**

## 4. Goal and Vision (What This Agent Should Achieve)
### Build an autonomous, safe, human approved digital organization agent that:
•	Scans local + cloud storage`(Future)`
•	Classifies files intelligently
•	Detects sensitive information
•	Identifies duplicates
•	Suggests cleanup actions
•	Requests human approval
•	Executes cleanup safely
•	Auto organizes weekly
•	Provides conversational assistance
•	Learns user preferences over time

#### This is not a “cleanup tool.” It is a Digital Estate Manager.

## 5. User Personas (Who This Agent Serves)
### 1. Everyday User : 
#### Wants a clean computer without losing important files.
### 2. Power User / Developer : 
#### Has messy project folders, large files, and duplicates.
### 3. Business User : 
#### Needs safe handling of sensitive documents (tax, legal, financial).


## 6. High Level Behaviors (What the Agent Must Do)

### ✔ 1. Folder Scope Approval (Mandatory Safety Step)

#### Before CleanSlate AI does anything, it must:
•	Ask the user which folders it is allowed to scan
•	Ask which folders it is allowed to organize
•	Ask which folders it must never touch
•	Store this as the Folder Scope Policy
•	Enforce this policy in all future operations

**Note:** Unchecked paths are completely ignored. Blocked paths are never scanned, read, or modified.
**This is a hard safety boundary.**

### ✔ 2. File Discovery
#### Scan local and cloud storage for:
•	Downloads
•	Desktop
•	Documents
•	Screenshots
•	Project folders
•	Cloud drive folders

#### Collect metadata:
•	Size
•	Type
•	Path
•	Last accessed
•	Hash (optional)

### ✔ 3. Classification
#### Use LLM reasoning to classify files into categories:
•	Resume
•	Tax document
•	Bank Statemnet
•	Medical record
•	DL & SSN
•	Screenshot
•	Invoice
•	School file
•	Source code
•	Media
•	Misc

### ✔ 4. Duplicate Detection
#### Identify:
•	Exact duplicates (hash match)
•	Near duplicates (similar name/size)

## ✔ 5. Sensitive Info Detection
#### Detect:
•	SSNs
•	Banking documents
•	Credit Card
•	Password files
•	API keys
•	Passport files
•	Legal/medical/ID documents

Sensitive files are never deleted.

### ✔ 6. Storage Optimization
#### Suggest:
•	Archive
•	Compress
•	Move
•	Delete (safe items only)

### ✔ 7. HITL Review
#### Before executing actions, CleanSlate AI must:
•	Explain findings
•	Show confidence scores
•	Show estimated storage recovery
•	Provide reasoning
•	Request approval

No destructive action happens without explicit approval.

### ✔ 8. Execution
#### Perform approved actions safely.
•	Move
•	Delete
•	Archive
•	Compress
•	Create folders

Move sensitive files to authenticated folder

### ✔ 9. Weekly Auto Organize
#### Triggered via Pub/Sub:
•	If enabled by the user: Uses pre approved folder scope
•	Runs in safe mode, no deletions
•	Moves/archives only
•	If sensitive files are found- move it to authenticated folder
•	Sends summary

### ✔ 10. Conversational Assistant (“My PC Assistant”)
#### User can ask:
•	“Find the file ‘ambient expense agent’.”
•	“Show me all files > 1GB.”
•	“Organize my screenshots.”
•	“What did you clean last week?”


### ✔ 11. Memory & Personalization
#### Agent learns:
•	User keeps coding projects
•	User archives screenshots
•	User never deletes tax docs

Future recommendations adapt automatically.

## 7. Safety Rules (How the Agent Stays Safe)
o	🚫 Never delete without explicit approval
o	🚫 Never delete sensitive files
o	🚫 Never touch system folders	
o	🚫 Never scan or modify unapproved folders
o	🚫 Never touch blocked folders
o	🚫 Never upload file contents without permission
o	✔ Always run in dry run mode first
o	✔ Always provide reasoning
o	✔ Always log actions
o	✔ Always allow rollback
o	✔ Always move sensitive files to authenticated folder
o	✔ Always protect sensitive files
o	✔ Always enforce Folder Scope Policy
##### ✔ Ask user permission
    •	Agent must ask user to approve folder paths before scanning
    •	Agent must never scan or modify unapproved paths
    •	Agent must maintain a Folder Scope Policy
    •	Agent must allow user to update the policy anytime

#### Note: These rules are mandatory.

## 8. HITL Interaction Model (How the User Approves Actions)

### Step 1 — Agent proposes an action plan

### Example:
```
**I found 37 duplicate files.**
**Estimated storage recovery:** 3.4 GB
**Confidence:** 98%
**Reason:** Identical SHA hash
```

### Step 2 — User reviews
#### User sees:
•	File groups
•	Explanations
•	Confidence
•	Proposed actions

### Step 3 — User approves or rejects

Agent must not proceed without approval.

## 9. Non Goals (What the Agent Will NOT Do)
•	Will not modify system files
•	Will not delete sensitive documents
•	Will not upload user data without permission
•	Will not run destructive actions automatically
•	Will not act outside approved folder scope or without HITL approval


## 10. Success Criteria (How We Know It Works)
### ✔ Functional
•	Correctly identifies clutter
•	Correctly detects sensitive files
•	Correctly identifies duplicates
•	Executes cleanup safely
### ✔ Safety
•	No accidental deletion
•	No sensitive file loss
•	No unauthorized actions
### ✔ User Experience
•	Clear explanations
•	Easy approvals
•	Useful conversational assistant
### ✔ Technical
•	ADK graph works end to end
•	MCP tools function reliably
•	Pub/Sub weekly job runs
•	Agent CLI commands work


## 11. Dependencies (What This Spec Relies On)
•	ADK Agent Graph Spec
•	MCP Tool Contract Spec
•	Security Spec
•	Deployment Spec
•	Agent CLI Spec
•	Skills Spec
All other specs must follow this master spec.


## 12. Future Improvements (Add this to SDD)
### 1. Cloud Storage Integration
•	Google Drive
•	OneDrive
•	Dropbox
•	iCloud
### 2. Multi Device Sync
•	Sync cleanup preferences across devices
•	Shared folder scope policy
### 3. Real Time File Monitoring
•	Detect clutter as it appears
•	Auto organize new downloads
### 4. AI Based Folder Structure Suggestions
•	Recommend folder hierarchies
•	Auto create project folders
### 5. Duplicate Photo Detection (Vision based)
•	Near duplicate image detection
•	Blurry photo detection
### 6. App Specific Cleanup
•	VSCode clutter
•	Jupyter notebooks
•	Browser downloads
•	Zoom recordings
### 7. Cloud Backup Before Cleanup
•	Backup files before deletion
•	Restore from cloud
### 8. Multi Agent Collaboration
•	One agent for scanning
•	One for classification
•	One for sensitive detection
•	One for planning
### 9. User Preference Learning
•	Learn what user tends to keep
•	Learn what user tends to delete
### 10. Mobile Companion App
•	View cleanup reports
•	Approve actions
•	Trigger cleanup remotely
