# Implementation Plan — Graph Wiring in agent.py (ADK 2.0 Spec)

This plan covers updating the ADK workflow graph inside `app/agent.py` to route all primary, search, weekly organizer, and error handling paths correctly.

## User Review Required

> [!IMPORTANT]
> **Dynamic Routing & State Delta Exclusions**:
> - Re-wire the 12 nodes (MyPCAssistantNode, FolderScopeNode, FileDiscoveryNode, ClassificationNode, DuplicateDetectionNode, SensitiveDetectionNode, OptimizationPlannerNode, HITLApprovalNode, ExecutionNode, RollbackNode, SummaryNode, WeeklyOrganizerNode) into a single, unified `workflow` object starting with `my_pc_assistant_node`.
> - Maintain compatibility by assigning `root_agent = workflow` and wrapping it in `app = App(root_agent=workflow, ...)`.

## Proposed Changes

### Graph Wiring Component

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
Update workflow edges to implement:
1. **Cleanup Workflow**:
   `my_pc_assistant_node` → `"cleanup"` → `folder_scope_node` → `"scope_ok"` → `file_discovery_node` → `"cleanup_scan"` → `classification_node` → `"dedupe"` → `duplicate_detection_node` → `"sensitive"` → `sensitive_detection_node` → `"plan"` → `optimization_planner_node` → (default) → `hitl_approval_node` → `"approved"` → `execution_node` → (default) → `summary_node`.
   `execution_node` → `"rollback"` → `rollback_node` → (default) → `summary_node`.
   `hitl_approval_node` → `"rejected"` → `summary_node`.
2. **Search Workflow (Short Loop)**:
   `my_pc_assistant_node` → `"search"` → `file_discovery_node` → `"search_return"` → `my_pc_assistant_node`.
3. **Weekly Organizer Workflow**:
   `my_pc_assistant_node` → `"weekly_organizer"` → `weekly_organizer_node` → `"run"` → `file_discovery_node` → `"weekly_scan"` → `classification_node` → ... → `optimization_planner_node` → `"execute"` → `execution_node` → `summary_node`.
   `weekly_organizer_node` → `"disabled"` → `summary_node`.
   `weekly_organizer_node` → `"error"` → `summary_node`.
4. **Error Handling Paths**:
   - `my_pc_assistant_node` → `"unclear_intent"` → `my_pc_assistant_node`.
   - `folder_scope_node` → `"scope_invalid"` → `folder_scope_node`.
   - `file_discovery_node` → `"error"` → `my_pc_assistant_node`.
   - `optimization_planner_node` → `"no_actions"` → `summary_node`.

---

## Verification Plan

### Automated Tests
- Run all project tests to verify the unified workflow graph runs correctly.
