# Implementation Plan — FileDiscoveryNode Rebuild

This plan covers rebuilding the `FileDiscoveryNode` to support multiple entry modes, enforce strict safety checks (symlink/hardlink blocking), perform sensitive filename masking, and limit scan depth/file counts.

## User Review Required

> [!IMPORTANT]
> **Safety Constraints**:
> - **Search / Safe Mode Path Masking**: When in search mode or weekly safe-mode automation, all absolute paths and sensitive filenames in output inventories will be masked (`sensitive_file_<sha1_hash>`) to prevent path leakages.
> - **Symlink & Junction Guards**: Skip any directory or file where `os.path.islink(path)` is true.
> - **Hardlink Guards**: Skip files where `st_nlink > 1`.
> - **Windows Read Resilience**: Skips locked/restricted system folders/files (e.g. throwing PermissionError or OSError) and logs them rather than crashing the workflow.
> - **Scanning Limits**: Restricts traversal to a maximum depth of 10 levels and a maximum count of 5,000 files.

## Open Questions

- *None at this stage. Requirements are fully specified by the final user plan.*

## Proposed Changes

### File Discovery Component

#### [MODIFY] [file_discovery_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/file_discovery_node.py)
Rebuild the node function to support the following:
- **Input schema support**: Accepts `FolderScopeOutput`, `MyPCAssistantOutput`, `WeeklyOrganizerInput`, or `FileDiscoveryInput`.
- **Mode detection**:
  - `MyPCAssistantOutput` (with `intent="search"`) → search mode.
  - `FolderScopeOutput` → interactive cleanup mode.
  - `WeeklyOrganizerInput` or `FileDiscoveryInput` (with `safe_mode=True`) → safe mode.
- **Search Query Validation**: Ensure search queries do not contain system paths, env variables, wildcards, sensitive keywords, and have length $\le$ 200.
- **Traversal & Scan logic**:
  - Recursive search up to a maximum depth of 10.
  - Limits file scan count to 5,000.
  - Skip symlinks and hardlinks.
  - Wrap directory/file walking inside `try-except (PermissionError, OSError)` block to log and skip forbidden/locked paths safely.
- **Sensitive Filename Masking**: If a filename matches sensitive pattern list (SSN, Passport, Bank, Medical, Tax terms), replace the filename segment with `sensitive_file_<sha1_hash_of_filename>`.
- **Output Schema**:
  - `file_inventory`: List[FileMetadata]
  - `folder_scope_policy`: FolderScopePolicy
  - `search_mode`: bool
  - `safe_mode`: bool
  - `reasoning`: str
- **Routing**: Set `route="classify"` to transition to `ClassificationNode`.

---

### Graph Transitions

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Wire/ensure transitions:
  - `(folder_scope_node, {"scan": file_discovery_node})`
  - `(my_pc_assistant_node, {"search": file_discovery_node})`
  - `(weekly_organizer_node, {"run": file_discovery_node})`
  - `(file_discovery_node, {"classify": classification_node})`

---

## Verification Plan

### Automated Tests
- Create [test_file_discovery.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_file_discovery.py) to cover:
  - `test_search_mode_query_validation`
  - `test_search_mode_filename_matching`
  - `test_interactive_mode_path_validation`
  - `test_symlink_rejection`
  - `test_permission_error_resilience`
  - `test_max_file_count_enforcement`
  - `test_max_depth_enforcement`
  - `test_sensitive_filename_masking`
  - `test_safe_mode_path_sanitization`
  - `test_integration_with_classification_node`
