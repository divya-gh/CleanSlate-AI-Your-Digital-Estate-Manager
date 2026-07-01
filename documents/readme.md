# 🖼️ CleanSlate AI — Your PC Assistant
(Insert your cover image here — e.g., /assets/cleanslate-banner.png)

# 🟦 1. Executive Summary
Problem Statement
Modern PCs accumulate thousands of files — documents, images, downloads, duplicates, sensitive identity files, and forgotten artifacts.
This digital clutter creates:

Security risks

Productivity loss

Storage inefficiency

Difficulty finding important files

Accidental exposure of sensitive documents

Users need a safe, intelligent, automated assistant that can:

Organize folders

Detect sensitive files

Remove duplicates

Archive old content

Protect identity documents

Provide rollback

Maintain traceability

Operate safely in sandboxed environments

Why We Built It
CleanSlate AI was built to demonstrate modern agent engineering using:

ADK Agent 2.0

MCP Server

Agent CLI

Pub/Sub Ambient Agent architecture

Spec‑Driven Development (SDD)

Security 7 Principles

Semgrep static analysis

STRIDE threat modeling

Antigravity development environment

This project showcases the ability to design, build, secure, and communicate a production‑grade AI agent system.

What CleanSlate AI Does
CleanSlate AI is a multi‑step, interrupt‑driven PC assistant that:

Scans user‑selected folders

Detects sensitive files (DL, SSN, passports, resumes, financial docs)

Creates an Authenticated Secure Folder

Moves sensitive files safely

Removes duplicates

Archives old content

Organizes files into structured categories

Provides rollback for all destructive actions

Generates professional cleanup summaries

Logs every action for traceability

Runs safely in sandbox environments (Kaggle, cloud VMs)

🟦 2. System Architecture Overview
CleanSlate AI is built using ADK Agent 2.0, following Microsoft’s enterprise agent architecture patterns.

High‑Level Architecture Diagram (ASCII)
Code
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
🟦 3. ADK Agent 2.0 Features Used
CleanSlate AI demonstrates:

✔ Multi‑step agent workflows
✔ Interrupt‑driven UI
✔ Ambient agent architecture
✔ Pub/Sub messaging
✔ Node‑based execution graph
✔ Table, toggle, and checkbox widgets
✔ Secure state management
✔ Rollback support
✔ Logging & traceability
✔ Antigravity development environment
✔ Agent CLI for local testing
✔ MCP server for tool orchestration
🟦 4. Security Architecture
CleanSlate AI is built using Microsoft’s Security 7 Principles.

1. Secure by Design
Sensitive file detection

Authenticated Secure Folder

PIN + security question

Runtime safety checks

2. Secure by Default
Sensitive files never deleted

Sensitive files never moved to unsafe folders

Rollback enabled for all destructive actions

3. Secure in Deployment
Sandbox‑safe file operations

No external network calls

No unsafe path traversal

4. Zero Trust
Every file is validated

Sensitive files require authentication

No implicit trust of user input

5. Defense in Depth
Multiple layers: detection → classification → secure storage → logging

6. Operational Security
Full traceability

Action logs

Rollback logs

Error logs

7. Privacy by Design
Sensitive filenames masked

Sensitive details hidden in summaries

No PII exposed in logs

🟦 5. Semgrep Rules
CleanSlate AI uses Semgrep for static analysis:

✔ Detect unsafe file operations
✔ Prevent path traversal
✔ Prevent insecure regex patterns
✔ Prevent insecure logging
✔ Prevent accidental PII exposure
✔ Enforce ADK node safety patterns
🟦 6. STRIDE Threat Model
Threat	Mitigation
S – Spoofing	PIN + security question
T – Tampering	Rollback + secure folder
R – Repudiation	Full action logs
I – Information Disclosure	Sensitive file masking
D – Denial of Service	Bounded folder scanning
E – Elevation of Privilege	No privileged operations


🟦 7. Agent SKILLS.md
CleanSlate AI uses:

File scanning skill

Sensitive file classification skill

Duplicate detection skill

Archive skill

Rollback skill

Logging skill

Table rendering skill

Toggle/checkbox UI skill

🟦 8. Workflows
✔ Folder selection
✔ Sensitive file detection
✔ Optimization planning
✔ Cleanup execution
✔ Rollback
✔ Summary dashboard
🟦 9. Outputs
CleanSlate AI produces:

Professional cleanup summary

Color‑coded action logs

Sensitive file protection report

Storage recovery report

Rollback capability report

🟦 10. Setup Instructions
Clone the Repository
Code
git clone https://github.com/<your-username>/CleanSlate-AI-PC-Assistant.git
cd CleanSlate-AI-PC-Assistant
Install Dependencies
Code
pip install -r requirements.txt
Run the Agent (Agent CLI)
Code
agent run cleanslate_agent
Run in Antigravity
Open the project folder → run the agent → test nodes → inspect logs.

Run in Playground
Upload the agent → test interrupts → validate UI.

🟦 11. Demo Video Placeholder
(Insert your YouTube demo link here)

🟦 12. Demo Tables (Side‑by‑Side)
Kaggle Demo	GitHub Demo
Kaggle Notebook URL	GitHub Repo URL
Kaggle Writeup URL	README.md
Kaggle Video	GitHub Video


🟦 13. Logging & Traceability
CleanSlate AI logs:

Every action

Every failure

Every rollback

Every sensitive file detection

Every optimization decision

Every node transition

🟦 14. Built with Spec‑Driven Development (SDD)
CleanSlate AI follows:

Requirements → Spec → Architecture → Nodes → UI → Testing → Docs

Full traceability from spec to implementation

🟦 15. Ambient Agent (Pub/Sub)
CleanSlate AI uses:

Pub/Sub channels for node communication

Ambient state propagation

Interrupt‑driven UI updates

🟦 16. Antigravity
Developed entirely in Antigravity, using:

Node graph editor

Agent manifest

Interrupt testing

Logging console

Spec‑Driven Development workflow

🟦 17. License
MIT License (or your choice)