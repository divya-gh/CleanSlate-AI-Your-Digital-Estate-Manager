# 🟦 CleanSlate AI — Your PC Assistant
A secure, intelligent, multi‑step ADK 2.0 agent that organizes your PC, protects sensitive files, and restores digital clarity.

## 🖼️ Project Cover Image
(Insert your image here — /assets/cleanslate-banner.png)

## 🟦 1. Vision & Problem Statement
**Modern users accumulate thousands of files across their PCs — resumes, identity documents, downloads, screenshots, schoolwork, work artifacts, and duplicates. Over time, this creates:**

•	Security risks (exposed identity documents, financial files)
•	Productivity loss (hard to find important files)
•	Storage inefficiency (duplicates, unused content)
•	Organizational chaos (no structure, no cleanup habits)


## Traditional cleanup tools are:
•	Manual
•	Unsafe
•	Non intelligent
•	Not privacy aware
•	Not rollback capable


## Our Vision
#### CleanSlate AI was built to demonstrate how modern AI agents can deliver:
•	Safe automation
•	Intelligent file organization
•	Sensitive file protection
•	Multi step workflows
•	Interrupt driven UI
•	Enterprise grade security
•	Full traceability
•	Rollback guarantees
**This project showcases your ability to design, build, secure, and communicate a modern AI agent system using ADK Agent 2.0, MCP, Agent CLI, Pub/Sub, and Spec‑Driven Development (SDD).**

---

## ✨ 2. What CleanSlate AI Does (Features & Workflow)
CleanSlate AI acts autonomously but respects strict boundaries to ensure user safety and data privacy. it is a multi‑step, interrupt‑driven PC assistant that executes as a multi-node Directed Acyclic Graph (DAG) built with the Agent Development Kit (ADK 2.0):

- **Mandatory Folder Scope Approval**: Asks for and strictly enforces allowed/blocked directories before taking any action:        
- **Intelligent File Discovery**: Scans local storage (Desktop, Downloads, Documents) and collects file metadata securely.
- **AI-Powered Classification**: Uses LLM reasoning to categorize files (Resume, Tax document, Medical record, Source code, Media, etc.).
- **Duplicate & Sensitive Detection**: Identifies exact/near duplicates and detects sensitive information (SSNs, DL, Banking docs, Passport, Passwords,API Keys) to protect them from deletion. 
- **Storage Optimization**: Suggests archiving old content, compressing, moving, or deleting duplicates and safe items to recover storage space.
- **Human-In-The-Loop (HITL) Review**: Provides explanations, confidence scores, and reasoning before requesting user approval for any destructive actions.
- **Execution & Rollback**: Executes approved actions with safety checks, rollback metadata, and logging.** Moves `sensitive files` safely **Authenticated Secure Folder**. Organizes files into structured categories and rovides rollback for all destructive actions.
- **Summary & Logging:** Produces a professional, color‑coded action log and cleanup summary and centralized logging capturing every proposed & executed action, failure & rollback, Sensitive file detections, Node transitions and pub/sub events for traceability.
- **Weekly Auto-Organize (Ambient Agent)**: A background Pub/Sub job that automatically organizes your PC weekly based on your preferences.
- **Conversational Assistant**: Ask natural language queries like *"Find the file 'ambient expense agent'"* or *"Organize my screenshots."*
- **sandbox environments**: Runs safely in the sandox environment (Kaggle, cloud VMs)

---

## 🔄 The Agentic Workflow

CleanSlate AI executes as a multi-node Directed Acyclic Graph (DAG) built with the Agent Development Kit (ADK 2.0). 

1. **Intent Routing (`MyPCAssistantNode`)**: Routes conversational queries to the right sub-flow (cleanup vs. search).
2. **Folder Scope Security (`FolderScopeNode`)**: Establishes the mandatory explicit security perimeter for the operation.
3. **File Discovery (`FileDiscoveryNode`)**: High-speed, metadata-only recursive traversal of approved directories.
4. **Classification (`ClassificationNode`)**: LLM-driven reasoning to categorize each file (e.g. Resume, Tax, Code, Media).
5. **Sensitive Detection (`SensitiveDetectionNode`)**: Uses strict heuristic and LLM checks to isolate highly sensitive files (SSNs, Passwords).
6. **Duplicate Detection (`DuplicateDetectionNode`)**: Groups identical files by tracking metadata and exact hashes.
7. **Optimization Planning (`OptimizationPlannerNode`)**: Generates an actionable cleanup plan (Move, Archive, Delete).
8. **HITL Approval (`HITLApprovalNode`)**: Formats the plan into an interactive UI and halts the graph execution until the user explicitly approves.
9. **Execution (`ExecutionNode`)**: Employs MCP tools to safely execute the approved plan (with built-in rollback logic).
10. **Summary & Dashboard (`SummaryNode`)**: Outputs the final recovery statistics and the secure pin-protected vault status.

---

## 🏗️ 3. System Architecture Overview
CleanSlate AI is built entirely via **Spec-Driven Development (SDD)**, meaning every feature traces directly back to a unified Master Specification while following a modular, enterprise‑grade architecture.

**CleanSlate AI uses ADK Agent 2.0, MCP, Agent CLI, Pub/Sub, Semgrep Rules, STRIDE Threat MODEL and Antigravity.**

##### High‑Level Architecture Diagram (ASCII)
```
                   ┌──────────────────────────────┐
                   │        User Interface         │
                   │  (Checkboxes, Toggles, Table) │
                   └───────────────┬──────────────┘
                                   │ Interrupts
                                   ▼
                    ┌──────────────────────────────┐
                    │        ADK Agent 2.0          │
                    │   (Ambient, Pub/Sub Driven)   │
                    └───────────────┬──────────────┘
                                   │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌──────────────┐          ┌────────────────┐          ┌──────────────────┐
│ FolderScope  │          │ Optimization   │          │   Execution       │
│ Node         │          │ Planner Node   │          │   Node            │
└──────────────┘          └────────────────┘          └──────────────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌──────────────┐          ┌────────────────┐          ┌──────────────────┐
│ Sensitive     │          │ Table Renderer │          │ Rollback Engine  │
│ Detector      │          └────────────────┘          └──────────────────┘
└──────────────┘
        │
        ▼
┌──────────────────────────────┐
│        Summary Node           │
│ (Professional Dashboard UI)   │
└──────────────────────────────┘
```

## 🟦 4. Technologies Used
#### CleanSlate AI demonstrates:

### ✔ ADK Agent 2.0
•	Multi step workflows
•	Interrupt driven UI
•	Node graph architecture
•	Ambient agent state

### ✔ MCP Server
•	Tool orchestration
•	File operations
•	Secure execution

### ✔ Agent CLI
•	Local testing
•	Node debugging
•	Workflow validation

### ✔ Pub/Sub (Ambient Agent)
•	Event driven communication
•	State propagation
•	Interrupt handling

### ✔ Antigravity
•	Node graph editor
•	Agent manifest
•	Logging console
•	SDD workflow

### ✔ Logging & Traceability
•	Full action logs
•	Rollback logs
•	Sensitive file logs
•	Error logs

### ✔ SKILLS.md
•	File scanning
•	Sensitive classification
•	Duplicate detection
•	Archive skill
•	Rollback skill
•	Logging skill
•	Table rendering skill

## 🟦 5. Security Architecture
#### CleanSlate AI is built using `Security 7 Principles`.

### 1. Secure by Design
•	Sensitive file detection
•	Authenticated Secure Folder
•	PIN + security question
•	Runtime safety checks

### 2. Secure by Default
Sensitive files never deleted

Sensitive files never moved to unsafe folders

Rollback enabled for all destructive actions

3. Secure in Deployment
Sandbox‑safe file operations

No external network calls

No unsafe path traversal

4. Zero Trust
Every file validated

Sensitive files require authentication

No implicit trust of user input

5. Defense in Depth
Detection → classification → secure storage → logging

6. Operational Security
Full traceability

Action logs

Rollback logs

Error logs

7. Privacy by Design
Sensitive filenames masked

Sensitive details hidden in summaries

No PII exposed in logs

## 🟦 6. Semgrep Rules
#### CleanSlate AI uses Semgrep for static analysis:
•	Detect unsafe file operations
•	Prevent path traversal
•	Prevent insecure regex patterns
•	Prevent insecure logging
•	Prevent accidental PII exposure
•	Enforce ADK node safety patterns


## 🟦 7. STRIDE Threat Model
### Threat	Mitigation

#### S – Spoofing	PIN + security question
#### T – Tampering	Rollback + secure folder
#### R – Repudiation	Full action logs
#### I – Information Disclosure	Sensitive file masking
#### D – Denial of Service	Bounded folder scanning
#### E – Elevation of Privilege	No privileged operations


## 🟦 8. Workflows
#### ✔ Folder selection
#### ✔ Sensitive file detection
#### ✔ Optimization planning
#### ✔ Cleanup execution
#### ✔ Rollback
 ####✔ Summary dashboard

## 🟦 9. Outputs
#### CleanSlate AI produces:
•	Professional cleanup summary
•	Color coded action logs
•	Sensitive file protection report
•	Storage recovery report
•	Rollback capability report

## 🟦 10. Setup Instructions
#### Clone the Repository
```
git clone https://github.com/<your-username>/CleanSlate-AI-PC-Assistant.git
cd CleanSlate-AI-PC-Assistant
```

#### Install Dependencies
```
pip install -r requirements.txt
```

#### Run the Agent (Agent CLI)
```
agent run cleanslate_agent
```
- Run in Antigravity
- Open the project folder → run the agent → test nodes → inspect logs.

#### Run in Playground
- Upload the agent → test interrupts → validate UI.

## 🟦 11. Demo Video Placeholder
(Insert your YouTube demo link here)

🟦 12. Demo Tables (Side‑by‑Side)
Kaggle Demo	GitHub Demo
Kaggle Notebook URL	GitHub Repo URL
Kaggle Writeup URL	README.md
Kaggle Video	GitHub Video


## 🟦 13. Logging & Traceability
#### CleanSlate AI logs:
•	Every action
•	Every failure
•	Every rollback
•	Every sensitive file detection
•	Every optimization decision
•	Every node transition

## 🟦 14. Built with Spec‑Driven Development (SDD)
#### CleanSlate AI follows:

- **Requirements → Spec → Architecture → Nodes → UI → Testing → Docs**

- **Full traceability from spec to implementation**

## 🟦 15. Ambient Agent (Pub/Sub)
#### CleanSlate AI uses:
•	Pub/Sub channels for node communication
•	Ambient state propagation
•	Interrupt driven UI updates

## 🟦 16. Antigravity
#### Developed entirely in Antigravity, using:
•	Node graph editor
•	Agent manifest
•	Interrupt testing
•	Logging console
•	Spec Driven Development workflow


### 🟦 17. License
MIT License 
