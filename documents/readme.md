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

#### ✔ Semgrep Security Hooks(static analysis)
•	Detect unsafe file operations
•	Prevent path traversal & accidental PII exposure
•	Prevent insecure regex patternsc& logging
•	Prevent insecure 
•	Enforce ADK node safety patterns
•	Safe CI/CD and commit pipeline.

#### ✔ STRIDE Threat Model(Threat	Mitigation)
•	Enforces SDD safety rule to reason about threats at design time.
#### S – Spoofing	PIN + security question
#### T – Tampering	Rollback + secure folder
#### R – Repudiation	Full action logs
#### I – Information Disclosure	Sensitive file masking
#### D – Denial of Service	Bounded folder scanning
#### E – Elevation of Privilege	No privileged operations

#### ✔ SKILLS.md
•	File scanning
•	Sensitive classification
•	Duplicate detection
•	Archive skill
•	Rollback skill
•	Logging skill
•	Table rendering skill

---

## 🛡️ Security Architecture


| 🧱 07 SECURITY PILLARS (Design Philosophy) | 🧩 07 SECURITY LAYERS (Operational Controls) |
| :--- | :--- |
| **1. SECURE_BY_DESIGN 🔒**<br>• Sensitive File Isolation<br>• Authenticated Secure Vault<br>• Access Recovery: PIN + security question<br>• Runtime Safety Gates | **1. Infrastructure & Networking 🌐**<br>• Sandboxed execution<br>• FS access only through MCP tools<br>• Network isolation<br>• No uncontrolled paths |
| **2. SECURE_BY_DEFAULT ⚙️**<br>• Sensitive files never deleted or moved to vault<br>• Implicit dry-run: Safety-first execution<br>• Rollback enabled for all destructive actions | **2. DATA_LAYER 📊**<br>• Encrypts sensitive context<br>• Least-privilege access: No content Preview<br>• Logs/Summary redact sensitive path<br>• Partitions storage to avoid cross-tenant exposure |
| **3. SECURE_IN_DEPLOYMENT 🚀**<br>• Runs safely in sandboxed environments<br>• No Exfiltration: Zero external network<br>• Traversal Defense: Absolute path enforcement | **3. Model Security 💻**<br>• Treats prompts and rule files as source code<br>• Protects against tampering and injection<br>• Semgrep rules prevent unsafe LLM usage<br>• STRIDE v2.0 documents model-level threats |
| **4. ZERO_TRUST 🔑**<br>• Explicit Scoping: Blocked paths are invisible to agent<br>• Sensitive operations require authentication<br>• Input Sanitization: No implicit trust of user input | **4. Application & Runtime 🔌**<br>• Uses LLM firewalls and pre/post tool‑call hooks<br>• Gateways prevent unrestricted agent calls<br>• Semgrep rules enforce runtime safety<br>• Enforces safe-mode in runtime |
| **5. Defense in Depth 👁️‍🗨️**<br>• Layered Pipeline: Discovery ➔ Local Pattern Matching ➔ LLM Classification ➔ Vault Encryption ➔ Transaction Logging<br>• Heuristics & LLM Co-Verification: Fallback regex rules | **5. IAM Management 💎**<br>• Unique agent identity<br>• HITLApproval required for delete<br>• Secure file handling with IAM rules<br>• STRIDE v2.0 documents IAM threats |
| **6. Operational Security 📝**<br>• Full traceability through structured logs<br>• Telemetry Protection: Erases sensitive file details in summary and logs<br>• Rollback records and audit trails<br>• Graceful Degradation: Recovers safely from timeout failures | **6. Observability & Security Ops 🧠**<br>• Continuous monitoring via logs, traces, and metrics<br>• Detects drift or infinite loops<br>• Implementing JSONL structured logs<br>• Semgrep ensures no sensitive leakage<br>• STRIDE v2.0 includes observability threats |
| **7. Privacy by Design ⚡**<br>• Redacts and masks sensitive filenames<br>• No PII exposed in logs or summaries<br>• Restricts the LLM from reading file content<br>• Works exclusively with metadata<br>• Safe-mode operations throughout the graph | **7. Governance 👤**<br>• Ensures compliance with AI-risk frameworks<br>• STRIDE v2.0 (404+ lines)<br>• Semgrep safety contract (26+ rules)<br>• Residual risks documented<br>• Strict enforcement of SPEC governance in nodes |

#### **Note:** Every principle and layer is implemented, tested, and documented.

---

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
