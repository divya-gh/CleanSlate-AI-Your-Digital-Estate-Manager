# 🧹 CleanSlate AI – My PC Assistant

> **"Your AI Chief of Staff for Digital Organization and Storage Management."**

![CleanSlate AI](docs/assets/cleanslate-ai.png)

## 📖 Problem Statement: Why We Built It
Modern computers accumulate massive digital clutter: downloads folders with thousands of files, duplicate documents and photos, old screenshots, large forgotten videos, unorganized project folders, cloud storage limits, and sensitive files stored in unsafe locations.

This clutter wastes time, increases cognitive load, and creates privacy risks. The problem is universal. Everyone experiences it, and no existing tool solves it intelligently. 

**CleanSlate AI** is an autonomous, multi-agent system that intelligently manages digital clutter, protects sensitive files, organizes storage, and provides a conversational PC assistant—all with strict human-in-the-loop safety. It is not just a “cleanup tool.” It is a **Digital Estate Manager**.

---

## 🌟 The Vision & Technical Decisions (Competition Highlights)
This project was built to showcase the effective use of Agentic AI technologies to solve a universal user problem: digital clutter. Our design philosophy centers around building a highly capable autonomous agent that prioritizes **safety, transparency, and user value**.

* **The Project Story & Vision**: We wanted an AI Chief of Staff that acts as a proactive digital estate manager. Instead of just answering questions, the agent needed to take agency over background maintenance while respecting strict privacy boundaries.
* **Solution Design**: We built a highly modular, multi-agent graph architecture. We separated concerns into discrete ADK nodes (File Discovery, Classification, Sensitive Detection, Optimization Planner) to ensure reasoning is traceable and debuggable.
* **Effective Use of Agent Technologies**: 
  * **Ambient Agents**: Using Pub/Sub, the agent can trigger weekly background organization tasks completely autonomously without user prompting.
  * **MCP (Model Context Protocol)**: We built native filesystem manipulation tools via MCP, giving the LLM secure, sandboxed access to local files without executing arbitrary code.
  * **Spec-Driven Development**: Every line of code traces back to the Master Specification, ensuring robust implementation quality and architectural integrity.
* **Overall User Value**: By blending conversational UX with ambient background processing and strict Human-In-The-Loop (HITL) safeguards, we deliver a premium, zero-anxiety digital cleanup experience.

---

## ✨ What It Does (Features & Workflows)
CleanSlate AI acts autonomously but respects strict boundaries to ensure user safety and data privacy.

- **Mandatory Folder Scope Approval**: Asks for and strictly enforces allowed/blocked directories before taking any action.
- **Intelligent File Discovery**: Scans local storage (Desktop, Downloads, Documents) and collects file metadata securely.
- **AI-Powered Classification**: Uses LLM reasoning to categorize files (Resume, Tax document, Medical record, Source code, Media, etc.).
- **Duplicate & Sensitive Detection**: Identifies exact/near duplicates and detects sensitive information (SSNs, Banking docs, Passwords) to protect them from deletion.
- **Storage Optimization**: Suggests archiving, compressing, moving, or deleting safe items to recover storage space.
- **Human-In-The-Loop (HITL) Review**: Provides explanations, confidence scores, and reasoning before requesting user approval for any destructive actions.
- **Weekly Auto-Organize (Ambient Agent)**: A background Pub/Sub job that automatically organizes your PC weekly based on your preferences.
- **Conversational Assistant**: Ask natural language queries like *"Find the file 'ambient expense agent'"* or *"Organize my screenshots."*

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

## 🏗️ Architecture & Technologies Used

CleanSlate AI is built entirely via **Spec-Driven Development (SDD)**, meaning every feature traces directly back to a unified Master Specification.

### Core Technologies
- **ADK 2.0 (Agent Development Kit)**: The backbone of the agent graph workflow, managing complex state and multi-node decision-making.
- **Agent is Ambient**: Uses Pub/Sub mechanisms to trigger weekly background organization tasks completely autonomously.
- **MCP (Model Context Protocol)**: Exposes tools like filesystem scanners and file movers natively to the agent.
- **Agent CLI**: For rapid scaffolding, building, evaluating, and deploying the agent.
- **ADK SKILLS**: Leveraged for building specialized capabilities into the AI workflows.
- **Semgrep Security Hooks**: Enforces SDD safety rules (like preventing LLM file content uploads) statically during the CI/CD and commit pipeline.
- **Antigravity**: Used for deep integration, observability, and complex agent interactions.
- **Logging & Traceability**: Comprehensive telemetry ensuring every action is recorded for auditability and rollback capabilities.

---

## 🔒 Security Architecture (The 7 Principles & STRIDE)

CleanSlate AI was designed using the **STRIDE Threat Model** (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege) to harden the agent against prompt injections, unauthorized filesystem access, and data exfiltration.

It adheres strictly to the **7 Principles of Agent Security**:

1. **Least Privilege**: The agent only reads and writes to explicitly approved folders (Folder Scope Policy). System folders are completely blocked.
2. **Human-In-The-Loop (HITL)**: No destructive action (like file deletion) occurs without explicit user review and approval.
3. **Data Minimization**: File contents are never uploaded to the cloud without permission; the agent operates entirely on local metadata and file names for classification.
4. **Secure Defaults**: Runs in "Dry-Run" mode by default. Sensitive files are moved to a secure, PIN-protected `Authenticated_Secure` folder.
5. **Fail-Safe & Rollback**: Every file operation is logged, enabling full reversibility. If an error occurs, the system fails gracefully without destroying data.
6. **Auditability**: Complete logging and traceability of all LLM reasoning, user approvals, and disk modifications.
7. **Defense in Depth**: Employs multiple layers of security, including regex-based fallback heuristics for safety checks when the LLM is unavailable.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js (for custom Web UI)
- Gemini API Key

### Clone and Run
```bash
# 1. Clone the repository
git clone https://github.com/your-org/cleanslate-ai-my-pc-assistant.git
cd cleanslate-ai-my-pc-assistant

# 2. Set up the Python Virtual Environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Configure Environment Variables
# Create a .env file and add your Gemini API Key
echo "GEMINI_API_KEY=your_api_key_here" > .env

# 5. Run the ADK Backend Server
python run.py
```

### Launching the UIs
CleanSlate AI supports two interfaces. Open a new terminal to start your preferred UI:

**ADK Dev UI (Built-in)**:
Access via `http://127.0.0.1:8080/dev-ui/` automatically when running `run.py`.

**Custom Web UI**:
```bash
# Run the custom chat interface
python launcher_server.py
# Access via http://localhost:8000
```

---

## 🎥 Demos

| Custom Web UI | ADK Dev UI |
| :---: | :---: |
| <video width="100%" controls><source src="docs/assets/custom-ui-demo.mp4" type="video/mp4"></video><br>_Showcasing the premium Chat Interface_ | <video width="100%" controls><source src="docs/assets/adk-dev-ui-demo.mp4" type="video/mp4"></video><br>_Showcasing the Developer ADK Dashboard_ |
