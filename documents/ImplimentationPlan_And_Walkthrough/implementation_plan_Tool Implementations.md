# Implementation Plan — MCP Tools Final Refinements

Implement the finalized safety enforcements, file size guards, atomic file operations, log rotation, and new Semgrep security rules.

## User Review Required

> [!IMPORTANT]
> - `list_files` and `read_file_metadata` will explicitly reject symlinks, Windows junctions, and directory traversal, returning `"symlink_blocked": true` on symlink rejection.
> - `compute_hash` will reject files >2GB, returning `"file_too_large": true`.
> - `delete_file` will include `"safe_mode_blocked": true` and `"safe_mode": true` in error details.
> - `write_log` will support operation tracking (`operation_id` using UUID4) and auto-rotate when log size exceeds 10MB.
> - Add Semgrep rules for: `no-symlink-following`, `no-unsafe-shutil-move`, `no-absolute-path-return`, and `no-directory-traversal`.
> - Push annotated git tag `v1.3-mcp-tools`.

## Proposed Changes

### MCP Tools Refinements
- **list_files / read_file_metadata**: Prevent traversal (`..`) using `os.path.realpath` checks. Reject symlinks with `os.path.islink()` and junctions via `st_reparse_tag` checks where supported.
- **compute_hash**: Validate file size < 2GB. Stream with `chunk_size = 65536`.
- **move_file / move_to_authenticated_folder**: Implement atomic fallback using `os.replace` first, then `shutil.move` if safe.
- **delete_file**: Log `"delete_reason"`. Add `"safe_mode_blocked": true` and `"blocked_by_sensitive": true` to error details.
- **write_log / read_log**: Add UUID4 `operation_id` and rotate log files at 10MB to `.1`.

### Semgrep Rules
- Add rules: `no-symlink-following`, `no-unsafe-shutil-move`, `no-absolute-path-return`, and `no-directory-traversal` to `.semgrep/sdd-safety-rules.yaml`.

---

## Verification Plan

### Automated Tests
- Test symlink/junction blocking, traversal rejection, 2GB limits, log rotation, atomic fallback, and refined error detail fields.
- Run `uv run pytest`.
- Run Semgrep scan.
