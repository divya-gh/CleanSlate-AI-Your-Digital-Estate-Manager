# Implementation Plan — WeeklyOrganizerNode

This plan outlines the creation and integration of the `WeeklyOrganizerNode`, which automates weekly cleanup in a safe, restricted mode.

## User Review Required

> [!IMPORTANT]
> The WeeklyOrganizerNode runs in **Safe Mode**. It will never execute deletions or compression.
> - Sensitive files are moved to `Authenticated/`
> - Duplicate files are moved to `WeeklyReview/`
> - All other files are skipped.
> - Triggers conditional routing: if disabled, it exits the graph immediately.

---

## Proposed Changes

### File Discovery Component

#### [MODIFY] [file_discovery_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/file_discovery_node.py)
- Update `FolderScopePolicy` schema to include:
  ```python
  safe_mode: bool = Field(default=False, description="Whether weekly organizer safe mode is active.")
  ```

---

### Weekly Organizer Component

#### [NEW] [weekly_organizer_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/weekly_organizer_node.py)
Create the new ADK node with:
- **Input Schema (`WeeklyOrganizerInput`)**:
  - `pubsub_event`: dict
  - `weekly_automation_enabled`: bool
  - `folder_scope_policy`: FolderScopePolicy
- **Output Schema (`WeeklySummary`)**:
  - `automation_ran`: bool
  - `actions_attempted`: int
  - `actions_completed`: int
  - `skipped`: int
  - `dry_run`: bool
  - `human_readable_report`: str
- **Behavior**:
  - If `weekly_automation_enabled` is `False`: returns `WeeklySummary` directly and sets route to `None` (terminates workflow).
  - If `weekly_automation_enabled` is `True`: sets `folder_scope_policy.safe_mode = True`, returns `FileDiscoveryInput` wrapping the policy, and sets route to `"run"`.

---

### Planner and Executor Components

#### [MODIFY] [optimization_planner_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/optimization_planner_node.py)
- Inspect `policy.safe_mode`.
- If `safe_mode` is `True`:
  - Skip all deletion, compression, archive, and screenshot suggestions.
  - Suggest move to `Authenticated/` for sensitive files.
  - Suggest move to `WeeklyReview/` for duplicate files (non-primary copies) that are safe to move.
  - Skip all other files.

#### [MODIFY] [execution_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/execution_node.py)
- Inspect `policy.safe_mode`.
- If `safe_mode` is `True`:
  - Fail and skip any `delete` or `compress` action.
  - For non-sensitive `move` actions, move the file to `WeeklyReview/` instead of `Organized/`.

---

### Graph Routing & Exports

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Import `weekly_organizer_node`.
- Wire `WeeklyOrganizerNode` as an isolated workflow:
  ```python
  (weekly_organizer_node, {"run": file_discovery_node}),
  ```
  - Note: FileDiscoveryNode and subsequent nodes will automatically propagate the modified policy (with `safe_mode=True`) through to ExecutionNode and SummaryNode.

#### [MODIFY] [__init__.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/__init__.py)
- Export `weekly_organizer_node`, `WeeklyOrganizerInput`, and `WeeklySummary`.

---

## Verification Plan

### Automated Tests
- Create [test_weekly_organizer.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_weekly_organizer.py) verifying:
  - If `weekly_automation_enabled` is `False`, returns summary report stating automation is disabled.
  - If `weekly_automation_enabled` is `True`, propagates `safe_mode=True` to `FileDiscoveryInput`.
  - In `safe_mode=True`, planner only schedules moves to `Authenticated` and `WeeklyReview`, skipping other actions.
  - In `safe_mode=True`, executor moves non-sensitive files to `WeeklyReview/` and guards against delete/compress.
