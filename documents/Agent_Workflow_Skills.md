# 🛠️ Agent & Workflow Skills Used in CleanSlate AI

CleanSlate AI was rapidly developed and deployed by utilizing specialized AI Agent Workflow Skills (via the Antigravity workspace) tailored for the **Google Agent Development Kit (ADK 2.0)**. 

These workflow skills empowered the iterative "Vibe Coding" process, allowing us to scaffold, build, observe, and document the multi-node `ENGINE_DAG` seamlessly.

---

### 🏗️ 1. Project Scaffolding (`google-agents-cli-scaffold`)
- **Purpose**: Used to initialize the entire ADK 2.0 agent project from scratch.
- **Application**: Scaffolded the `app/` directory structure, generated the `agent.py` baseline, and configured the prototype-first workflow environments so we could begin development instantly.

### 🧠 2. Core Node Development (`google-agents-cli-adk-code`)
- **Purpose**: The primary coding skill used to design the ADK workflow graph.
- **Application**: Leveraged heavily to implement the complex intent routing (`MyPCAssistantNode`), set up the `ResumabilityConfig` for Human-in-the-Loop interrupts (`HITLApprovalNode`), and pass strict context state dynamically between 10 unique execution nodes.

### 🔄 3. Development Lifecycle (`google-agents-cli-workflow`)
- **Purpose**: Governed the continuous integration and development loop.
- **Application**: Guided the end-to-end development journey—from running the agent locally and debugging state payloads to enforcing strict ADK 2.0 best practices throughout the agent's evolution.

### 📊 4. Logging & Tracing (`google-agents-cli-observability`)
- **Purpose**: Established deep visibility into the agent's autonomous actions.
- **Application**: Assisted in building the `write_log` MCP tool and instrumenting the DAG nodes. Ensuring every file classification, duplication check, and metadata read is transparent and fully auditable by the user.

### 🚀 5. Deployment Architecture (`google-agents-cli-deploy`)
- **Purpose**: Secured the application for isolated execution.
- **Application**: Provided critical architectural guidance on how to safely containerize and deploy this agent so it runs perfectly within a Linux Sandbox environment (such as Kaggle) without pathing errors.

### ⚙️ 6. Workflow Extraction (`workflow-skill-creator`)
- **Purpose**: Reusable action distillation.
- **Application**: Whenever a repetitive documentation or coding task was completed during the project, this skill allowed us to package that workflow into a repeatable pattern to save time during rapid prototyping.

### 🛡️ 7. Threat Modeling (`stride-threat-model`)
- **Purpose**: Systematic security evaluation.
- **Application**: Used to assess the agent's security boundaries, mapping data flows to identify and mitigate Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege across all local filesystem operations.

### 🐙 8. Automated VCS (`git-mini`)
- **Purpose**: Secure source control management.
- **Application**: A highly disciplined, automated git commit-and-push workflow that prevents accidental commits of secrets/PII (like `.env` or key files), strictly limits commit message lengths (concise and meaningful), and handles automatic upstream rebasing during the Vibe Coding flow.

---

## 💻 Local Agentic Capabilities (Domain Skills)
Beyond the overarching workflow skills, the CleanSlate AI agent executes localized "Custom Skills" across its internal node graph:
* **🔍 File Scanning**: High-speed, metadata-only recursive filesystem traversal.
* **🕵️ Sensitive Classification**: LLM-driven and heuristic detection of PII (SSNs, API Keys, Passwords).
* **👯 Duplicate Detection**: Exact hash (`SHA-256`) and near-duplicate semantic grouping.
* **⏪ Archive & Rollback**: Safe compression capabilities coupled with verifiable inverse-action JSON payloads for undo operations.
* **📊 Logging & Table Rendering**: Beautifully formatted console and UI dashboards to summarize execution paths and HITL recovery stats.
