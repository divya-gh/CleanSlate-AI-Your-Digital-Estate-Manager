"""ExecutionNode — ADK 2.0 Graph Workflow Node.

Safely executes approved cleanup actions (move, delete, archive, compress,
or create folders). Enforces double-safety runtime checks (never deletes sensitive
files, never touches blocked paths, respects allowed path boundaries, protects system
folders). Supports dry-run and logs all outcomes.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import time
from pathlib import Path
from typing import Literal

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from pydantic import BaseModel, Field

from app.nodes.file_discovery_node import FolderScopePolicy, resolve_real_path
from app.nodes.hitl_approval_node import HITLApprovalOutput
from app.nodes.optimization_planner_node import OptimizationPlannerOutput
from app.nodes.sensitive_detection_node import SensitiveFileEntry
from app.mcp_tools.registry import test_tool

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
        sf_real_path = resolve_real_path(sf.path)
        if os.path.normcase(os.path.abspath(sf_real_path)) == norm_path:
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
        dry_run = node_input.folder_scope_policy.dry_run

    policy = node_input.folder_scope_policy
    sensitive_files = node_input.sensitive_files

    from app.config import set_policy_override
    set_policy_override(policy.model_dump())
    try:
        log: list[ExecutionLogEntry] = []
        success_count = 0
        failure_count = 0
        estimated_recovery_sum = 0
        actual_failures_count = 0

        # Pre-process Authenticated_Secure folders to enforce PIN locking
        if hasattr(policy, "pin_hash") and getattr(policy, "pin_hash"):
            auth_dirs_seen = set()
            for action in approved_actions:
                path = resolve_real_path(action.path)
                if action.action_type == "move" and _is_sensitive_file(path, sensitive_files):
                    matching_ap = _find_matching_allowed_path(path, policy)
                    dest_parent = Path(matching_ap) if matching_ap else Path(path).parent
                    auth_dir = dest_parent / "Authenticated_Secure"
                    if str(auth_dir) not in auth_dirs_seen:
                        auth_dirs_seen.add(str(auth_dir))
                        data_dir = auth_dir / "_data_"
                        os.makedirs(data_dir, exist_ok=True)
                        if os.name == "nt":
                            # Hide the data folder initially
                            os.system(f'attrib +h +s "{data_dir}"')
                        
                        unlock_py = (
                            "import hashlib, os, getpass\n\n"
                            f"EXPECTED = '{policy.pin_hash}'\n"
                            "pin = getpass.getpass('Enter 4-digit PIN: ')\n"
                            "if hashlib.sha256(pin.encode()).hexdigest() == EXPECTED:\n"
                            "    script_dir = os.path.dirname(os.path.abspath(__file__))\n"
                            "    data_dir = os.path.join(script_dir, '_data_')\n"
                            "    if os.name == 'nt': os.system(f'attrib -h -s \"{data_dir}\"')\n"
                            "    print('Folder unlocked! You can now access _data_')\n"
                            "    if os.name == 'nt': os.system(f'explorer \"{data_dir}\"')\n"
                            "    input('Press Enter to exit...')\n"
                            "else:\n"
                            "    print('Invalid PIN.')\n"
                            "    input('Press Enter to exit...')\n"
                        )
                        lock_py = (
                            "import os\n"
                            "script_dir = os.path.dirname(os.path.abspath(__file__))\n"
                            "data_dir = os.path.join(script_dir, '_data_')\n"
                            "if os.name == 'nt': os.system(f'attrib +h +s \"{data_dir}\"')\n"
                            "print('Folder locked!')\n"
                            "import time; time.sleep(1)\n"
                        )
                        with open(auth_dir / "Unlock.py", "w") as f:
                            f.write(unlock_py)
                        with open(auth_dir / "Lock.py", "w") as f:
                            f.write(lock_py)

        def _process_action(action):
            local_log = []
            local_audit_logs = []
            local_success = 0
            local_failure = 0
            local_actual_failures = 0
            local_recovery = 0

            path = resolve_real_path(action.path)
            action_type = action.action_type
            now = time.time()

            p = Path(path)
            parent_dir = p.parent
            is_sensitive = _is_sensitive_file(path, sensitive_files)

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
                if is_sensitive:
                    matching_ap = _find_matching_allowed_path(path, policy)
                    dest_parent = Path(matching_ap) if matching_ap else parent_dir
                    auth_dir = dest_parent / "Authenticated_Secure"
                    dest_dir = auth_dir / "_data_"
                    os.makedirs(dest_dir, exist_ok=True)
                else:
                    dest_dir = parent_dir / (
                        "WeeklyReview" if policy.safe_mode else "Organized"
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

            def log_exec_action(
                status: str,
                reason: str,
                backup: str | None = None,
                action_type=action_type,
                path=path,
                is_sensitive=is_sensitive,
                calc_rollback_supported=calc_rollback_supported,
            ) -> None:
                entry_dict = {
                    "node": "ExecutionNode",
                    "action_type": action_type,
                    "path": path,
                    "is_sensitive": is_sensitive,
                    "hitl_status": "approved"
                    if isinstance(node_input, HITLApprovalOutput)
                    else "not_required",
                    "result": status,
                    "reason": reason,
                    "rollback_supported": calc_rollback_supported,
                    "rollback_enabled": rollback_enabled_flag,
                    "backup_path": backup,
                    "tool_name": "write_log",
                }
                local_audit_logs.append(entry_dict)

            if rollback_enabled_flag and not dry_run:
                log_exec_action("pending", "Starting execution with rollback enabled.")

            # Guard 1: Blocked path double-guard
            if _is_path_blocked(path, policy):
                local_log.append(
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
                local_failure += 1
                log_exec_action(
                    "failure",
                    "Runtime Safety Check: Target path is inside blocked directories.",
                )
                return local_log, local_audit_logs, local_success, local_failure, local_actual_failures, local_recovery

            # Guard 2: Allowed path double-guard
            if not _is_path_allowed(path, policy):
                local_log.append(
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
                local_failure += 1
                log_exec_action(
                    "failure",
                    "Runtime Safety Check: Target path is outside allowed directories.",
                )
                return local_log, local_audit_logs, local_success, local_failure, local_actual_failures, local_recovery

            # Guard 3: System folder double-guard
            if _is_system_folder(path):
                local_log.append(
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
                local_failure += 1
                log_exec_action(
                    "failure",
                    "Runtime Safety Check: Modifying system directories is prohibited.",
                )
                return local_log, local_audit_logs, local_success, local_failure, local_actual_failures, local_recovery

            # Guard 4: Sensitive file deletion double-guard
            if action_type == "delete" and _is_sensitive_file(path, sensitive_files):
                local_log.append(
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
                local_failure += 1
                log_exec_action(
                    "failure",
                    "Runtime Safety Check: Sensitive files must never be deleted.",
                )
                return local_log, local_audit_logs, local_success, local_failure, local_actual_failures, local_recovery

            # Guard 5: safe_mode double-guard against deletes and compressions
            if policy.safe_mode and action_type in ("delete", "compress"):
                local_log.append(
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
                local_failure += 1
                log_exec_action(
                    "failure",
                    "Runtime Safety Check: Deletions and compression are prohibited in safe mode.",
                )
                return local_log, local_audit_logs, local_success, local_failure, local_actual_failures, local_recovery

            # Guard 6: Prevent overwrite guard for target destinations
            dest_exists = False
            if calc_new_path and not dry_run:
                if os.path.exists(calc_new_path):
                    dest_exists = True

            if calc_new_path and not dry_run and dest_exists:
                local_log.append(
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
                local_failure += 1
                log_exec_action(
                    "failure",
                    "Runtime Safety Check: Overwrite prevention. Target path is occupied.",
                )
                return local_log, local_audit_logs, local_success, local_failure, local_actual_failures, local_recovery

            # Guard 7: Ensure sensitive files ONLY move to Authenticated_Secure
            if is_sensitive and action_type == "move":
                if calc_new_path and "Authenticated_Secure" not in Path(calc_new_path).parts:
                    local_log.append(
                        ExecutionLogEntry(
                            path=path,
                            action_type=action_type,
                            status="failure",
                            timestamp=now,
                            reasoning="Runtime Safety Check: Sensitive files must only be moved to Authenticated_Secure.",
                            dry_run=dry_run,
                            original_path=path,
                            new_path=calc_new_path,
                            backup_path=calc_backup_path,
                            rollback_supported=False,
                        )
                    )
                    local_failure += 1
                    log_exec_action(
                        "failure",
                        "Runtime Safety Check: Sensitive files must only be moved to Authenticated_Secure.",
                    )
                    return local_log, local_audit_logs, local_success, local_failure, local_actual_failures, local_recovery

            # File presence check (for dry-run=False)
            file_exists = False
            if not dry_run:
                if os.path.exists(path):
                    file_exists = True

            if not dry_run and not file_exists:
                local_log.append(
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
                local_failure += 1
                log_exec_action("failure", "File not found on disk at time of execution.")
                return local_log, local_audit_logs, local_success, local_failure, local_actual_failures, local_recovery

            # Simulate execution in dry-run mode
            if dry_run:
                local_log.append(
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
                local_success += 1
                local_recovery += action.estimated_space_recovered
                log_exec_action("skipped", "dry_run")
                return local_log, local_audit_logs, local_success, local_failure, local_actual_failures, local_recovery

            # Real execution (dry_run=False)
            try:
                if action_type == "delete":
                    if calc_backup_path:
                        # Registry-based safe move to backup path (deletes original from directory)
                        move_res = test_tool("move_file", source=path, destination=calc_backup_path)
                        if "error" in move_res:
                            raise ValueError(f"MoveToBackupFailed: {move_res['error']['message']}")
                    else:
                        # Permanent delete via MCP tool
                        del_res = test_tool("delete_file", path=path, hitl_approved=True)
                        if "error" in del_res:
                            raise ValueError(f"DeleteFailed: {del_res['error']['message']}")
                    local_log.append(
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
                    # Node already verified sensitivity and computed correct destination
                    # (Authenticated/ for sensitive, Organized/ or WeeklyReview/ for others).
                    # Use move_file uniformly — move_to_authenticated_folder's own
                    # is_sensitive() heuristic can produce false negatives.
                    move_res = test_tool("move_file", source=path, destination=calc_new_path)

                    if "error" in move_res:
                        raise ValueError(f"MoveFailed: {move_res['error']['message']}")

                    local_log.append(
                        ExecutionLogEntry(
                            path=path,
                            action_type="move",
                            status="success",
                            timestamp=now,
                            reasoning=f"File moved successfully to '{calc_new_path}'.",
                            dry_run=False,
                            original_path=path,
                            new_path=calc_new_path,
                            backup_path=None,
                            rollback_supported=True,
                        )
                    )

                elif action_type == "compress":
                    comp_res = test_tool("compress_files", files=[path], destination=calc_new_path)
                    if "error" in comp_res:
                        raise ValueError(f"CompressionFailed: {comp_res['error']['message']}")
                    
                    # Delete original file
                    del_res = test_tool("delete_file", path=path, hitl_approved=True)
                    if "error" in del_res:
                        raise ValueError(f"OriginalDeleteFailed: {del_res['error']['message']}")

                    local_log.append(
                        ExecutionLogEntry(
                            path=path,
                            action_type="compress",
                            status="success",
                            timestamp=now,
                            reasoning=f"File compressed successfully into '{calc_new_path}'.",
                            dry_run=False,
                            original_path=path,
                            new_path=calc_new_path,
                            backup_path=None,
                            rollback_supported=False,
                        )
                    )

                elif action_type == "archive":
                    # Same rationale as move — use move_file uniformly.
                    move_res = test_tool("move_file", source=path, destination=calc_new_path)

                    if "error" in move_res:
                        raise ValueError(f"ArchiveFailed: {move_res['error']['message']}")

                    local_log.append(
                        ExecutionLogEntry(
                            path=path,
                            action_type="archive",
                            status="success",
                            timestamp=now,
                            reasoning=f"File archived successfully to '{calc_new_path}'.",
                            dry_run=False,
                            original_path=path,
                            new_path=calc_new_path,
                            backup_path=None,
                            rollback_supported=True,
                        )
                    )
                else:
                    raise ValueError(f"Unknown action type: {action_type}")

                local_success += 1
                local_recovery += action.estimated_space_recovered
                log_exec_action(
                    "success",
                    f"Action {action_type} completed successfully.",
                    backup=calc_backup_path,
                )

            except Exception as e:
                local_log.append(
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
                local_failure += 1
                local_actual_failures += 1
                log_exec_action("failure", f"Execution error: {e}", backup=calc_backup_path)

            return local_log, local_audit_logs, local_success, local_failure, local_actual_failures, local_recovery

        with concurrent.futures.ThreadPoolExecutor(max_workers=64) as executor:
            results = list(executor.map(_process_action, approved_actions))

        for r_log, r_audit, r_succ, r_fail, r_act, r_rec in results:
            log.extend(r_log)
            success_count += r_succ
            failure_count += r_fail
            actual_failures_count += r_act
            estimated_recovery_sum += r_rec
            for entry_dict in r_audit:
                test_tool("write_log", entry=json.dumps(entry_dict))

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
    finally:
        from app.config import set_policy_override
        set_policy_override(None)
