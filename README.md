# 🧹 CleanSlate AI — My PC Assistant
> **"Your AI Chief of Staff for Digital Organization and Storage Management."**
#### A secure, intelligent, multi‑step ADK 2.0 agent that organizes your PC, protects sensitive files, and restores digital clarity.
![CleanSlate AI](assets/cleanslate_corporate_banner.png)
---
## 🛎️ Track: `Concierge Agents`

## 📖 Problem Statement: Why CleanSlate AI?
**Modern users accumulate thousands of files across their PCs — multiple resumes, identity documents, photos, downloads, schoolwork, work artifacts, and duplicates old screenshots, large forgotten videos, unorganized project folders, cloud storage limits, and sensitive files stored in unsafe locations.. Over time, this creates:**

- Security risks (exposed identity documents, financial files)
- Productivity loss (hard to find important files)
- Storage inefficiency (duplicates, unused content)
- Organizational chaos (no structure, no cleanup habits)

This clutter wastes time, increases cognitive load, and creates privacy risks. While everyone experiences it, and no existing tool solves it intelligently.

---
## 🌟 The Vision & Technical Philosophy
CleanSlate AI was built to showcase the effective use of Agentic AI technologies to solve a universal user problem: digital clutter. The design philosophy centers around building a highly capable autonomous agent that prioritizes safety, transparency, and user value.

**The Project Story & Vision**: We wanted an AI Chief of Staff that acts as a proactive digital estate manager. Instead of just answering questions, the agent needed to take agency over background maintenance while respecting strict privacy boundaries.

#### CleanSlate AI demonstrates:
•	Safe automation
•	Intelligent file organization
•	Sensitive file protection
•	Multi step workflows
•	Interrupt driven UI
•	Enterprise grade security
•	Full traceability
•	Rollback guarantees

**Overall User Value:** By blending conversational UX with ambient background processing and strict Human-In-The-Loop (HITL) safeguards, CleanSlate AI delivers a premium, zero-anxiety digital cleanup experience.

---
## ✨ 2. What CleanSlate AI Does (Features & Workflow)
CleanSlate AI acts autonomously but respects strict boundaries to ensure user safety and data privacy. it is a multi‑step, interrupt‑driven ambient PC assistant with:

- **Mandatory Folder Scope Approval**: Asks for and strictly enforces allowed/blocked directories before taking any action:        
- **Intelligent File Discovery**     : Scans local storage (Desktop, Downloads, Documents) and collects file metadata securely.
- **AI-Powered Classification**      : Uses LLM reasoning to categorize files (Resume, Tax document, Medical record, Source code, Media, etc.).
- **Duplicate & Sensitive Detection**: Identifies exact/near duplicates and detects sensitive information (SSNs, DL, Banking docs, Passport, Passwords,API Keys) to protect them from deletion. 
- **Storage Optimization**           : Suggests archiving old content, compressing, moving, or deleting duplicates and safe items to recover storage space.
- **Human-In-The-Loop (HITL) Review**: Provides explanations, confidence scores, and reasoning before requesting user approval for any destructive actions.
- **Execution & Rollback**           : Executes approved actions with safety checks, rollback metadata, and logging.** Moves `sensitive files` safely **Authenticated Secure Folder**. Organizes files into structured categories and rovides rollback for all destructive actions.
- **Summary & Logging                :** Produces a professional, color‑coded action log and cleanup summary and centralized logging capturing every proposed & executed action, failure & rollback, Sensitive file detections, Node transitions and pub/sub events for traceability.
- **Weekly Auto-Organize (Ambient Agent)**: A background Pub/Sub job that automatically organizes your PC weekly based on your preferences.
- **Conversational Assistant**       : Ask natural language queries like *"Find the file 'ambient expense agent'"* or *"Organize my screenshots."*
- **Sandbox Environments**           : Runs safely in the sandox environment (Kaggle, cloud VMs)
  
---
## 🔄 The Agentic Routing
CleanSlate AI executes as a multi-node Directed Acyclic Graph (DAG) built with the Agent Development Kit (ADK 2.0). 

1. **Intent Routing:** - `MyPCAssistantNode` - Routes conversational queries to the right sub-flow (cleanup vs. search).
2. **Folder Scope Security:** - `FolderScopeNode` - Establishes the mandatory explicit security perimeter for the operation.
3. **File Discovery:** - `FileDiscoveryNode` - High-speed, metadata-only recursive traversal of approved directories.
4. **Classification:** - `ClassificationNode` - LLM-driven reasoning to categorize each file (e.g. Resume, Tax, Code, Media).
5. **Sensitive Detection:** - `SensitiveDetectionNode` - Uses strict heuristic and LLM checks to isolate highly sensitive files (SSNs, Passwords).
6. **Duplicate Detection:** - `DuplicateDetectionNode` - Groups identical files by tracking metadata and exact hashes.
7. **Optimization Planning:** - `OptimizationPlannerNode` - Generates an actionable cleanup plan (Move, Archive, Delete).
8. **HITL Approval:** - `HITLApprovalNode` - Formats the plan into an interactive UI and halts the graph execution until the user explicitly approves.
9. **Execution:** - `ExecutionNode` - Employs MCP tools to safely execute the approved plan (with built-in rollback logic).
10. **Summary & Dashboard:** - `SummaryNode` - Outputs the final recovery statistics and the secure pin-protected vault status.
    
---
## 🏗️ 3. System Architecture Overview
CleanSlate AI is built entirely via **Spec-Driven Development (SDD)**, meaning every feature traces directly back to a unified Master Specification while following a modular, enterprise‑grade architecture.
- **Requirements → Spec → Architecture → Nodes → UI → Testing → Docs**

**CleanSlate AI uses ADK Agent 2.0, MCP, Agent CLI, Pub/Sub, ADK SKILLS, Semgrep Rules, STRIDE Threat MODEL and Antigravity.**

##### High‑Level Architecture Diagram (ASCII)
```
                           ┌──────────────────────────────┐
                           │      Conversational UI       │
                           │  (Launcher Server, Web UI)   │
                           └──────────────┬───────────────┘
                                          │ User Query / Weekly Timer
                                          ▼
                           ┌──────────────────────────────┐
                           │      MyPCAssistantNode       │
                           │  (Intent Router & Dispatch)  │
                           └──────────────┬───────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
      ┌──────────────────────┐                        ┌──────────────────────┐
      │   FolderScopeNode    │                        │  WeeklyOrganizerNode │
      │ (Security Perimeter) │                        │ (Ambient Background) │
      └───────────┬──────────┘                        └───────────┬──────────┘
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          ▼
                              ┌──────────────────────┐
                              │  FileDiscoveryNode   │
                              │ (Traverses FS / OS)  │
                              └───────────┬──────────┘
                                          │ File Metadata
                                          ▼
                              ┌──────────────────────┐
                              │  ClassificationNode  │
                              │  (LLM Semantic Tag)  │
                              └───────────┬──────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
      ┌──────────────────────┐                        ┌──────────────────────┐
      │  SensitiveDetection  │                        │  DuplicateDetection  │
      │  (PII / Secret Scan) │                        │  (Exact/Near Hash)   │
      └───────────┬──────────┘                        └───────────┬──────────┘
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          ▼
                              ┌──────────────────────┐
                              │  OptimizationNode    │
                              │  (Action Planner)    │
                              └───────────┬──────────┘
                                          │ Proposed Plan
                                          ▼
                              ┌──────────────────────┐
                              │   HITLApprovalNode   │
                              │ (User Interruption)  │
                              └───────────┬──────────┘
                                          │ User Approved
                                          ▼
                              ┌──────────────────────┐
                              │    ExecutionNode     │
                              │  (MCP File Ops)      │
                              └───────────┬──────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
      ┌──────────────────────┐                        ┌──────────────────────┐
      │     SummaryNode      │                        │     RollbackNode     │
      │ (Dashboard Metrics)  │                        │  (Revert State)      │
      └──────────────────────┘                        └──────────────────────┘
```
---
###  🛠️  4. Core Technologies Used

#### ✔ ADK Agent 2.0
Multi step workflows
•	Interrupt driven UI
•	Node graph architecture
•	Ambient agent state

#### ✔ MCP Server
Tool orchestration
•	File operations
•	Secure execution

#### ✔ Agent CLI
Rapid scaffolding
•	Building, evaluating and deploying the agent
•	Node debugging, Local testing
•	Workflow validation

#### ✔ Pub/Sub (Ambient Agent)
Event driven communication
•	State propagation
•	Interrupt handling
•	Triggers autonomous weekly background organization

#### ✔ Antigravity
Node graph editor
•	Agent manifest
•	Logging console
•	SDD workflow

#### ✔ Logging & Traceability
Full action logs
•	Audibility & Rollback capability
•	Sensitive file & error logs
•	Node transitions and pub/sub events

#### ✔ Semgrep Security Hooks(static analysis)
Detect unsafe file operations
•	Prevent path traversal & accidental PII exposure
•	Prevent insecure regex patternsc& logging 
•	Enforce ADK node safety patterns
•	Safe CI/CD and commit pipeline.

#### ✔ Custom Agent Skills (Skills.md)
CleanSlate AI utilizes specialized local agent skills to automate secure workflows:
* **`git-mini`**: A secure, automated git commit-and-push workflow that prevents accidental commits of secrets/PII (such as `.env` or key files), validates that commit messages are meaningful and concise (≤10 characters), and automatically rebases upstream changes.
* **`stride-threat-model`**: A systematic threat modeling assessment tool mapping security boundaries, entry points, and data flows to identify and mitigate Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege (STRIDE) risks across all agent nodes.
* Other Skills: File scanning
•	Sensitive classification
•	Duplicate detection
•	Archive & Rollback skill
•	Logging & Table rendering skill

#### ✔ STRIDE Threat Model(Threat	Mitigation)
Enforces SDD safety rule to reason about threats at design time:
•	S – Spoofing	PIN + security question
•	T – Tampering	Rollback + secure folder
•	R – Repudiation	Full action logs
•	I – Information Disclosure	Sensitive file masking
•	D – Denial of Service	Bounded folder scanning
•	E – Elevation of Privilege	No privileged operations

---
## 🛡️ Security Architecture
#### CleanSlate AI adheres strictly to both 7-Pillars of Security    &     7-Layers of AI Agent Security to deliver enterprise‑grade protection. 

The Pillars define **why** security decisions are made, while the Layers define **where** those decisions are enforced. Together, they ensure CleanSlate AI is safe, compliant, and production‑ready.

#### This table shows them **side‑by‑side** for clarity.

|🔒 **7-PILLARS - SECURITY** *(Design Philosophy)*  | 🧩 **7-LAYERS - AI AGENT SECURITY** *(Operational Controls)* |
|------------------------------------------------|----------------------------------------------------------|
| **1. Secure by Design** 🔒 <br>• Sensitive file isolation <br>• Authenticated Secure Vault <br>• PIN + security question <br>• Runtime safety gates | **1. Infrastructure & Networking** 🌐 <br>• Sandboxed execution <br>• MCP‑only file access <br>• Network isolation <br>• No uncontrolled paths |
| **2. Secure by Default** ⚙️ <br>• Sensitive files never deleted <br>• Safety‑first dry‑run <br>• Rollback for all destructive actions | **2. Data Layer** 📊 <br>• Least‑privilege access <br>• Sensitive path redaction <br>• Partitioned storage |
| **3. Secure in Deployment** 🚀 <br>• Sandbox‑safe <br>• Zero external network <br>• Logging safety enforcement <br>• Absolute path traversal defense | **3. Model Security** 💻 <br>• Prompts treated as source code <br>• Injection protection <br>• Semgrep model rules <br>• STRIDE model‑level threats |
| **4. Zero Trust** 🔑 <br>• Explicit scoping <br>• Authentication required <br>• Input sanitization | **4. Application & Runtime** 🔌 <br>• LLM firewalls <br>• Pre/post tool‑call hooks <br>• Runtime gateways <br>• Semgrep runtime safety |
| **5. Defense in Depth** 👁️‍🗨️ <br>• Discovery → Classification → Vault → Logging <br>• Heuristics + LLM co‑verification <br>• Fallback regex rules | **5. IAM Management** 💎 <br>• Unique agent identity <br>• HITL approval required <br>• IAM‑safe file handling <br>• STRIDE IAM threats |
| **6. Operational Security** 📝 <br>• Structured logs <br>• Sensitive redaction <br>• Rollback records <br>• Graceful degradation | **6. Observability & Security Ops** 🧠 <br>• Logs, traces, metrics <br>• Drift detection <br>• Infinite loop detection <br>• Semgrep leakage protection |
| **7. Privacy by Design** ⚡ <br>• Filename masking <br>• No PII in logs <br>• Metadata‑only operations <br>• Safe‑mode execution | **7. Governance** 👤 <br>• AI‑risk compliance <br>• STRIDE v2.0 (404+ lines) <br>• Semgrep safety contract <br>• Residual risk documentation |

#### **Note:** Every principle and layer is implemented, tested, and documented.

---
## 🚀 Getting Started

### 👉 Prerequisites
- **Python 3.11+** and **uv** (recommended)
- **Google AI Studio Gemini API Key**

### 📐 Setup Instructions

 #### 1. Clone the Repository
```bash
git clone https://github.com/divya-gh/CleanSlate-AI-PC-Assistant.git
cd CleanSlate-AI-PC-Assistant
```
 #### 2. Set up the Python Virtual Environment & Install Dependencies
* **Using `uv` (Recommended)**:
```bash
  # This will automatically create the virtual environment and install all dependencies
  uv sync
  ```
* **OR using standard `pip`**:
  ```bash
  python -m venv .venv
  
  # source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
  pip install -r requirements.txt
  ```
#### 3. Configure Environment Variables
```bash
Create a `.env` file and add your Gemini API Key:
echo "GEMINI_API_KEY=your_api_key_here" > .env
```
#### 4. Run the **ADK Backend Server**
```bash
python run.py
Open the project folder ➔ run the agent ➔ test nodes ➔ inspect logs.
```
#### 5. Launching the **UIs**
```bash
CleanSlate AI supports two interfaces. Open a new terminal to start your preferred UI:

ADK Dev UI (Built-in):
  Access via `http://127.0.0.1:8080/dev-ui/` automatically when running `run.py`.

Custom Web UI:
  Run the custom chat interface:
  python launcher_server.py

  Access via `http://localhost:8000`
```
#### 6. Run in **Playground**
```
Upload the agent ➔ test interrupts ➔ validate UI.
```
---
## 🟦 11. Demo Video Placeholder
(Insert your YouTube demo link here)

🟦 12. Demo Tables (Side‑by‑Side)
Kaggle Demo	GitHub Demo
Kaggle Notebook URL	GitHub Repo URL
Kaggle Writeup URL	README.md
Kaggle Video	GitHub Video

### 🖥️ User Interface Screenshots

| 💬 Welcome Chat Interface | 📋 Human-in-the-Loop Approval |
| :---: | :---: |
| ![Welcome Chat](Images/welcome_chat_ui.png) | ![HITL Approval Table](Images/hitl_approval_table.png) |


### 🟦 17. License
MIT License 
