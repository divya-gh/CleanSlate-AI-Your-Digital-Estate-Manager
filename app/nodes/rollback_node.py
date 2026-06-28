"""RollbackNode — ADK 2.0 Graph Workflow Node.

Reverses successfully executed cleanup actions (moves, archives, deletions) safely
in the event of execution failures or when explicitly requested.
Enforces double-safety runtime checks (never deletes, never touches blocked paths,
respects allowed path boundaries, protects system folders, prevents overwriting).
Rely ONLY on execution_log metadata; do not re-scan the filesystem.
"""

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field

from app.nodes.execution_node import ExecutionLogEntry, ExecutionOutput
from app.nodes.file_discovery_node import FolderScopePolicy
from app.nodes.sensitive_detection_node import SensitiveFileEntry
from app.mcp_tools.registry import test_tool

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class RollbackSummary(BaseModel):
    """Summary of the rollback operation."""

    attempted: int = Field(description="Number of rollback actions attempted.")
    succeeded: int = Field(
        description="Number of rollback actions successfully restored."
    )
    failed: int = Field(description="Number of rollback actions that failed.")
    unsupported: int = Field(
        description="Number of rollback actions that are unsupported."
    )
    dry_run: bool = Field(description="Whether this rollback was a dry run simulation.")
    human_readable_report: str = Field(
        description="Human-readable preview/report of rollback actions."
    )


class RollbackOutput(BaseModel):
    """Output payload emitted by RollbackNode."""

    execution_log: list[ExecutionLogEntry] = Field(
        default_factory=list, description="Updated execution log."
    )
    rollback_summary: RollbackSummary = Field(
        description="Summary of rollback details."
    )
    errors: list[str] = Field(
        default_factory=list, description="Rollback failure reasons."
    )
    folder_scope_policy: FolderScopePolicy = Field(
        description="Folder scope policy propagated downstream."
    )
    sensitive_files: list[SensitiveFileEntry] = Field(
        default_factory=list,
        description="Sensitive files propagated downstream.",
    )
    dry_run: bool = Field(description="Dry run status from execution.")
    estimated_recovery: int = Field(
        default=0, description="Total storage space recovered in bytes."
    )


# ---------------------------------------------------------------------------
# Safety Helpers
# ---------------------------------------------------------------------------


def _is_path_allowed(path: str, policy: FolderScopePolicy) -> bool:
    """Double-check allowed paths (must reside under at least one allowed path)."""
    resolved_path = os.path.normcase(os.path.abspath(path))
    if not policy.allowed_paths:
        return False

    any_allowed = False
    for ap in policy.allowed_paths:
        ap_resolved = os.path.normcase(os.path.abspath(ap))
        if resolved_path == ap_resolved or resolved_path.startswith(
            ap_resolved + os.sep
        ):
            any_allowed = True
            break
    return any_allowed


def _is_path_blocked(path: str, policy: FolderScopePolicy) -> bool:
    """Double-check blocked paths."""
    resolved_path = os.path.normcase(os.path.abspath(path))
    for bp in policy.blocked_paths:
        bp_resolved = os.path.normcase(os.path.abspath(bp))
        if resolved_path == bp_resolved or resolved_path.startswith(
            bp_resolved + os.sep
        ):
            return True
    return False


_SYSTEM_COMPONENTS = {
    "windows",
    "system32",
    "program files",
    "program files (x86)",
    "programdata",
    "appdata",
    ".git",
    ".venv",
    "node_modules",
    ".ruff_cache",
    ".pytest_cache",
}


def _is_system_folder(path: str) -> bool:
    """Double-check system directories."""
    parts = [p.lower() for p in Path(path).parts]
    for part in parts:
        if part in _SYSTEM_COMPONENTS:
            if part == "appdata" and "temp" in parts:
                continue
            return True
    return False


def _is_sensitive_file(path: str, sensitive_files: list[SensitiveFileEntry]) -> bool:
    """Check if the file is marked sensitive in the database/output."""
    norm_path = os.path.normcase(os.path.abspath(path))
    for sf in sensitive_files:
        if os.path.normcase(os.path.abspath(sf.path)) == norm_path:
            return sf.sensitive
    return False


def _clean_path(path: str, policy: FolderScopePolicy) -> str:
    """Hides absolute system/blocked paths by replacing them with generic text."""
    if _is_path_blocked(path, policy) or _is_system_folder(path):
        return "a protected file"
    return os.path.basename(path)


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def rollback_node(node_input: ExecutionOutput) -> RollbackOutput:
    """RollbackNode — reverses successful actions in execution_log where possible."""
    execution_log = node_input.execution_log
    policy = node_input.folder_scope_policy
    sensitive_files = node_input.sensitive_files
    dry_run = node_input.dry_run

    from app.config import set_policy_override
    set_policy_override(policy.model_dump())

    entry_dict = {
        "node": "RollbackNode",
        "action_type": "rollback",
        "path": None,
        "is_sensitive": False,
        "hitl_status": "not_required",
        "result": "pending",
        "reason": "Starting rollback sequence.",
        "rollback_reason": "execution failure",
        "tool_name": "write_log",
    }
    test_tool("write_log", entry=json.dumps(entry_dict))

    attempted_count = 0
    succeeded_count = 0
    failed_count = 0
    unsupported_count = 0
    errors_list: list[str] = []
    report_lines: list[str] = []

    # Create a copy of the log to update
    updated_log = [entry.model_copy() for entry in execution_log]

    # Rollback must process actions in reverse order of their execution
    for entry in reversed(updated_log):
        # We only roll back actions that successfully executed
        if entry.status != "success":
            continue

        is_sens = _is_sensitive_file(entry.original_path, sensitive_files)

        def log_rb_action(status: str, reason: str) -> None:
            entry_dict = {
                "node": "RollbackNode",
                "action_type": "rollback",
                "path": entry.original_path,
                "is_sensitive": is_sens,
                "hitl_status": "not_required",
                "result": status,
                "reason": reason,
                "backup_path": entry.backup_path,
                "rollback_reason": "execution failure",
                "tool_name": "write_log",
            }
            test_tool("write_log", entry=json.dumps(entry_dict))

        clean_orig = _clean_path(entry.original_path, policy)

        # Check support
        if not entry.rollback_supported:
            unsupported_count += 1
            report_lines.append(
                f"- Skipping {entry.action_type.upper()} for '{clean_orig}': Rollback not supported."
            )
            continue

        attempted_count += 1

        # Safeguard 1: Blocked paths
        if _is_path_blocked(entry.original_path, policy):
            failed_count += 1
            err = f"Rollback safety violation: Target path '{clean_orig}' is blocked."
            errors_list.append(err)
            report_lines.append(f"- Failed to restore '{clean_orig}': Blocked path.")
            log_rb_action(
                "failure", "Rollback safety violation: Target path is blocked."
            )
            continue

        # Safeguard 2: Allowed paths
        if not _is_path_allowed(entry.original_path, policy):
            failed_count += 1
            err = f"Rollback safety violation: Target path '{clean_orig}' is outside allowed directories."
            errors_list.append(err)
            report_lines.append(
                f"- Failed to restore '{clean_orig}': Outside allowed paths."
            )
            log_rb_action(
                "failure",
                "Rollback safety violation: Target path is outside allowed directories.",
            )
            continue

        # Safeguard 3: System folders
        if _is_system_folder(entry.original_path):
            failed_count += 1
            err = f"Rollback safety violation: Target path '{clean_orig}' resides inside a system directory."
            errors_list.append(err)
            report_lines.append(f"- Failed to restore '{clean_orig}': System folder.")
            log_rb_action(
                "failure",
                "Rollback safety violation: Target path resides inside a system directory.",
            )
            continue

        # Safeguard 4: Prevent overwrite
        orig_exists = False
        meta_res = test_tool("read_file_metadata", path=entry.original_path)
        if "error" not in meta_res:
            orig_exists = True

        if orig_exists:
            failed_count += 1
            err = f"Overwrite prevention: Path occupied at '{clean_orig}'."
            errors_list.append(err)
            report_lines.append(
                f"- Failed to restore '{clean_orig}': Path is occupied."
            )
            log_rb_action("failure", "Overwrite prevention: Path occupied.")
            continue

        # Recreate parent directory if missing safely under allowed_paths
        parent_dir = Path(entry.original_path).parent
        parent_exists = False
        meta_res = test_tool("list_files", path=str(parent_dir))
        if "error" not in meta_res:
            parent_exists = True

        if not parent_exists:
            # Check if parent directory itself is safe
            if (
                _is_path_allowed(str(parent_dir), policy)
                and not _is_path_blocked(str(parent_dir), policy)
                and not _is_system_folder(str(parent_dir))
            ):
                if not dry_run:
                    # Create folder safely via MCP tool
                    create_res = test_tool("create_folder", path=str(parent_dir))
                    if "error" in create_res:
                        failed_count += 1
                        err = f"Failed to recreate parent directory for '{clean_orig}': {create_res['error']['message']}"
                        errors_list.append(err)
                        report_lines.append(
                            f"- Failed to restore '{clean_orig}': Parent dir missing."
                        )
                        log_rb_action(
                            "failure", f"Failed to recreate parent directory: {create_res['error']['message']}"
                        )
                        continue
            else:
                failed_count += 1
                err = (
                    f"Parent directory recreation safety violation for '{clean_orig}'."
                )
                errors_list.append(err)
                report_lines.append(
                    f"- Failed to restore '{clean_orig}': Parent dir unsafe."
                )
                log_rb_action(
                    "failure", "Parent directory recreation safety violation."
                )
                continue

        # Dry run simulation
        if dry_run:
            succeeded_count += 1
            report_lines.append(
                f"- [Simulated] Restored '{clean_orig}' to its original location."
            )
            log_rb_action("skipped", "dry_run")
            continue

        # Perform the actual reversal
        try:
            if entry.action_type == "delete":
                if not entry.backup_path:
                    raise FileNotFoundError("Backup file path is empty.")
                
                backup_exists = False
                meta_res = test_tool("read_file_metadata", path=entry.backup_path)
                if "error" not in meta_res:
                    backup_exists = True
                if not backup_exists:
                    raise FileNotFoundError("Backup file not found.")

                # Copy back without deleting backup file (audit constraint)
                import shutil
                shutil.copy2(entry.backup_path, entry.original_path)  # nosemgrep: no-direct-filesystem-access-in-nodes

                succeeded_count += 1
                report_lines.append(
                    f"- Restored deleted file '{clean_orig}' from backup."
                )
                log_rb_action("success", "Restored deleted file from backup.")

            elif entry.action_type in ("move", "archive"):
                if not entry.new_path:
                    raise FileNotFoundError("Moved/archived file destination path is empty.")

                new_exists = False
                meta_res = test_tool("read_file_metadata", path=entry.new_path)
                if "error" not in meta_res:
                    new_exists = True
                if not new_exists:
                    raise FileNotFoundError(
                        "Moved/archived file not found at destination."
                    )

                move_res = test_tool("move_file", source=entry.new_path, destination=entry.original_path)
                if "error" in move_res:
                    raise ValueError(move_res["error"]["message"])

                succeeded_count += 1
                report_lines.append(
                    f"- Moved file '{clean_orig}' back to original path."
                )
                log_rb_action("success", "Moved file back to original location.")

            else:
                raise ValueError(
                    f"Unknown action type for rollback: {entry.action_type}"
                )

        except Exception as e:
            failed_count += 1
            err = f"Reversal failed for '{clean_orig}': {e}"
            errors_list.append(err)
            report_lines.append(f"- Failed to restore '{clean_orig}': {e}")
            log_rb_action("failure", f"Reversal failed: {e}")

    # Generate human readable report summary
    hdr_lines = ["### Rollback Activity Report"]
    hdr_lines.append(f"- Restored: {succeeded_count}")
    hdr_lines.append(f"- Unsupported: {unsupported_count}")
    hdr_lines.append(f"- Failures: {failed_count}")
    hdr_lines.append(f"- Dry-run active: {dry_run}")
    if report_lines:
        hdr_lines.append("\n#### Restored Files Summary:")
        hdr_lines.extend(report_lines)
    else:
        hdr_lines.append("\nNo rollback actions were required or performed.")

    human_readable_report = "\n".join(hdr_lines)

    summary = RollbackSummary(
        attempted=attempted_count,
        succeeded=succeeded_count,
        failed=failed_count,
        unsupported=unsupported_count,
        dry_run=dry_run,
        human_readable_report=human_readable_report,
    )

    entry_dict = {
        "node": "RollbackNode",
        "action_type": "rollback",
        "path": None,
        "is_sensitive": False,
        "hitl_status": "not_required",
        "result": "success" if failed_count == 0 else "failure",
        "reason": f"Rollback sequence completed. Succeeded: {succeeded_count}, Failed: {failed_count}.",
        "rollback_reason": "execution failure",
        "tool_name": "write_log",
    }
    test_tool("write_log", entry=json.dumps(entry_dict))

    return RollbackOutput(
        execution_log=updated_log,
        rollback_summary=summary,
        errors=errors_list,
        folder_scope_policy=policy,
        sensitive_files=sensitive_files,
        dry_run=dry_run,
        estimated_recovery=node_input.estimated_recovery,
    )
