"""ExecutionNode — ADK 2.0 Graph Workflow Node.

Safely executes approved cleanup actions (move, delete, archive, compress,
or create folders). Enforces double-safety runtime checks (never deletes sensitive
files, never touches blocked paths, respects allowed path boundaries, protects system
folders). Supports dry-run and logs all outcomes.
"""

from __future__ import annotations

import os
import shutil
import time
import zipfile
from pathlib import Path
from typing import Literal

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from pydantic import BaseModel, Field

from app.nodes.file_discovery_node import FolderScopePolicy, resolve_real_path
from app.nodes.hitl_approval_node import HITLApprovalOutput
from app.nodes.optimization_planner_node import OptimizationPlannerOutput
from app.nodes.sensitive_detection_node import SensitiveFileEntry

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class ExecutionLogEntry(BaseModel):
    """Log entry detailing the outcome of an executed cleanup action."""

    path: str = Field(description="Absolute path to the target file.")
    action_type: str = Field(
        description="The executed action: 'delete', 'move', 'archive', 'compress'."
    )
    status: Literal["success", "failure"] = Field(
        description="Outcome status of the action."
    )
    timestamp: float = Field(description="Epoch timestamp when executed.")
    reasoning: str = Field(description="Reasoning / explanation of success or failure.")
    dry_run: bool = Field(description="Whether this action was simulated (dry-run).")
    original_path: str = Field(description="Original path of the target file.")
    new_path: str | None = Field(
        default=None, description="New path of the target file after execution."
    )
    backup_path: str | None = Field(
        default=None, description="Path where the backup copy is stored."
    )
    rollback_supported: bool = Field(
        default=False, description="Whether rollback is supported for this action."
    )


class ExecutionOutput(BaseModel):
    """Output payload emitted by ExecutionNode."""

    execution_log: list[ExecutionLogEntry] = Field(
        default_factory=list, description="Execution log list."
    )
    reasoning: str = Field(description="High-level reasoning summary of execution.")
    original_path: str = Field(default="", description="Original path.")
    new_path: str | None = Field(default=None, description="New path.")
    backup_path: str | None = Field(default=None, description="Backup path.")
    rollback_supported: bool = Field(
        default=False, description="Whether rollback is supported."
    )
    dry_run: bool = Field(
        default=True, description="Whether this execution was a dry run."
    )
    rollback_enabled: bool = Field(
        default=True, description="Whether rollback is enabled overall."
    )
    folder_scope_policy: FolderScopePolicy = Field(
        description="The folder scope policy used for discovery, propagated downstream."
    )
    sensitive_files: list[SensitiveFileEntry] = Field(
        default_factory=list,
        description="List of sensitive file entries, propagated downstream.",
    )
    estimated_recovery: int = Field(
        default=0, description="Total storage space recovered in bytes."
    )


# ---------------------------------------------------------------------------
# Helper functions
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


def _find_matching_allowed_path(path: str, policy: FolderScopePolicy) -> str | None:
    """Find the allowed path that the target file resides under."""
    resolved_path = os.path.normcase(os.path.abspath(path))
    if not policy.allowed_paths:
        return None
    for ap in policy.allowed_paths:
        ap_resolved = os.path.normcase(os.path.abspath(ap))
        if resolved_path == ap_resolved or resolved_path.startswith(
            ap_resolved + os.sep
        ):
            return ap
    return None


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def execution_node(node_input: HITLApprovalOutput | OptimizationPlannerOutput) -> Event:
    """ExecutionNode — safely executes each approved action."""
    if isinstance(node_input, HITLApprovalOutput):
        approved_actions = node_input.approved_actions
        rollback_enabled_flag = node_input.rollback_enabled
        dry_run = node_input.dry_run
    else:
        # OptimizationPlannerOutput (Weekly Safe Mode)
        approved_actions = node_input.action_plan.actions
        rollback_enabled_flag = False
        dry_run = node_input.action_plan.dry_run

    policy = node_input.folder_scope_policy
    sensitive_files = node_input.sensitive_files

    log: list[ExecutionLogEntry] = []
    success_count = 0
    failure_count = 0
    estimated_recovery_sum = 0
    actual_failures_count = 0

    for action in approved_actions:
        path = resolve_real_path(action.path)
        action_type = action.action_type
        now = time.time()

        p = Path(path)
        parent_dir = p.parent

        # Pre-compute rollback-related paths and flags
        if action_type == "delete":
            matching_ap = _find_matching_allowed_path(path, policy)
            rollback_dir = (
                Path(matching_ap) / ".rollback"
                if matching_ap
                else parent_dir / ".rollback"
            )
            calc_backup_path = str(rollback_dir / p.name)
            calc_new_path = None
            calc_rollback_supported = True
        elif action_type == "move":
            is_sensitive = _is_sensitive_file(path, sensitive_files)
            dest_dir = parent_dir / (
                "Authenticated"
                if is_sensitive
                else ("WeeklyReview" if policy.safe_mode else "Organized")
            )
            calc_backup_path = None
            calc_new_path = str(dest_dir / p.name)
            calc_rollback_supported = True
        elif action_type == "archive":
            dest_dir = parent_dir / "Archive"
            calc_backup_path = None
            calc_new_path = str(dest_dir / p.name)
            calc_rollback_supported = True
        elif action_type == "compress":
            calc_backup_path = None
            calc_new_path = path + ".zip"
            calc_rollback_supported = False
        else:
            calc_backup_path = None
            calc_new_path = None
            calc_rollback_supported = False

        # Guard 1: Blocked path double-guard
        if _is_path_blocked(path, policy):
            log.append(
                ExecutionLogEntry(
                    path=path,
                    action_type=action_type,
                    status="failure",
                    timestamp=now,
                    reasoning="Runtime Safety Check: Target path is inside blocked directories.",
                    dry_run=dry_run,
                    original_path=path,
                    new_path=None,
                    backup_path=None,
                    rollback_supported=False,
                )
            )
            failure_count += 1
            continue

        # Guard 2: Allowed path double-guard
        if not _is_path_allowed(path, policy):
            log.append(
                ExecutionLogEntry(
                    path=path,
                    action_type=action_type,
                    status="failure",
                    timestamp=now,
                    reasoning="Runtime Safety Check: Target path is outside allowed directories.",
                    dry_run=dry_run,
                    original_path=path,
                    new_path=None,
                    backup_path=None,
                    rollback_supported=False,
                )
            )
            failure_count += 1
            continue

        # Guard 3: System folder double-guard
        if _is_system_folder(path):
            log.append(
                ExecutionLogEntry(
                    path=path,
                    action_type=action_type,
                    status="failure",
                    timestamp=now,
                    reasoning="Runtime Safety Check: Modifying system directories is prohibited.",
                    dry_run=dry_run,
                    original_path=path,
                    new_path=None,
                    backup_path=None,
                    rollback_supported=False,
                )
            )
            failure_count += 1
            continue

        # Guard 4: Sensitive file deletion double-guard
        if action_type == "delete" and _is_sensitive_file(path, sensitive_files):
            log.append(
                ExecutionLogEntry(
                    path=path,
                    action_type=action_type,
                    status="failure",
                    timestamp=now,
                    reasoning="Runtime Safety Check: Sensitive files must never be deleted.",
                    dry_run=dry_run,
                    original_path=path,
                    new_path=None,
                    backup_path=None,
                    rollback_supported=False,
                )
            )
            failure_count += 1
            continue

        # Guard 5: safe_mode double-guard against deletes and compressions
        if policy.safe_mode and action_type in ("delete", "compress"):
            log.append(
                ExecutionLogEntry(
                    path=path,
                    action_type=action_type,
                    status="failure",
                    timestamp=now,
                    reasoning="Runtime Safety Check: Deletions and compression are prohibited in safe mode.",
                    dry_run=dry_run,
                    original_path=path,
                    new_path=None,
                    backup_path=None,
                    rollback_supported=False,
                )
            )
            failure_count += 1
            continue

        # Guard 6: Prevent overwrite guard for target destinations
        if calc_new_path and not dry_run and os.path.exists(calc_new_path):
            log.append(
                ExecutionLogEntry(
                    path=path,
                    action_type=action_type,
                    status="failure",
                    timestamp=now,
                    reasoning=f"Runtime Safety Check: Overwrite prevention. Target path '{os.path.basename(calc_new_path)}' is occupied.",
                    dry_run=dry_run,
                    original_path=path,
                    new_path=calc_new_path,
                    backup_path=calc_backup_path,
                    rollback_supported=calc_rollback_supported,
                )
            )
            failure_count += 1
            continue

        # File presence check (for dry-run=False)
        if not dry_run and not os.path.exists(path):
            log.append(
                ExecutionLogEntry(
                    path=path,
                    action_type=action_type,
                    status="failure",
                    timestamp=now,
                    reasoning="File not found on disk at time of execution.",
                    dry_run=dry_run,
                    original_path=path,
                    new_path=calc_new_path,
                    backup_path=calc_backup_path,
                    rollback_supported=calc_rollback_supported,
                )
            )
            failure_count += 1
            continue

        # Simulate execution in dry-run mode
        if dry_run:
            log.append(
                ExecutionLogEntry(
                    path=path,
                    action_type=action_type,
                    status="success",
                    timestamp=now,
                    reasoning=f"Dry-run simulation: Proposing {action_type} action successfully verified.",
                    dry_run=True,
                    original_path=path,
                    new_path=calc_new_path,
                    backup_path=calc_backup_path,
                    rollback_supported=calc_rollback_supported,
                )
            )
            success_count += 1
            estimated_recovery_sum += action.estimated_space_recovered
            continue

        # Real execution (dry_run=False)
        try:
            if action_type == "delete":
                if calc_backup_path:
                    os.makedirs(os.path.dirname(calc_backup_path), exist_ok=True)
                    shutil.copy2(path, calc_backup_path)
                os.remove(path)  # nosemgrep: no-direct-file-deletes
                log.append(
                    ExecutionLogEntry(
                        path=path,
                        action_type="delete",
                        status="success",
                        timestamp=now,
                        reasoning="File removed successfully from disk with backup copy saved for rollback.",
                        dry_run=False,
                        original_path=path,
                        new_path=None,
                        backup_path=calc_backup_path,
                        rollback_supported=True,
                    )
                )

            elif action_type == "move":
                is_sensitive = _is_sensitive_file(path, sensitive_files)
                if is_sensitive:
                    parent_dir = p.parent
                    dest_dir = parent_dir / "Authenticated"
                else:
                    parent_dir = p.parent
                    dest_dir = parent_dir / (
                        "WeeklyReview" if policy.safe_mode else "Organized"
                    )

                os.makedirs(dest_dir, exist_ok=True)
                dest_path = dest_dir / p.name
                shutil.move(path, str(dest_path))

                log.append(
                    ExecutionLogEntry(
                        path=path,
                        action_type="move",
                        status="success",
                        timestamp=now,
                        reasoning=f"File moved successfully to '{dest_path}'.",
                        dry_run=False,
                        original_path=path,
                        new_path=str(dest_path),
                        backup_path=None,
                        rollback_supported=True,
                    )
                )

            elif action_type == "compress":
                zip_path = path + ".zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(path, p.name)
                os.remove(path)  # nosemgrep: no-direct-file-deletes

                log.append(
                    ExecutionLogEntry(
                        path=path,
                        action_type="compress",
                        status="success",
                        timestamp=now,
                        reasoning=f"File compressed successfully into '{zip_path}'.",
                        dry_run=False,
                        original_path=path,
                        new_path=zip_path,
                        backup_path=None,
                        rollback_supported=False,
                    )
                )

            elif action_type == "archive":
                parent_dir = p.parent
                dest_dir = parent_dir / "Archive"
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = dest_dir / p.name
                shutil.move(path, str(dest_path))

                log.append(
                    ExecutionLogEntry(
                        path=path,
                        action_type="archive",
                        status="success",
                        timestamp=now,
                        reasoning=f"File archived successfully to '{dest_path}'.",
                        dry_run=False,
                        original_path=path,
                        new_path=str(dest_path),
                        backup_path=None,
                        rollback_supported=True,
                    )
                )
            else:
                raise ValueError(f"Unknown action type: {action_type}")

            success_count += 1
            estimated_recovery_sum += action.estimated_space_recovered

        except Exception as e:
            log.append(
                ExecutionLogEntry(
                    path=path,
                    action_type=action_type,
                    status="failure",
                    timestamp=now,
                    reasoning=f"Execution error: {e}",
                    dry_run=False,
                    original_path=path,
                    new_path=calc_new_path,
                    backup_path=calc_backup_path,
                    rollback_supported=calc_rollback_supported,
                )
            )
            failure_count += 1
            actual_failures_count += 1

    reasoning = (
        f"Executed {len(approved_actions)} action(s). "
        f"Status: {success_count} success(es), {failure_count} failure(s). "
        f"Dry run mode: {dry_run}."
    )

    rollback_should_trigger = rollback_enabled_flag and (actual_failures_count > 0)

    output_payload = ExecutionOutput(
        execution_log=log,
        reasoning=reasoning,
        original_path="",
        new_path=None,
        backup_path=None,
        rollback_supported=False,
        dry_run=dry_run,
        rollback_enabled=rollback_enabled_flag,
        folder_scope_policy=policy,
        sensitive_files=sensitive_files,
        estimated_recovery=estimated_recovery_sum,
    )

    if rollback_should_trigger:
        return Event(output=output_payload, actions=EventActions(route="rollback"))
    else:
        return Event(output=output_payload, actions=EventActions())
