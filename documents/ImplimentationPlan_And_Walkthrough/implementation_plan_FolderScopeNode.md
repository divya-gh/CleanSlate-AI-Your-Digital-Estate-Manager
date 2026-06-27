# Implementation Plan — FolderScopeNode

This plan details the implementation of `FolderScopeNode` to gather allowed and blocked paths from the user during interactive cleanup sessions and establish a hard safety boundary.

## User Review Required

> [!IMPORTANT]
> **Safety Constraints**:
> - **No Auto-selection**: The node never auto-selects or infers allowed paths.
> - **System Path Isolation**: Allowed paths cannot contain system paths or system components.
> - **Implicit System Blocking**: System paths are added to blocked paths automatically by default.
> - **Interactive Loops**: If paths entered by the user are invalid or violate system checks, the node presents the validation error and prompts again.
> - **Zero Filesystem Interaction**: The node does not scan or touch the disk.

## Open Questions

- *None at this stage, as requirements are fully specified.*

## Proposed Changes

### Folder Scope Component

#### [NEW] [folder_scope_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/folder_scope_node.py)
Create `folder_scope_node.py` with:
- **Input Schema (`FolderScopeInput`)**:
  - `cleanup_intent`: bool
  - `user_query`: str | None = None
- **Output Schema (`FolderScopeOutput`)**:
  - `folder_scope_policy`: FolderScopePolicy | None = None
  - `message`: str
- **Behavior**:
  - If `cleanup_intent` is `False`: returns `FolderScopeOutput` message stating cleanup was not requested and terminates (`route=None`).
  - If `cleanup_intent` is `True`:
    - Checks for `allowed_paths` in `ctx.resume_inputs`. If not present, yields `RequestInput` prompting for allowed directories.
    - Checks for `blocked_paths` in `ctx.resume_inputs`. If not present, yields `RequestInput` prompting for blocked directories.
    - Validates inputs: checks for absolute paths, rejects empty entries/duplicates, checks that no allowed path resides in/contains system folders, and automatically populates default system paths inside `blocked_paths`.
    - If validation fails, resets input keys in `ctx.resume_inputs` and prompts again with an error message.
    - Construct `FolderScopePolicy` with:
      - `allowed_paths`: normalized paths
      - `blocked_paths`: normalized paths + default system paths
      - `safe_mode`: False
      - `allow_deletes`: True
      - `allow_moves`: True
      - `allow_archives`: True
      - `allow_compress`: True
    - Sets route to `"scan"`.

---

### File Discovery & Graph Modifications

#### [MODIFY] [file_discovery_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/file_discovery_node.py)
- Import `FolderScopeOutput` dynamically/normally.
- Modify `file_discovery_node` to also accept `FolderScopeOutput`.
- Extract the `FolderScopePolicy` when `FolderScopeOutput` is passed.

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Import `folder_scope_node`, `FolderScopeInput`, `FolderScopeOutput` from `app.nodes`.
- Remove placeholder `folder_scope_node`.
- Modify edge:
  - Change `(folder_scope_node, file_discovery_node)` to `(folder_scope_node, {"scan": file_discovery_node})`.

#### [MODIFY] [__init__.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/__init__.py)
- Import and export `FolderScopeInput`, `FolderScopeOutput`, and `folder_scope_node` in alphabetical order.

---

### Additional Feature / Enhancement Note

> [!TIP]
> **Proposed Enhancement: Validation Autocomplete & Existance Verification**:
> Currently, the user must manually input absolute paths. As an enhancement, we can verify if the entered directory paths actually exist on the user's filesystem. If a path does not exist, we notify the user instead of letting the downstream scanner fail silently or crash.

---

## Verification Plan

### Automated Tests
- Create [test_folder_scope.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_folder_scope.py) verifying:
  - If `cleanup_intent` is `False`, exits immediately with `route=None` and correct message.
  - Interactive loop correctly prompts for `allowed_paths` and `blocked_paths` when absent from context.
  - Validates allowed paths to reject system directories.
  - Correctly auto-populates system directories in blocked paths.
  - Correctly formats and constructs `FolderScopePolicy`.
  - Integrates with `file_discovery_node` to accept `FolderScopeOutput` successfully.
