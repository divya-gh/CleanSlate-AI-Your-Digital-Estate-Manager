📘 CleanSlate‑AI — My PC Assistant
An ADK 2.0 Ambient Agent with Safe Automation, HITL, Rollback, and Weekly Organization
Built with Antigravity, TDD, STRIDE Threat Modeling, and Semgrep Static Safety Rules
🧭 Overview
CleanSlate‑AI is a secure, autonomous PC‑cleanup and file‑organization agent built using Google’s ADK 2.0, Antigravity, and Test‑Driven Development.
It performs:

Intelligent file cleanup

Duplicate detection

Sensitive file protection

Weekly automated organization

Rollback‑safe execution

Search‑only scanning

Human‑in‑the‑loop (HITL) approvals

Strict folder‑scope enforcement

This agent is designed to be safe by default, explainable, and fully reversible, making it suitable for real‑world personal and enterprise environments.

┌──────────────────────────────────────────────────────────────────────────────┐
│                           CleanSlate‑AI Architecture                         │
│                     (ADK 2.0 Ambient Agent — Unified Graph)                  │
└──────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────┐
│        User / Intent          │
│  (Natural Language Request)   │
└───────────────┬──────────────┘
                │
                ▼
┌───────────────────────────────┐
│     MyPCAssistantNode         │
│  • Intent classification       │
│  • Routes: cleanup/search/     │
│    weekly_organizer/unclear   │
└───────────────┬──────────────┘
                │
   ┌────────────┼───────────────┬──────────────────────────────┐
   │            │               │                              │
   ▼            ▼               ▼                              ▼
Cleanup      Search        Weekly Organizer             Error Recovery
Workflow     Workflow      Workflow                     (unclear_intent)

───────────────────────────────────────────────────────────────────────────────
CLEANUP WORKFLOW (HITL + Rollback)
───────────────────────────────────────────────────────────────────────────────

┌───────────────────────────────┐
│       FolderScopeNode         │
│  • HITL approval required     │
│  • Enforces folder scope      │
└───────────────┬──────────────┘
                │ "scope_ok"
                ▼
┌───────────────────────────────┐
│      FileDiscoveryNode        │
│  • Scans allowed paths        │
│  • Emits cleanup_scan         │
└───────────────┬──────────────┘
                │ "cleanup_scan"
                ▼
┌───────────────────────────────┐
│     ClassificationNode        │
│  • File type classification   │
│  • Emits dedupe               │
└───────────────┬──────────────┘
                │ "dedupe"
                ▼
┌───────────────────────────────┐
│   DuplicateDetectionNode      │
│  • Exact + near duplicates    │
│  • Emits sensitive            │
└───────────────┬──────────────┘
                │ "sensitive"
                ▼
┌───────────────────────────────┐
│   SensitiveDetectionNode      │
│  • PII / confidential files   │
│  • Emits plan                 │
└───────────────┬──────────────┘
                │ "plan"
                ▼
┌───────────────────────────────┐
│  OptimizationPlannerNode      │
│  • Dry‑run planning           │
│  • Rollback metadata          │
│  • Emits: default / no_actions│
└───────────────┬──────────────┘
                │ default
                ▼
┌───────────────────────────────┐
│      HITLApprovalNode         │
│  • User approves plan         │
│  • Routes: approved/rejected  │
└───────────────┬──────────────┘
        "approved"│     │"rejected"
                  ▼     ▼
       ┌───────────────────────────────┐
       │        ExecutionNode          │
       │  • Real file operations       │
       │  • Safe‑mode enforcement      │
       │  • Emits: default/rollback    │
       └───────────────┬──────────────┘
                       │
         ┌─────────────┼──────────────┐
         │ default      │ "rollback"   │
         ▼              ▼              │
┌────────────────┐   ┌──────────────────────────┐
│ SummaryNode    │   │      RollbackNode        │
│ Final report   │   │ Undo operations safely   │
└────────────────┘   └───────────────┬──────────┘
                                      │ default
                                      ▼
                              ┌────────────────┐
                              │  SummaryNode   │
                              └────────────────┘

───────────────────────────────────────────────────────────────────────────────
SEARCH WORKFLOW (Non‑Destructive)
───────────────────────────────────────────────────────────────────────────────

MyPCAssistantNode → "search" → FileDiscoveryNode → "search_return" → MyPCAssistantNode

───────────────────────────────────────────────────────────────────────────────
WEEKLY ORGANIZER WORKFLOW (Safe Mode Automation)
───────────────────────────────────────────────────────────────────────────────

MyPCAssistantNode
   → "weekly_organizer"
WeeklyOrganizerNode
   → "run"
FileDiscoveryNode
   → "weekly_scan"
ClassificationNode
   → DuplicateDetectionNode
   → SensitiveDetectionNode
   → OptimizationPlannerNode ("execute")
ExecutionNode (safe_mode=True)
   → SummaryNode

WeeklyOrganizerNode → "disabled" → SummaryNode  
WeeklyOrganizerNode → "error" → SummaryNode

───────────────────────────────────────────────────────────────────────────────
SAFETY LAYERS
───────────────────────────────────────────────────────────────────────────────

• Folder Scope Policy  
• HITL Approval  
• Safe Mode  
• Rollback  
• Sensitive File Protection  
• Semgrep Static Rules  
• STRIDE Threat Modeling  
• Error‑safe routing  




🏗️ Architecture Summary
CleanSlate‑AI is built around a unified ADK workflow graph containing 12 nodes, each responsible for a specific stage of the cleanup lifecycle:

MyPCAssistantNode

FolderScopeNode

FileDiscoveryNode

ClassificationNode

DuplicateDetectionNode

SensitiveDetectionNode

OptimizationPlannerNode

HITLApprovalNode

ExecutionNode

RollbackNode

SummaryNode

WeeklyOrganizerNode

The graph supports three workflows:

Cleanup Workflow (HITL + rollback)

Search Workflow (short loop, non‑destructive)

Weekly Organizer Workflow (safe‑mode automation)

All workflows share the same unified graph, ensuring consistency, safety, and maintainability.

🔁 Unified ADK Graph Wiring (ADK 2.0 Spec)
Cleanup Workflow
Code
MyPCAssistantNode
  → "cleanup"
FolderScopeNode
  → "scope_ok"
FileDiscoveryNode
  → "cleanup_scan"
ClassificationNode
  → "dedupe"
DuplicateDetectionNode
  → "sensitive"
SensitiveDetectionNode
  → "plan"
OptimizationPlannerNode
  → default
HITLApprovalNode
  → "approved"
ExecutionNode
  → default → SummaryNode
  → "rollback" → RollbackNode → SummaryNode
Search Workflow (Short Loop)
Code
MyPCAssistantNode
  → "search"
FileDiscoveryNode
  → "search_return"
MyPCAssistantNode
Weekly Organizer Workflow (Safe Mode)
Code
MyPCAssistantNode
  → "weekly_organizer"
WeeklyOrganizerNode
  → "run"
FileDiscoveryNode
  → "weekly_scan"
ClassificationNode
  → ...
OptimizationPlannerNode
  → "execute"
ExecutionNode
  → SummaryNode
WeeklyOrganizerNode
  → "disabled" → SummaryNode
  → "error" → SummaryNode
Error Handling
"unclear_intent" → MyPCAssistantNode

"scope_invalid" → FolderScopeNode

"error" (discovery) → MyPCAssistantNode

"no_actions" → SummaryNode

"error" (weekly) → SummaryNode

All error paths are safe, reversible, and non‑destructive.

🔐 Safety Model (SDD Safety Rules)
CleanSlate‑AI enforces a multi‑layered safety system:

🚫 Forbidden
Never delete without explicit HITL approval

Never delete sensitive files

Never touch system folders

Never scan or modify unapproved folders

Never touch blocked folders

Never upload file contents without permission

Never bypass FolderScopeNode

Never bypass HITLApprovalNode

Never bypass safe_mode in weekly automation

✔ Required
Always run dry‑run planning before execution

Always provide reasoning for every action

Always log actions

Always support rollback

Always protect sensitive files

Always move sensitive files to Authenticated folder

Always enforce folder scope policy

Always allow user to update folder scope

Always sanitize paths in logs and summaries

This safety model is enforced at:

Static level (Semgrep rules)

Runtime level (ADK nodes)

Human level (HITL)

Recovery level (RollbackNode)

🛡️ STRIDE Threat Modeling Skill
CleanSlate‑AI includes a custom STRIDE Threat Modeling Skill that:

Scans the entire codebase

Maps system boundaries

Analyzes workflows

Identifies threats across all STRIDE categories

Generates a threat_model.md file

Recommends mitigations

Ensures continuous security review

This aligns the project with Google’s Secure Agentic Coding standards.

🧪 Testing & QA
The project uses full TDD with:

Unit tests

Workflow tests

Safety tests

Rollback tests

Weekly automation tests

Error‑handling tests

Latest test run:

Code
65 passed, 17 warnings in 23.16s
This confirms:

Graph wiring correctness

Routing key correctness

Safe‑mode enforcement

HITL enforcement

Rollback correctness

Sensitive file protection

Weekly automation safety

🧰 Semgrep Static Safety Rules
A custom .semgrep/sdd-safety-rules.yaml enforces:

No hardcoded API keys

No direct file deletes

No unsafe path operations

No system folder access

No file content uploads

No bypassing folder scope

No bypassing HITL

No unsafe actions in safe_mode

Rollback metadata required for destructive actions

This ensures static safety before runtime safety even begins.

🧩 Future Extensions
CleanSlate‑AI is designed to grow:

MCP Tools (filesystem, cloud storage, metadata extraction)

Observability (structured logs, metrics, dashboards)

Multi‑agent collaboration

Cloud deployment

User profiles & personalization

Advanced duplicate detection (ML‑based)

The README will evolve as these features are added.

🚀 Getting Started
Clone the repository

Install dependencies

Configure environment variables

Run tests

Launch the agent

The agent will guide you through folder scope approval and cleanup workflows.

🏁 Conclusion
CleanSlate‑AI is a secure, explainable, reversible, and production‑ready ADK 2.0 agent built with:

Antigravity

TDD

STRIDE

Semgrep

HITL

Rollback

Safe‑mode automation

This README serves as the living architecture document for the project and will grow as new capabilities are added.