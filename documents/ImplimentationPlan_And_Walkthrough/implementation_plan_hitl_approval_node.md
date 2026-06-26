# ExecutionNode Implementation Plan

We will create the `ExecutionNode` in the ADK 2.0 graph workflow.

## Proposed Changes

### Nodes Module

#### [NEW] [execution_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/execution_node.py)
We will create a new ADK 2.0 node with:
- **Input schema**: Accepts `HITLApprovalOutput` (predecessor's output) containing `approved_actions`, `folder_scope_policy`, and `sensitive_files`.
- **Output schema (`ExecutionOutput`)**: Emits `execution_log[]` where each log entry contains:
  - `path`: str
  - `action_type`: str
  - `status`: str (success/failure)
  - `timestamp`: float
  - `reasoning`: str
- **Safety / Behavior**:
  - Implements local file execution:
    - **`delete`**: Safely deletes the file locally (only if `safe_to_delete` is True and path is allowed).
    - **`move`**: Moves the file to a target destination directory (e.g. creating it if needed).
    - **`compress`**: Simulates compression (or zips the file locally and removes the original).
    - **`archive`**: Moves files to an archive directory.
    - If a file is sensitive and is processed for moves or organization, we move it to an `Authenticated` subdirectory under the allowed path.
  - Enforces double-safety runtime checks:
    - **Never** deletes any file that exists in `sensitive_files` marked as sensitive.
    - **Never** modifies paths that are blocked or not allowed.
    - **Never** modifies system folders.
  - Catches `OSError` or any execution exception, records a failure, logs it, and continues processing other actions in the queue.

#### [MODIFY] [hitl_approval_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/hitl_approval_node.py)
- Propagate `folder_scope_policy` and `sensitive_files` in `HITLApprovalOutput` so they are accessible by `ExecutionNode`.

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Import and wire `execution_node` after `hitl_approval_node`.

## Verification Plan

### Automated Tests
- Create unit tests verifying:
  - Actions (delete, move, compress, archive) are executed correctly on temporary test files.
  - If a file is marked sensitive, delete actions fail or are blocked at runtime.
  - If a path is blocked, the node skips execution and logs a failure.
  - Failures during file system operations are logged but do not crash the node (continues execution).
  - Run linting and type checks.
