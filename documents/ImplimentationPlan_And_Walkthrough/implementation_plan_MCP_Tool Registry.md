# Implementation Plan — MCP Tool Spec (Refined)

Implement all 10 MCP tools under the `app/mcp_tools/` directory, incorporating the detailed design and safety refinements from the feedback.

## User Review Required

> [!IMPORTANT]
> - Centralize policy checks inside `app/mcp_tools/utils.py`.
> - Ensure `delete_file.py` rejects deletions when `hitl_approved=False` or when the file is sensitive or safe mode is enabled.
> - Ensure `compute_hash.py` implements a streaming chunked loop with a localized nosemgrep ignore.
> - Prevent compressing or deleting sensitive files.

## Proposed Changes

### MCP Tools Layer

#### [NEW] [__init__.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/__init__.py)
Package entrypoint exposing the registry of tools.

#### [NEW] [utils.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/utils.py)
Shared safety functions:
- `is_path_allowed_by_policy(path)`: Checks against policy and blocks system folders.
- `is_sensitive(path)`: Extension, name, and keyword heuristics.
- `is_authenticated_folder(path)`: Checks if the path belongs to a secure/authenticated directory.

#### [NEW] [list_files.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/list_files.py)
Lists directory files and folders; metadata only (no previews, no content).

#### [NEW] [read_file_metadata.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/read_file_metadata.py)
Metadata-only information via `os.stat` and `mimetypes` (no content reads).

#### [NEW] [compute_hash.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/compute_hash.py)
Computes hashes using chunked streaming reads with localized `# nosemgrep` comments.

#### [NEW] [move_file.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/move_file.py)
Atomic moves with checks; restricts sensitive files to authenticated directories.

#### [NEW] [delete_file.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/delete_file.py)
Requires `hitl_approved=True` and `safe_mode=False`. Refuses to delete sensitive files.

#### [NEW] [create_folder.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/create_folder.py)
Creates allowed directories atomically.

#### [NEW] [compress_files.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/compress_files.py)
Skips sensitive files during compression.

#### [NEW] [write_log.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/write_log.py)
Uses the central audit logger to append JSONL entries.

#### [NEW] [read_log.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/read_log.py)
Reads logs with line limit and redacts sensitive paths.

#### [NEW] [move_to_authenticated_folder.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/move_to_authenticated_folder.py)
Enforces sensitive file migration to authenticated destinations.

---

## Verification Plan

### Automated Tests
- Create tests under `tests/unit/test_mcp_tools.py` verifying:
  - Allowed vs blocked paths.
  - Sensitive vs non-sensitive behavior.
  - HITL flag enforcement in `delete_file`.
  - Redaction in logging.
  - Hashing performance/streaming.
- Run `uv run pytest`.
- Verify Semgrep safety check passes with 0 violations.
