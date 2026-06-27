# RollbackNode Implementation Plan

We will create a new node `RollbackNode` in the ADK 2.0 graph workflow. `RollbackNode` will reverse successfully executed cleanup actions (restoring files from backups or moving files back) in case of execution failures.

## User Review Required
No breaking changes. This node will run conditionally as a sibling to `SummaryNode` after `ExecutionNode`.

## Proposed Changes

### Nodes Module

#### [NEW] [rollback_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/rollback_node.py)
We will create a new ADK 2.0 node with:
- **Input schema (`ExecutionOutput`)**: Consumes the log and configuration from `ExecutionNode`.
- **Output schema (`RollbackOutput`)**: Contains updated execution log, metadata, and a `rollback_summary` structure:
  - `attempted`: int
  - `succeeded`: int
  - `failed`: int
  - `unsupported`: int
  - `dry_run`: bool
  - `human_readable_report`: str
- **Behavior**:
  - Reverses delete actions by copying files back from `backup_path` to `original_path`.
  - Reverses move/archive actions by moving files back from `new_path` to `original_path`.
  - Skips compress actions (unsupported) and logs them as such.
  - Skips blocked paths, system folders, and paths outside `allowed_paths`.
  - Continues processing even if some reversals fail.
  - Never deletes any files during the rollback.
  - If `dry_run=True`, only simulates actions.

#### [MODIFY] [execution_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/execution_node.py)
- Modify the return value of `execution_node` to return an `Event` wrapping `ExecutionOutput`.
- Route to `"rollback"` if `failure_count > 0` and `rollback_enabled` is True.

#### [MODIFY] [summary_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/summary_node.py)
- Update `summary_node` input schema to accept `ExecutionOutput | RollbackOutput`.
- Update report formatting to append a **Rollback Execution Details** section if `rollback_summary` is present in the input.

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Wire `RollbackNode` conditionally after `ExecutionNode` and route it to `SummaryNode`:
  ```python
  (execution_node, {"rollback": rollback_node})
  (rollback_node, summary_node)
  ```

---

## Recommended Enhancement Note (RollbackNode)
- **Pre-Rollback Simulator (Dry-Run Rollback Preview)**: Add a feature to verify target original path status before starting the rollback. If the target path has since been occupied by a new file, the rollback can notify the user or suggest a merge instead of silently failing or overwriting.

---

## Verification Plan

### Automated Tests
- Create [test_rollback.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_rollback.py) verifying:
  - Deletions are correctly restored from `.rollback` files.
  - Moves and archives are correctly restored to original paths.
  - Blocked paths, system folders, and unallowed paths are skipped.
  - `dry_run=True` generates simulation logs without any filesystem side-effects.
  - Rollback summary counters match expected outcomes.
