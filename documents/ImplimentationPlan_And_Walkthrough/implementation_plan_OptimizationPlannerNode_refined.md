# Implementation Plan — OptimizationPlannerNode Rebuild (Final, Refined)

This plan covers rebuilding the `OptimizationPlannerNode` to generate recommended cleanup action plans with safe exclusions, audit logging metadata, and routing keys.

## User Review Required

> [!IMPORTANT]
> **Safety & Privacy Safeguards**:
> - **Exclusion Filters**:
>   - Exclude all files residing under `.rollback/`, `Authenticated/`, `WeeklyReview/`, or `Organized/`.
>   - Exclude files with masked filenames (`sensitive_file_<hash>`) from deletion entirely.
>   - If `safe_mode=True`, disable delete and compress actions.
> - **Duplicate deletion constraints**:
>   - Only delete duplicates if they are exact duplicates (SHA-256 match, `similarity_score == 1.0`), not sensitive, not masked, not in blocked/system paths, and not the last remaining copy.
> - **Metadata Logging**:
>   - Add versioning, timestamp, generated-by metadata to the `ActionPlan`.
>   - Add `action_reason` and `requires_user_confirmation` to each action entry.
> - **Routing**:
>   - If `safe_mode=True` (Weekly Organizer flow), route directly to `ExecutionNode` via `"execute"`.
>   - Otherwise, route to default edge (`hitl_approval_node`) using `route=None`.

## Proposed Changes

### Optimization Planner Component

#### [MODIFY] [optimization_planner_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/optimization_planner_node.py)
Rebuild node schemas and planning logic:
- **CleanupAction**: Add `action_reason: str` and `requires_user_confirmation: bool`.
- **ActionPlan**: Add `plan_version: str`, `generated_at: float`, and `generated_by: str`.
- **OptimizationPlannerOutput**: Add `sensitive_files`, `non_sensitive_files`, `safe_mode`, and `search_mode` to propagate downstream.
- **Safety Heuristics**: Exclude rollback/system directories, masked files from deletion, check age constraints ($>30$ days for archive), and check sizes ($>1$ MB and not already compressed).
- **Routing**: Set `route="execute"` in safe mode, otherwise `route=None`.

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Wire routing transitions:
  - `(optimization_planner_node, {"execute": execution_node})` (replaces `"safe_execute"` in both workflows).

---

## Verification Plan

### Automated Tests
- Update/create unit tests in `test_optimization_planner.py` to cover:
  - Exclusion of `.rollback/`, `Authenticated/`, `WeeklyReview/`, `Organized/` files.
  - Masked filenames excluded from deletion.
  - Delete/compress blocked in safe mode.
  - Duplicate deletion constraints.
  - Version, timestamp, generated-by metadata on the plan.
  - Correct routing configuration.
