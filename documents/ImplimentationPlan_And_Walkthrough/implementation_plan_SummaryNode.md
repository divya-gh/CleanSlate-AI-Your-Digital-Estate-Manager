# SummaryNode Implementation Plan

We will create a new node `SummaryNode` in the ADK 2.0 graph workflow. `SummaryNode` will act as a pure reporting node that aggregates the results of all executed cleanup actions and presents them in a secure, human-readable report.

## User Review Required
No breaking changes. This node will run immediately after `ExecutionNode`.

## Proposed Changes

### Nodes Module

#### [NEW] [summary_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/summary_node.py)
We will create a new ADK 2.0 node with:
- **Input schema (`ExecutionOutput`)**: Consume execution outcomes from `ExecutionNode`.
- **Output schema (`SummaryOutput`)**: Emits a `summary` containing:
  - `total_actions`: int
  - `successful_actions`: int
  - `failed_actions`: int
  - `skipped_actions`: int
  - `estimated_recovery`: int
  - `dry_run`: bool
  - `sensitive_files_protected`: int
  - `rollback_supported_actions`: int
  - `rollback_unsupported_actions`: int
  - `human_readable_report`: str
- **Behavior**:
  - Aggregate statistics from `execution_log[]`.
  - Calculate successful/failed/skipped action counts.
  - Count sensitive files that were protected (skipped delete or moved to `Authenticated`).
  - Count actions based on their `rollback_supported` status.
  - Formulate a clear markdown report for the UI.
- **Safety / Limits**:
  - Pure reporting: Absolutely no file system writes or modifications.
  - Never include sensitive file content previews, blocked paths, or system paths in the human-readable report. Use generic descriptors or relative basenames if paths must be referenced, avoiding absolute/sensitive leaks.

#### [MODIFY] [execution_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/execution_node.py)
- Update `ExecutionOutput` to propagate `folder_scope_policy` and `sensitive_files` so that `SummaryNode` has access to these lists downstream.

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Import and wire `summary_node` downstream of `execution_node`.

---

## Recommended Enhancement Note
- **Pre-Rollback Simulator**: We propose adding a **Dry-Run Rollback Preview** mode. When a rollback is requested, the system can generate a preview listing exactly which files will be restored from `.rollback` (deletions) or moved back (moves/archives) and how much storage change is expected, allowing the user to confirm the rollback before execution.

---

## Verification Plan

### Automated Tests
- Create [test_summary.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_summary.py) verifying:
  - Output metrics (successes, failures, recovery, rollback counts) are correctly aggregated.
  - Safety check: Assert that the human-readable report does not leak absolute blocked/system paths or sensitive file content.
  - Pure reporting check: Verify no file system calls are executed by `SummaryNode`.
