# Implementation Plan — MyPCAssistantNode

This plan outlines the creation and integration of `MyPCAssistantNode`, which acts as the main entry point and UI classification layer for all interactive user sessions.

## User Review Required

> [!IMPORTANT]
> **Safety Constraints**:
> - Never infer cleanup intent unless the user explicitly asks for cleanup.
> - Never reveal sensitive file paths or system paths.
> - Never perform any file operations or scan files.
> - Never override user folder scope.
> - Never trigger automated workflows (WeeklyOrganizerNode is Pub/Sub only).

---

## Proposed Changes

### Entry Point & Intent Classification Component

#### [NEW] [my_pc_assistant_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/my_pc_assistant_node.py)
Create the new ADK node with:
- **Input Schema (`MyPCAssistantInput`)**:
  - `user_query`: str
- **Output Schema (`MyPCAssistantOutput`)**:
  - `intent`: str  # 'cleanup' | 'search' | 'explain' | 'other'
  - `search_query`: str | None
  - `explanation_request`: str | None
- **Behavior**:
  - Categorizes `user_query` using Gemini classification (`gemini-2.5-flash`) with strict prompt rules.
  - If intent is `"cleanup"`, sets route to `"cleanup"` and forwards output.
  - If intent is `"search"`, sets route to `"search"` and forwards output.
  - If intent is `"explain"`, sets route to `"explain"` and forwards output.
  - If intent is `"other"`, responds conversationally (without routing downstream).

---

### File Discovery & Summary Adapters

#### [MODIFY] [file_discovery_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/file_discovery_node.py)
- Modify `file_discovery_node` to accept `FileDiscoveryInput | MyPCAssistantOutput`.
- If input is `MyPCAssistantOutput`, construct a default `FileDiscoveryInput` using `search_query=node_input.search_query`.

#### [MODIFY] [summary_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/summary_node.py)
- Modify `summary_node` to accept `ExecutionOutput | RollbackOutput | MyPCAssistantOutput`.
- If input is `MyPCAssistantOutput`, generate a conversational explanation for `explanation_request` via Gemini (`gemini-2.5-flash`) and output it in `SummaryOutput.human_readable_report`.

---

### Graph Routing & Exports

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Import `my_pc_assistant_node` and its schemas.
- Update `root_agent` to use `MyPCAssistantInput` as its `input_schema`.
- Wire `START -> my_pc_assistant_node`.
- Connect transitions:
  - `(my_pc_assistant_node, {"cleanup": folder_scope_node})`
  - `(my_pc_assistant_node, {"search": file_discovery_node})`
  - `(my_pc_assistant_node, {"explain": summary_node})`

#### [MODIFY] [__init__.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/__init__.py)
- Export the newly created `my_pc_assistant_node`, `MyPCAssistantInput`, and `MyPCAssistantOutput`.

---

## Proposed Enhancement Note

> [!TIP]
> **Heuristics Fallback for Classification**:
> In production networks, Gemini API limits or network issues might cause API call timeouts. We recommend adding a rule-based regex keyword classification check as a fallback if the API call fails, mapping queries containing `"clean"`, `"delete"`, or `"remove"` to `"cleanup"`, and queries containing `"find"`, `"search"`, or `"where"` to `"search"`.

---

## Verification Plan

### Automated Tests
- Create [test_my_pc_assistant.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_my_pc_assistant.py) verifying:
  - `"cleanup"` intent detection (routes to `FolderScopeNode`).
  - `"search"` intent detection and query extraction (routes to `FileDiscoveryNode`).
  - `"explain"` intent detection (routes to `SummaryNode` with correct query).
  - `"other"` intent detection (exits workflow).
  - Safety constraints: never infers cleanup intent for ambiguous or search queries.
