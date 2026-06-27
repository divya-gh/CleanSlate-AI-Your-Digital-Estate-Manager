# Implementation Plan — MyPCAssistantNode

This plan outlines the creation and integration of `MyPCAssistantNode`, which acts as the main entry point and UI classification layer for all interactive user sessions.

## User Review Required

> [!IMPORTANT]
> **Safety Constraints**:
> - **Explicit Cleanup Only**: Cleanup intent must only be triggered by explicit verbs like “clean”, “organize my PC”, “declutter”, “optimize storage”. Ambiguous queries (“my PC is slow”, “I can’t find files”) must be classified as “other” and must not trigger cleanup.
> - **Metadata Isolation**: `MyPCAssistantNode` must never access filesystem metadata at all — it cannot accidentally reveal paths because it cannot see them.
> - **Search Limits**: `MyPCAssistantNode` must not call `FileDiscoveryNode` unless `intent="search"`.
> - **Weekly Organizer Guard**: `MyPCAssistantNode` must never emit a route that leads to `WeeklyOrganizerNode`.
> - **Sanitization**: `search_query` must be sanitized to remove absolute paths, system paths, sensitive keywords, and wildcard expansion.

---

## Proposed Changes

### Entry Point & Intent Classification Component

#### [NEW] [my_pc_assistant_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/my_pc_assistant_node.py)
Create the new ADK node with:
- **Input Schema (`MyPCAssistantInput`)**:
  - `user_query`: str
  - `session_id`: str | None = None
  - `timestamp`: datetime | None = None
- **Output Schema (`MyPCAssistantOutput`)**:
  - `intent`: str  # 'cleanup' | 'search' | 'explain' | 'other'
  - `search_query`: str | None = None
  - `explanation_request`: str | None = None
  - `cleanup_intent_reasoning`: str | None = None
  - `conversational_response`: str | None = None
- **Behavior**:
  - Categorizes `user_query` using Gemini classification (`gemini-2.5-flash`) with a safety-biased prompt:
    - If ambiguous, classify as `"other"`.
    - If partially cleanup-related, classify as `"other"`.
    - Only explicit cleanup verbs yield `"cleanup"`.
  - If intent is `"cleanup"`, sets route to `"cleanup"`, does not pass `search_query` or `explanation_request`, sets `cleanup_intent_reasoning="User explicitly requested cleanup"`.
  - If intent is `"search"`, sanitizes the search query (filters out absolute paths, system folders, wildcards), sets route to `"search"`.
  - If intent is `"explain"`, sets route to `"explain"`.
  - If intent is `"other"`, returns a `SummaryOutput`-compatible conversational response directly and sets route to `None`.
  - **Regex Fallback (Heuristics)**:
    - `"clean"`, `"cleanup"`, `"organize my PC"`, `"declutter"` (only explicit cleanup words) → `"cleanup"`
    - `"find"`, `"search"`, `"locate"`, `"where is"` → `"search"`
    - Vague terms (like `"slow"`, `"messy"`, `"full"`) → `"other"`

---

### File Discovery & Summary Adapters

#### [MODIFY] [file_discovery_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/file_discovery_node.py)
- Modify `file_discovery_node` to accept `FileDiscoveryInput | MyPCAssistantOutput`.
- If input is `MyPCAssistantOutput`, check if `intent == "search"`. If not, raise ValueError (rejecting the input).
- Validate the `search_query`: must not be empty, must not contain system paths or sensitive keywords, and must not exceed max length.
- Construct a default `FileDiscoveryInput` using the validated `search_query`.

#### [MODIFY] [summary_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/summary_node.py)
- Modify `summary_node` to accept `ExecutionOutput | RollbackOutput | MyPCAssistantOutput`.
- If input is `MyPCAssistantOutput`:
  - Verify it has `explanation_request` or `conversational_response`.
  - If it is a direct conversational response, populate it into `SummaryOutput.human_readable_report`.
  - If it is an explanation request, generate a conversational explanation via Gemini (`gemini-2.5-flash`) without accessing any file system metadata, file lists, or system paths, and return it in `SummaryOutput.human_readable_report`.

---

### Graph Routing & Exports

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Import `my_pc_assistant_node` and its schemas.
- Update `root_agent` to use `MyPCAssistantInput` as its `input_schema`.
- Wire `START -> my_pc_assistant_node`.
- Connect transitions:
  - `(my_pc_assistant_node, {"cleanup": folder_scope_node})`
  - `(my_pc_assistant_node, {"search": file_discovery_node})`
  - `(my_pc_assistant_node, {"explain": summary_node})`

#### [MODIFY] [__init__.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/__init__.py)
- Export the newly created elements in alphabetical order:
  - `MyPCAssistantInput`
  - `MyPCAssistantOutput`
  - `my_pc_assistant_node`

---

## Proposed Enhancement Note

> [!TIP]
> **Heuristics Fallback for Classification**:
> In production networks, Gemini API limits or network issues might cause API call timeouts. We recommend adding a rule-based regex keyword classification check as a fallback if the API call fails, mapping queries containing `"clean"`, `"delete"`, or `"remove"` to `"cleanup"`, and queries containing `"find"`, `"search"`, or `"where"` to `"search"`.

---

## Verification Plan

### Automated Tests
- Create [test_my_pc_assistant.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_my_pc_assistant.py) verifying:
  - `"cleanup"` intent detection (routes to `FolderScopeNode`).
  - `"search"` intent detection and query extraction (routes to `FileDiscoveryNode`).
  - `"explain"` intent detection (routes to `SummaryNode` with correct query).
  - `"other"` intent detection (exits workflow with conversational output).
  - Safety constraints: never infers cleanup intent for ambiguous or search queries.
  - Ambiguous queries → `"other"`
  - Queries containing both search + cleanup terms → `"other"`
  - Queries referencing WeeklyOrganizerNode → `"other"`
  - Queries referencing system paths → `"other"`
  - Explanation mode → `SummaryNode` produces explanation, not file summary.
