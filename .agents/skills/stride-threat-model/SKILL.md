---
name: stride-threat-model
description: Performs a systematic STRIDE threat modeling assessment on the current project's codebase and architecture. Use this when starting a new implementation phase or reviewing existing components.
---

# STRIDE Threat Modeling Skill

## Goal
Analyze the Cleanslate PC Assistant ADK 2.0 agent graph, nodes, tools, and configuration files to produce a structured `threat_model.md` that identifies risks and mitigations across all STRIDE categories.

## Scope
- app/agent.py (graph wiring, routing keys, workflows)
- app/nodes/** (MyPCAssistantNode, FolderScopeNode, FileDiscoveryNode, ClassificationNode, DuplicateDetectionNode, SensitiveDetectionNode, OptimizationPlannerNode, HITLApprovalNode, ExecutionNode, RollbackNode, SummaryNode, WeeklyOrganizerNode)
- tools, configs, environment files
- safety rules and Semgrep configuration (if present)

## STRIDE Dimensions

For each major component (nodes, workflows, tools, configs), evaluate:

### Spoofing
- Can caller identity or intent be faked?
- Are there any paths where untrusted input can trigger privileged actions?
- Are HITL and folder scope checks enforced before destructive actions?

### Tampering
- Can users or external inputs modify:
  - folder_scope_policy
  - allowed_paths / blocked_paths
  - execution actions
  - rollback metadata
- Are file operations always routed through ExecutionNode with safety checks?
- Can users manipulate data flows, parameters, or underlying
     state?


### Repudiation
- Are critical actions (delete, move, archive, rollback) logged?
- Can a user plausibly deny having approved a plan or folder scope?
- Are summaries and logs sufficient to reconstruct what happened?

### Information Disclosure
- Can sensitive file names, paths, or contents leak via:
  - logs
  - summaries
  - error messages
  - external APIs (e.g., Gemini)?
- Are sensitive files always moved to the Authenticated folder and never uploaded?

### Denial of Service
- Can the agent be overloaded via:
  - huge folder scopes
  - repeated weekly automation
  - excessive MCP calls
- Are there guardrails on:
  - scan depth
  - file count
  - retry loops
  - error handling?

### Elevation of Privilege
- Can a user bypass:
  - FolderScopeNode HITL
  - HITLApprovalNode
  - safe_mode constraints
  - rollback protections?
- Are there any direct file operations outside ExecutionNode?

## Method

1. **Map System Boundaries**
   - Identify entry points (user prompts, weekly automation, search).
   - Identify privileged nodes (ExecutionNode, RollbackNode, HITLApprovalNode, FolderScopeNode).
   - Identify data stores (local filesystem, rollback backups, logs).

2. **Trace Workflows**
   - Cleanup workflow (intent → scope → discovery → classify → dedupe → sensitive → plan → HITL → execute → summary → rollback).
   - Search workflow (short loop).
   - Weekly organizer workflow (safe_mode automation).
   - Error handling paths.

3. **Apply STRIDE**
   - For each workflow and node, list potential threats under each STRIDE category.
   - For each threat, document:
     - Component
     - Threat description
     - STRIDE category
     - Likelihood (Low/Medium/High)
     - Impact (Low/Medium/High)
     - Existing mitigations
     - Recommended improvements

4. **Generate `threat_model.md`**
   - Save a Markdown file at the project root:
     - `cleanslate-pc-assistant/threat_model.md`
   - Include sections:
     - Overview
     - System Boundaries
     - Workflow Map
     - STRIDE Analysis (per category)
     - Mitigation Summary
     - Residual Risk
     - Future Improvements

5. **Style & Constraints**
   - Use concise, structured Markdown.
   - Do not include actual API keys, absolute paths, or sensitive filenames.
   - Refer to sensitive items generically (e.g., "Sensitive file in Documents").
   - Align findings with the project’s SDD safety rules and Semgrep policies.

When done, confirm that `cleanslate-pc-assistant/threat_model.md` has been created and is consistent with the ADK 2.0 agent graph and safety model.
