[![Google Cloud Agent Runtime](https://img.shields.io/badge/Google%20Cloud-Agent%20Runtime-blue.svg)](https://cloud.google.com/vertex-ai)
[![ADK 2.0](https://img.shields.io/badge/ADK-2.0-green.svg)](https://adk.dev)
[![Python 3.11](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Enabled-purple.svg)](https://modelcontextprotocol.io/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini_AI-orange.svg)](https://deepmind.google/technologies/gemini/)
[![Semgrep](https://img.shields.io/badge/Security-Semgrep-green.svg)](https://semgrep.dev/)
[![STRIDE](https://img.shields.io/badge/Security-STRIDE_Threat_Model-blue.svg)]()
[![Built with Antigravity](https://img.shields.io/badge/Built%20with-Antigravity-cyan.svg)]()

---
# 🧹 CleanSlate AI — Your Digital Estate Manager
> **"AI Chief of Staff for Digital Organization and Storage Management."**

---
#### A secure, intelligent, multi‑step ADK 2.0 agent that organizes your PC, protects sensitive files, and restores digital clarity.
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <img src="assets/cleanslate_corporate_banner.png" width="700" height= "500" alt="CleanSlate AI Corporate Banner">

---
## 🛎️ Track: `Concierge Agents`

---
## 📖 The Problem: Why CleanSlate AI?
Modern users passively accumulate thousands of files across their devices—outdated resumes, scattered tax documents, unorganized photos, bloated downloads, and forgotten project folders. Over time, this uncontrolled digital sprawl leads to:

- **Security & Privacy Risks**: Sensitive PII (identity documents, financial records) left exposed in unencrypted or shared folders.
- **Cognitive Load & Productivity Loss**: Navigating organizational chaos wastes time and makes finding critical files nearly impossible.
- **Storage Inefficiency**: Duplicates, large forgotten videos, and unused applications exhaust local and cloud storage limits.

While everyone experiences digital clutter, existing tools only offer surface-level solutions. They require too much manual intervention and lack the intelligence to contextually understand the files they are managing.

---
## 🌟 Vision & Technical Philosophy
CleanSlate AI was designed to demonstrate the transformative power of Agentic AI in solving universal, everyday user problems. Our core philosophy is simple: build a highly capable autonomous agent that prioritizes **safety**, **transparency**, and **user value**.

**The Project Story & Vision**: We set out to build an **AI Chief of Staff** that acts as a proactive digital estate manager. Rather than acting as a passive chatbot that only answers questions, CleanSlate AI takes agency over your digital environment—conducting ambient background maintenance while rigorously respecting strict privacy boundaries.

#### CleanSlate AI demonstrates state-of-the-art agentic design patterns:
- **Safe Automation & Rollback Guarantees**: 100% reversible actions with full traceability.
- **Context-Aware Organization**: Intelligent classification and deduplication of complex file hierarchies.
- **Enterprise-Grade Security**: Proactive detection and vaulting of sensitive data.
- **Interrupt-Driven Workflows**: Seamlessly blending autonomous background processing with strict Human-In-The-Loop (HITL) safeguards.

**Overall User Value:** By merging an intuitive conversational UX with ambient processing, CleanSlate AI delivers a premium, zero-anxiety digital cleanup experience.

---
## ✨ 2. What CleanSlate AI Does (Features)
CleanSlate AI acts autonomously but respects strict boundaries to ensure user safety and data privacy. It operates as a multi‑step, interrupt‑driven ambient PC assistant equipped with the following core features:

- **Mandatory Folder Scope Approval:** Explicitly requests and strictly enforces allowed/blocked directories before initiating any actions.
- **Intelligent File Discovery:** Scans local storage (e.g., Desktop, Downloads, Documents) to securely collect file metadata.
- **AI-Powered Classification:** Leverages advanced LLM reasoning to categorize files (Resumes, Tax documents, Source code, Media, etc.) with high accuracy.
- **Sensitive & Duplicate Detection:** Proactively identifies exact/near duplicates and detects highly sensitive information (SSNs, DLs, Banking docs, Passwords, API Keys) to shield them from accidental deletion.
- **Storage Optimization:** Intelligently suggests archiving, compressing, moving, or safely deleting duplicates and unused items to reclaim storage space.
- **Human-In-The-Loop (HITL) Review:** Provides transparent explanations, confidence scores, and clear AI reasoning before requesting user approval for any destructive actions.
- **Execution & Rollback:** Safely executes approved actions, moves sensitive files into an authenticated Secure Folder, organizes remaining files into structured categories, and provides full rollback capabilities for all destructive actions.
- **Traceability & Logging:** Produces a professional, color‑coded action log and cleanup summary. Centralized logging captures every proposed and executed action, failure, rollback, sensitive file detection, node transition, and pub/sub event.
- **Weekly Auto-Organize (Ambient Agent):** Operates as a background Pub/Sub job that automatically organizes your PC weekly based on your distinct preferences.
- **Conversational Assistant:** Allows users to execute natural language queries like *"Find the file 'ambient expense agent'"* or *"Organize my screenshots."*
- **Sandbox Environments:** Safely containerized to run seamlessly in sandbox environments like Kaggle notebooks and cloud VMs.
  
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
###  🛠️  4. Core Technologies & Tools Used

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
#### S — Spoofing  
`Risk:` Unauthorized triggers to organize files.  
`Mitigation:`  Local PIN authentication required for any secure‑vault modification.
#### T — Tampering  
`Risk:` Folder‑scope policy altered to access system directories.  
`Mitigation:` Policy is hashed and validated at runtime; changes require manual re‑authorization.
#### R — Repudiation  
`Risk:` User claims the agent deleted files without approval.  
`Mitigation:` Cryptographically signed audit logs record timestamps, actions, and HITL approval IDs.
#### I — Information Disclosure  
`Risk:` LLM accidentally exposes sensitive file contents.  
`Mitigation:` Nodes operate on metadata only; sensitive files are isolated in a local secure vault.
#### D — Denial of Service  
`Risk:` Infinite loops (e.g., symlinks) consuming CPU.  
`Mitigation:` Bounded scanning limits depth to 10 and caps file count at 5,000 per run.  
#### E — Elevation of Privilege  
`Risk:` Prompt injection bypassing HITL approval.  
`Mitigation:` ExecutionNode only processes actions validated by HITLApprovalNode, ensuring strict separation.

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
### 🎬 CleanSlate AI Demo Video  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <img width="20" height="20" alt="image" src="https://github.com/user-attachments/assets/7bcbfde5-c8f0-4751-abe5-7251846d00cf"/> Playground Chat UI (GIF Demo)

<div style="display: flex; gap: 25px; align-items: flex-start;">
  <a href="https://youtu.be/9HInUm5U1XY?si=n_XpTV8sgyXlEutV" target="_blank">
    <img src="https://img.youtube.com/vi/9HInUm5U1XY/maxresdefault.jpg" height="250" alt="Watch the CleanSlate AI Demo" />
  </a>
  <a href="assets/cleanSateAI_Demo.gif" target="_blank">
    <img src="assets/cleanSateAI_Demo.gif" height="250" alt="Playground Chat UI Demo" />
  </a>
</div>

---
### 🖥️ User Interface Screenshots

| 💬 Welcome Chat Interface | 📋 Human-in-the-Loop Approval | 📊 Summary Report |
| :---: | :---: | :---: |
| <img src="assets/welcome_chat_ui.png" height="400" alt="Welcome Chat"> | <img src="assets/hitl_approval_table.png" height="400" alt="HITL Approval Table"> | <img src="assets/summary.png" height="400" alt="Summary"> |

---
### 📂 Project Documentation & Specs
All detailed specifications, architecture diagrams, and implementation plans are documented in the [`documents/`](documents/) directory.
- 📄 [System Architecture & Master Specs](documents/SPECS/)
- 🔒 [Security & Threat Modeling](documents/Security/)
- 🛠️ [Model Context Protocol (MCP) Tools](documents/MCP_Tools/)
- 💻 [Agent CLI Implementation](documents/Agent_CLI/)
- 🧪 [Testing, Logging & Observability](documents/Testing_Logging_Observability/)
- 📋 [Implementation Plan & Walkthrough](documents/ImplimentationPlan_And_Walkthrough/)

---
### 🟦 17. License
Released under Attribution 4.0 International (CC BY 4.0).

---
### 📚 Acknowledgments & Citations
- **Project**: Kaggle AI Agents: Google Intensive Vibe Coding Capstone Project
- **Code Assistance**: Built with the help of Google's Advanced Agentic Coding assistant (Antigravity) and the ADK 2.0 framework.
- **Image Generation**: The graphical assets, diagrams, and banners in this project were conceptualized and generated using **Microsoft Copilot** and **Google Gemini**.
