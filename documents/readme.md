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
CleanSlate AI acts autonomously but respects strict boundaries to ensure user safety and data privacy. it is a multi‑step, interrupt‑driven ambient PC assistant with:

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
- **Sandbox Environments**: Runs safely in the sandox environment (Kaggle, cloud VMs)

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

**CleanSlate AI uses ADK Agent 2.0, MCP, Agent CLI, Pub/Sub, ADK SKILLS, Semgrep Rules, STRIDE Threat MODEL and Antigravity.**

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
---

##  🛠️  4. Core Technologies Used

#### ✔ ADK Agent 2.0
•	Multi step workflows
•	Interrupt driven UI
•	Node graph architecture
•	Ambient agent state

#### ✔ MCP Server
•	Tool orchestration
•	File operations
•	Secure execution

#### ✔ Agent CLI
•	Rapid scaffolding
•	Building, evaluating and deploying the agent
•	Node debugging, Local testing
•	Workflow validation

#### ✔ Pub/Sub (Ambient Agent)
•	Event driven communication
•	State propagation
•	Interrupt handling
•	Triggers autonomous weekly background organization

#### ✔ Antigravity
•	Node graph editor
•	Agent manifest
•	Logging console
•	SDD workflow

#### ✔ Logging & Traceability
•	Full action logs
•	Audibility & Rollback capability
•	Sensitive file & error logs
•	Node transitions and pub/sub events

#### ✔ Semgrep Security Hooks
•	Statistically safe CI/CD and commit pipeline.

#### ✔ STRIDE Threat Model
•	Enforces SDD safety rule
• Reason about threats at design time.

#### ✔ SKILLS.md
•	File scanning
•	Sensitive classification
•	Duplicate detection
•	Archive skill
•	Rollback skill
•	Logging skill
•	Table rendering skill

---

## 🔒 7-Pillar Security Architecture (The 7 Principles & STRIDE)
#### CleanSlate adheres strictly to the 7 Pillars of Security (Design Philosophy) as well as 7-Layers of  AI Agent Security Architecture (Operational Controls): .

<table style="width: 100%; border-collapse: collapse; border: 1px solid #e2e8f0;">
  <thead>
    <tr style="background-color: #f8fafc; border-bottom: 2px solid #cbd5e1;">
<th width="50%" align="left" style="padding:14px; background-color:#0B132B; color:#0000FF; font-family:Consolas, Monaco, 'Courier New', monospace; font-size:18px; font-weight:bold; letter-spacing:0.5px; border:1px solid #1C2541;">🏛️ 7 SECURITY PILLARS</th>
<th style="width: 50%; padding: 12px; text-align: left; font-family:Consolas, Monaco, 'Courier New', monospace; font-size: 18px;">7 Layers of Security</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-bottom: 1px solid #e2e8f0;">
      <td style="padding: 10px; vertical-align: top; border-right: 1px solid #cbd5e1;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#0A192F;">🛡️ 1. SECURE_BY_DESIGN</span><br>
        <span style="font-size: 11px; color: #475569; padding-left: 20px; display: inline-block;"><i>• Sensitive content detection</i></span><br>
        <span style="font-size: 11px; color: #475569; padding-left: 20px; display: inline-block;"><i>• Authenticated Secure vault</i></span><br>
        <span style="font-size: 11px; color: #475569; padding-left: 20px; display: inline-block;"><i>• PIN + security question</i></span><br>
      </td>
      <td style="padding: 10px; vertical-align: top;">
        <b>1. Physical Layer</b><br>
        • Local host hardware machine boundary
      </td>
    </tr>
    <tr style="border-bottom: 1px solid #e2e8f0; background-color: #f8fafc;">
      <td style="padding: 12px; vertical-align: top; border-right: 1px solid #cbd5e1;">
        <b>2. Secure by Default</b><br>
        • Sensitive files never deleted or moved to unsafe folders<br>
        • Safety-first execution flow with dry-run<br>
        • Rollback enabled for all destructive actions
      </td>
      <td style="padding: 12px; vertical-align: top;">
        <b>2. Data Layer</b><br>
        • Isolated environment asset & state directory
      </td>
    </tr>
    <tr style="border-bottom: 1px solid #e2e8f0;">
      <td style="padding: 12px; vertical-align: top; border-right: 1px solid #cbd5e1;">
        <b>3. Secure in Deployment</b><br>
        • Sandbox‑safe file operations<br>
        • No external network calls<br>
        • No unsafe path traversal
      </td>
      <td style="padding: 12px; vertical-align: top;">
        <b>3. Operating System Layer</b><br>
        • Scoped system-level path & OS access hooks
      </td>
    </tr>
    <tr style="border-bottom: 1px solid #e2e8f0; background-color: #f8fafc;">
      <td style="padding: 12px; vertical-align: top; border-right: 1px solid #cbd5e1;">
        <b>4. Zero Trust</b><br>
        • Every file validated<br>
        • Sensitive files require authentication<br>
        • No implicit trust of user input
      </td>
      <td style="padding: 12px; vertical-align: top;">
        <b>4. Network Layer</b><br>
        • Air-gapped boundary limits (Zero cloud APIs)
      </td>
    </tr>
    <tr style="border-bottom: 1px solid #e2e8f0;">
      <td style="padding: 12px; vertical-align: top; border-right: 1px solid #cbd5e1;">
        <b>5. Continuous Monitoring</b><br>
        • Automated active background validation
      </td>
      <td style="padding: 12px; vertical-align: top;">
        <b>5. Application Layer</b><br>
        • Cryptographic vault isolation runtime
      </td>
    </tr>
    <tr style="border-bottom: 1px solid #e2e8f0; background-color: #f8fafc;">
      <td style="padding: 12px; vertical-align: top; border-right: 1px solid #cbd5e1;">
        <b>6. Encrypted State Logs</b><br>
        • Tamper-proof transaction logging history
      </td>
      <td style="padding: 12px; vertical-align: top;">
        <b>6. AI Agent Layer</b><br>
        • LLM prompt guardrails and validation rules
      </td>
    </tr>
    <tr style="border-bottom: 1px solid #e2e8f0;">
      <td style="padding: 12px; vertical-align: top; border-right: 1px solid #cbd5e1;">
        <b>7. Failure Isolation</b><br>
        • Process sandboxing during structural faults
      </td>
      <td style="padding: 12px; vertical-align: top;">
        <b>7. User Access Layer</b><br>
        • Multifactor identity verification (PIN + Prompt)
      </td>
    </tr>
  </tbody>
</table>

----

* **Secure Vault**: Protected `Authenticated_Secure` directory with localized access controls.
* **Access Recovery**: Dual-factor authentication using a localized PIN and customizable security question.
* **Runtime Constraints**: Strict runtime safety gates preventing unauthorized system calls.

### 2. Secure by Default
* **Non-Destructive Vaulting**: Sensitive files are never deleted; they are securely moved to the vault.
* **Implicit Dry-Run**: Safety-first execution flow presenting proposed changes prior to making modifications.
* **Universal Rollback**: Complete transaction logs recorded to revert any file system operations (rename, move, delete).

### 3. Secure in Deployment
* **Sandbox Integration**: Tested and verified to operate safely in restricted cloud sandboxes (e.g., Kaggle, remote VMs).
* **No Exfiltration**: Zero external network requests allowed during execution, retaining all sensitive data locally.
* **Traversal Defense**: Absolute path enforcement and blocking of parent directory traversal (`..`).

### 4. Zero Trust
* **Explicit Scoping**: The Folder Scope Policy acts as a hard boundary—unapproved directories are completely invisible to the agent.
* **Authentication Boundaries**: Re-authenticates requests targeting the secure vault to prevent privilege creep.
* **Input Sanitization**: Rejects and sanitizes raw user inputs, including leading/trailing quote stripping and slash normalization.

### 5. Defense in Depth
* **Layered Pipeline**: Executes in distinct sequential phases: Discovery ➔ Local Pattern Matching ➔ LLM Classification ➔ Vault Encryption ➔ Transaction Logging.
* **Heuristics & LLM Co-Verification**: Fallback regex rules verify classification to ensure security even when API connections are degraded.

### 6. Operational Security
* **Full Auditability**: Logs every node transition, LLM decision, user input, and file modification.
* **Telemetry Protection**: Erases sensitive file details from execution summaries and telemetry outputs.
* **Graceful Degradation**: Recovers safely from file locks, permissions issues, or API timeout failures without leaving partial transactions.

### 7. Privacy by Design
* **Filename Masking**: Redacts and masks sensitive filenames (e.g., `[RESTRICTED]/SSN_****.txt`) in logs and UI lists.
* **Content Blindness**: Restricts the LLM from reading file content; the agent works exclusively with metadata.
* **PII Redaction**: Auto-filters any personally identifiable information (PII) from user-facing reports.

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
