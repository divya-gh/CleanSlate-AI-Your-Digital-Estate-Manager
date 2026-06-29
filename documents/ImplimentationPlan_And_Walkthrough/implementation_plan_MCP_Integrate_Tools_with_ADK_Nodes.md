# Implementation Plan — MCP Tool Node Integration

This plan outlines the integration of the refined MCP tools package with the ADK 2.0 agent graph nodes to ensure safe, policy-compliant, and metadata-only execution.

## User Review Required

> [!IMPORTANT]
> - All node-level file access and directory listings will be fully refactored to delegate to the MCP tools (`list_files`, `read_file_metadata`, `compute_hash`, etc.) registered inside `app/mcp_tools/registry.py`. Nodes will never touch the filesystem directly.
> - Nodes will handle MCP error formats gracefully and propagate the error objects upstream completely unchanged for agent response validation.
> - Semgrep rules will run on the node layer to ensure no accidental `open()` or direct directory walking calls slip in.

## Proposed Changes

### Component integration

***

### [FileDiscoveryNode](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/file_discovery_node.py)
- Refactor the directory walking function to call `list_files` (from the MCP registry) recursively rather than using `os.walk` directly.
- Recursion is done by repeatedly calling `list_files` to keep discovery fully MCP-driven.
- Retrieve metadata utilizing the `read_file_metadata` tool for each discovered item.
- Enforce allowed scope path masking and system exclusions inside the discovery boundaries.

***

### [ClassificationNode](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/classification_node.py)
- Replace direct `os.stat` or file opens with the metadata-only `read_file_metadata` MCP tool.
- Guarantee that classification logic uses only metadata fields (extension, size, timestamps). Absolutely zero file content reads or opens occur.

***

### [DuplicateDetectionNode](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/duplicate_detection_node.py)
- Retrieve hashes using `compute_hash` from the MCP registry.
- Propagate `"file_too_large"` and `"sensitive_file_blocked"` flags exactly as MCP tools return them.

***

### [SensitiveDetectionNode](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/sensitive_detection_node.py)
- Heuristics must rely on metadata only (suffix, size, timestamps) with no content inspection. Use `read_file_metadata` to retrieve file suffixes, sizes, and times for sensitivity checks.

***

### [ExecutionNode](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/execution_node.py)
- Refactor all file operations to call the corresponding MCP tool via the registry.
- `ExecutionNode` is a pure orchestrator: it never touches the filesystem directly, never logs directly, and only calls MCP tools:
  - `move_file` (for generic moves)
  - `delete_file` (requires `hitl_approved` flag, checks `safe_mode`)
  - `create_folder` (creates directory tree safely)
  - `compress_files` (filters target files)
  - `move_to_authenticated_folder` (locks sensitive files)
  - `write_log` (for writing execution event audits)

***

### [RollbackNode](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/rollback_node.py)
- Use `move_file` for atomic replacement rollback logic.
- Treat MCP errors as first-class citizens and log rollback failures via `write_log`.

***

### [SummaryNode](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/summary_node.py)
- Use `read_log` to fetch and format execution audits.
- Redact sensitive paths automatically since `read_log` already performs this step.

***

### [WeeklyOrganizerNode](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/weekly_organizer_node.py)
- Rely on MCP tools (`list_files`, `read_file_metadata`, `move_file`, and `compress_files`) for every operation with no custom filesystem logic.
- Track weekly status operations using `write_log`.

## Verification Plan

### Automated Tests
- Run `uv run pytest` to execute the full unit/integration test suite.
- Add tests verifying that nodes never call `os.*` or `open()` directly.
- Add tests confirming nodes propagate MCP error objects unchanged.
- Run Semgrep static analysis scanning: `uv run semgrep scan --config=.semgrep/sdd-safety-rules.yaml --error`.
  - Ensure node-level Semgrep rules include:
    - `no-direct-open`
    - `no-direct-os-walk`
    - `no-direct-path-joins-outside-policy`
