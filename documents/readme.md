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
•	Prevent insecure 
•	Enforce ADK node safety patterns
•	Safe CI/CD and commit pipeline.

#### ✔ STRIDE Threat Model(Threat	Mitigation)
•	S – Spoofing	PIN + security question
•	T – Tampering	Rollback + secure folder
•	R – Repudiation	Full action logs
•	I – Information Disclosure	Sensitive file masking
•	D – Denial of Service	Bounded folder scanning
•	E – Elevation of Privilege	No privileged operations
•	Enforces SDD safety rule to reason about threats at design time.

#### ✔ SKILLS.md
File scanning
•	Sensitive classification
•	Duplicate detection
•	Archive skill
•	Rollback skill
•	Logging skill
•	Table rendering skill

---

## 🛡️ Security Architecture
#### CleanSlate AI adheres strictly to the 7-Pillars of Security & 7-Layers of AI Agent Security Architecture:

<table border="5" width="100%" cellpadding="10" cellspacing="0" style="width:100%; border-collapse:separate; border-style:double; border-width:6px; border-color:#FFFFFF; font-family:sans-serif;">
  <thead>
    <tr>
      <th width="50%" align="left" style="padding:14px; background-color:#0B132B; color:#6A5ACD; font-family:Consolas, Monaco, 'Courier New', monospace; font-size:20px; font-weight:bold; letter-spacing:0.5px; border-bottom:3px double #FFFFFF; border-right:1px solid #FFFFFF;">.
🔒 07 SECURITY PILLARS<br>--Design Philosophy</th>
      <th width="50%" align="left" style="padding:14px; background-color:#0B132B; color:#6A5ACD; font-family:Consolas, Monaco, 'Courier New', monospace; font-size:20px; font-weight:bold; letter-spacing:0.5px; border-bottom:3px double #FFFFFF;">🧩 07 SECURITY LAYERS<br>--Operational Controls</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF; border-right:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">1. SECURE_BY_DESIGN🔒</span><br>
        <span style="font-size: 11px; color: #8a99ad; padding-left: 20px; display: inline-block;"><i>  • Sensitive File Isolation</i></span><br>
        <span style="font-size: 11px; color: #8a99ad; padding-left: 20px; display: inline-block;"><i>  • Authenticated Secure Vault</i></span><br>
        <span style="font-size: 11px; color: #8a99ad; padding-left: 20px; display: inline-block;"><i>  • Access Recovery-PIN + security question</i></span><br>
        <span style="padding-left: 20px; display: inline-block;"><i>• Runtime Safety Gates</i></span>
      </td>
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">1. INFRASTRUCTURE_&_NETWORKING🌐</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Sandboxed execution</span><br>
        <span style="padding-left: 20px; display: inline-block;">• FS access only through MCP tools</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Network isolation</span><br>
        <span style="padding-left: 20px; display: inline-block;">• No uncontrolled paths</span><br>
      </td>
    </tr>
    <tr style="background-color:rgba(255,255,255,0.03);">
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF; border-right:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">2. SECURE_BY_DEFAULT⚙️</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Sensitive files never deleted or moved to vault</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Implicit dry-run: Safety-first execution</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Rollback enabled for all destructive actions</span>
      </td>
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">2. DATA_LAYER📊</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Least‑privilege access: No content Preview</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Logs/Summary redact sensitive path</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Partitions storage to avoid cross‑tenant exposure</span>
      </td>
    </tr>
    <tr>
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF; border-right:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">3. SECURE_IN_DEPLOYMENT🚀</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Runs safely in sandboxed environments</span><br>
        <span style="padding-left: 20px; display: inline-block;">• No Exfiltration: Zero external network</span><br>
         <span style="padding-left: 20px; display: inline-block;">•Safety enforcement in logging</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Traversal Defense: Absolute path enforcement</span>
      </td>
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">3. MODEL_SECURITY💻</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Treats prompts and rule files as source code</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Protects against tampering and injection.</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Semgrep rules prevent unsafe LLM usage</span><br>
        <span style="padding-left: 20px; display: inline-block;">• STRIDE v2.0 documents model-level threats</span>
      </td>
    </tr>
    <tr style="background-color:rgba(255,255,255,0.03);">
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF; border-right:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">4. ZERO_TRUST🔑</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Explicit Scoping: Blocked path are invisible to agent</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Sensitive operation require authentication</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Input Sanitization: No implicit trust of user input</span>
      </td>
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">4. APPLICATION_&_RUNTIME🔌</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Uses LLM firewalls and pre/post tool‑call hooks</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Gateways prevent unrestricted agent calls.</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Semgrep rules enforce runtime safety</span><br>
       </td>
    </tr>
    <tr>
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF; border-right:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">5. DEFENSE_IN_DEPTH👁️‍🗨️</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Layered Pipeline: Discovery ➔</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Local Pattern Matching➔ LLM Classification</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Vault Encryption ➔ Transaction Logging</span><br>        
        <span style="padding-left: 20px; display: inline-block;">• Heuristics & LLM Co-Verification:Fallback regex rules</span>
      </td>
      </td>
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">5. IAM_MANAGEMENT💎</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Unique agent identity</span><br>
        <span style="padding-left: 20px; display: inline-block;">• HITLApproval required for delete</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Secure file handling with IAM rules</span><br>        
        <span style="padding-left: 20px; display: inline-block;">• STRIDE v2.0 documents IAM threats</span>
      </td>
    </tr>
    <tr style="background-color:rgba(255,255,255,0.03);">
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF; border-right:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">6. OPERATIONAL_SECURITY📝</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Full traceability through structured logs</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Telemetry Protection:Erases sensitive file details in summary and logs</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Rollback records, and audit trails</span><br>        
        <span style="padding-left: 20px; display: inline-block;">• Graceful Degradation: Recovers safely timeout failures</span>
      </td>
      <td valign="top" style="padding:12px; border-bottom:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">6. OBSERVABILITY_&_SECURITY_OPS🧠</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Continuous monitoring via logs, traces, and metrics</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Detects drift or infinite loops</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Semgrep ensures no sensitive leakage</span><br>        
        <span style="padding-left: 20px; display: inline-block;">• STRIDE v2.0 includes observability threats</span>
      </td>
    </tr>
    <tr>
      <td valign="top" style="padding:12px; border-right:1px solid #FFFFFF;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">7. PRIVACY_BY_DESIGN⚡</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Redacts and masks sensitive filenames</span><br>
        <span style="padding-left: 20px; display: inline-block;">• No PII exposed in logs or summaries.</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Restricts the LLM from reading file content</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Works exclusively with metadata</span><br>        
        <span style="padding-left: 20px; display: inline-block;">• Safe-mode operations throught the graph</span>
      </td>
      <td valign="top" style="padding:12px;">
        <span style="font-family:Consolas, Monaco, 'Courier New', monospace; font-size:14px; font-weight:bold; color:#FFFFFF;">7. GOVERNANCE👤</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Ensures compliance with AI‑risk frameworks</span><br>
        <span style="padding-left: 20px; display: inline-block;">• STRIDE v2.0 (404+ lines)</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Semgrep safety contract (26+ rules)</span><br>
        <span style="padding-left: 20px; display: inline-block;">• Residual risks documented</span><br>        
        <span style="padding-left: 20px; display: inline-block;">• SStrict enforcemnt of SPEC governance in nodes</span>
      </td>
    </tr>
  </tbody>
</table>

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


</div>
MIT License 
