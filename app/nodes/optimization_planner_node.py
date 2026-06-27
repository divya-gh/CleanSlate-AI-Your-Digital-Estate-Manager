"""OptimizationPlannerNode — ADK 2.0 Graph Workflow Node.

Generates a recommended cleanup action plan (move, archive, compress, delete)
based on classification, duplicates, and sensitive files, respecting
the folder scope policy and safety constraints.
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Literal

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from pydantic import BaseModel, Field

from app.nodes.classification_node import ClassifiedFile
from app.nodes.duplicate_detection_node import DuplicateGroup
from app.nodes.file_discovery_node import FileMetadata, FolderScopePolicy
from app.nodes.sensitive_detection_node import (
    SensitiveDetectionOutput,
    SensitiveFileEntry,
)

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class CleanupAction(BaseModel):
    """A single proposed cleanup action."""

    path: str = Field(description="Absolute path to the target file.")
    action_type: Literal["delete", "move", "archive", "compress"] = Field(
        description="The type of action suggested: 'delete', 'move', 'archive', 'compress'."
    )
    reasoning: str = Field(
        description="Detailed explanation of why this action is suggested."
    )
    action_reason: str = Field(
        default="",
        description="Human readable explanation.",
    )
    requires_user_confirmation: bool = Field(
        default=False,
        description="True if this action requires user confirmation before execution.",
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        default="low",
        description="Risk level associated with this cleanup action.",
    )
    estimated_time_seconds: float = Field(
        default=0.0,
        description="Estimated time to perform the action in seconds.",
    )
    estimated_space_recovered: int = Field(
        description="Estimated space recovered in bytes."
    )
    safe_to_delete: bool = Field(
        description="True if the file is safe to delete (not sensitive, not blocked, not system folder)."
    )
    confidence: float = Field(
        description="Confidence score for this suggestion (0.0 to 1.0).",
        ge=0.0,
        le=1.0,
    )


class ActionPlan(BaseModel):
    """The generated cleanup action plan."""

    actions: list[CleanupAction] = Field(
        default_factory=list,
        description="List of proposed actions.",
    )
    reasoning: list[str] = Field(
        default_factory=list,
        description="High-level reasoning comments summarizing the plan.",
    )
    estimated_recovery: int = Field(
        description="Total estimated storage space recovered in bytes."
    )
    dry_run: bool = Field(
        default=True,
        description="True because the planner always runs in dry-run mode first.",
    )
    plan_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the generated plan.",
    )
    total_actions: int = Field(
        default=0,
        description="Total count of proposed actions in the plan.",
    )
    total_sensitive_files: int = Field(
        default=0,
        description="Total count of sensitive files identified.",
    )
    total_duplicates_detected: int = Field(
        default=0,
        description="Total count of duplicate files detected.",
    )
    plan_version: str = Field(
        default="1.0",
        description="Version string for the action plan format.",
    )
    generated_at: float = Field(
        default_factory=time.time,
        description="Timestamp indicating when the plan was generated.",
    )
    generated_by: str = Field(
        default="OptimizationPlannerNode",
        description="Name of the node generating the plan.",
    )
    safe_mode: bool = Field(
        default=False,
        description="Whether safe mode was active when generating the plan.",
    )
    search_mode: bool = Field(
        default=False,
        description="Whether search mode was active when generating the plan.",
    )


class OptimizationPlannerOutput(BaseModel):
    """Output payload emitted by OptimizationPlannerNode."""

    action_plan: ActionPlan = Field(description="The generated action plan.")
    reasoning: str = Field(
        description="High-level reasoning summary of the planner node."
    )
    classified_files: list[ClassifiedFile] = Field(
        default_factory=list,
        description="List of classification results for every file (propagated downstream).",
    )
    duplicate_groups: list[DuplicateGroup] = Field(
        default_factory=list,
        description="List of duplicate groups identified (propagated downstream).",
    )
    file_inventory: list[FileMetadata] = Field(
        default_factory=list,
        description="List of metadata objects for every discovered file (propagated downstream).",
    )
    folder_scope_policy: FolderScopePolicy = Field(
        default_factory=lambda: FolderScopePolicy(allowed_paths=[]),
        description="The folder scope policy used for discovery, propagated downstream.",
    )
    sensitive_files: list[SensitiveFileEntry] = Field(
        default_factory=list,
        description="List of sensitive file entries (propagated downstream).",
    )
    non_sensitive_files: list[str] = Field(
        default_factory=list,
        description="List of non-sensitive file paths.",
    )
    safe_mode: bool = Field(
        default=False,
        description="Whether safe mode was active during planning.",
    )
    search_mode: bool = Field(
        default=False,
        description="Whether search mode was active during planning.",
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _is_path_allowed(path: str, policy: FolderScopePolicy) -> bool:
    """Verify path is allowed and not blocked by the scope policy."""
    resolved_path = os.path.normcase(os.path.abspath(path))

    # 1. Check blocked paths
    for bp in policy.blocked_paths:
        bp_resolved = os.path.normcase(os.path.abspath(bp))
        if resolved_path == bp_resolved or resolved_path.startswith(
            bp_resolved + os.sep
        ):
            return False

    # 2. Check allowed paths
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


def _is_excluded_path(path: str) -> bool:
    """Check if the path resides inside agent directories or excluded directories."""
    normalized = path.replace("\\", "/").lower()

    # Agent components and working folders
    agent_dirs = [
        "/.agents/",
        "/app/",
        "/tests/",
        "/.venv/",
        "/node_modules/",
        "/.ruff_cache/",
        "/.pytest_cache/",
    ]
    if any(
        ad in normalized or normalized.endswith(ad.rstrip("/")) for ad in agent_dirs
    ):
        return True

    # Excluded application folders
    parts = [p.lower() for p in Path(path).parts]
    excluded_dirs = {
        ".rollback",
        "authenticated",
        "weeklyreview",
        "organized",
        "windows",
        "system32",
        "program files",
        "program files (x86)",
        "programdata",
        "appdata",
    }
    for p in parts:
        if p in excluded_dirs:
            if p == "appdata" and "temp" in parts:
                continue
            return True
    return False


_COMPRESSED_EXTENSIONS = {
    ".zip",
    ".gz",
    ".tar",
    ".rar",
    ".7z",
    ".bz2",
    ".xz",
}

# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def optimization_planner_node(
    node_input: SensitiveDetectionOutput,
) -> Event:
    """OptimizationPlannerNode — generates recommended cleanup action plan."""
    inventory = node_input.file_inventory
    policy = node_input.folder_scope_policy
    duplicate_groups = node_input.duplicate_groups
    classified_lookup = {cf.path: cf for cf in node_input.classified_files}
    sensitive_lookup = {sf.path: sf for sf in node_input.sensitive_files}

    safe_mode = node_input.safe_mode or policy.safe_mode
    search_mode = node_input.search_mode or getattr(policy, "search_mode", False)

    actions: list[CleanupAction] = []
    reasoning_comments: list[str] = []
    total_recovered = 0

    # Build maps for duplicate identification
    paths_to_delete: set[str] = set()
    exact_duplicates: set[str] = set()

    for group in duplicate_groups:
        if len(group.files) > 1:
            # First file is kept (not suggested for deletion)
            for dup_entry in group.files[1:]:
                paths_to_delete.add(dup_entry.path)
                if dup_entry.similarity_score == 1.0:
                    exact_duplicates.add(dup_entry.path)

    total_sensitive_count = sum(1 for sf in node_input.sensitive_files if sf.sensitive)
    total_duplicates_detected = len(paths_to_delete)

    for file in inventory:
        path_str = file.path
        is_allowed = _is_path_allowed(path_str, policy)
        is_excluded = _is_excluded_path(path_str)

        # Skip checking any excluded folders or working directories entirely
        if is_excluded:
            continue

        sf = sensitive_lookup.get(path_str)
        is_sensitive = sf.sensitive if sf else False

        # In safe mode, we ONLY suggest moves to Authenticated or WeeklyReview
        if safe_mode:
            if is_sensitive:
                if is_allowed:
                    actions.append(
                        CleanupAction(
                            path=path_str,
                            action_type="move",
                            reasoning="Sensitive file moved to Authenticated",
                            action_reason="Safe isolation of sensitive file.",
                            requires_user_confirmation=True,
                            risk_level="low",
                            estimated_space_recovered=0,
                            safe_to_delete=False,
                            confidence=1.0,
                        )
                    )
                continue

            if path_str in paths_to_delete:
                if is_allowed:
                    actions.append(
                        CleanupAction(
                            path=path_str,
                            action_type="move",
                            reasoning="Duplicate file moved to WeeklyReview",
                            action_reason="Safe isolation of duplicate file.",
                            requires_user_confirmation=True,
                            risk_level="low",
                            estimated_space_recovered=0,
                            safe_to_delete=False,
                            confidence=0.90,
                        )
                    )
                continue

            continue

        # Fetch category/basename
        cf = classified_lookup.get(path_str)
        category = cf.category if cf else "misc"
        basename = Path(path_str).name
        is_masked = "sensitive_file_" in basename.lower()

        # Determine baseline safety constraints
        is_safe_to_delete = is_allowed and (not is_sensitive) and (not is_excluded)

        # Calculate ages
        now = time.time()
        age_days = (now - file.last_modified) / 86400.0
        access_age_days = (now - file.last_accessed) / 86400.0

        # 1. Duplicate Handling constraints
        if path_str in paths_to_delete:
            if (
                is_safe_to_delete
                and (path_str in exact_duplicates)
                and (not is_masked)
                and policy.allow_deletes
                and (not search_mode)
                and category != "source_code"
            ):
                actions.append(
                    CleanupAction(
                        path=path_str,
                        action_type="delete",
                        reasoning="Exact duplicate of another file.",
                        action_reason="Exact duplicate file cleanup.",
                        requires_user_confirmation=True,
                        risk_level="medium",
                        estimated_space_recovered=file.size,
                        safe_to_delete=True,
                        confidence=0.95,
                    )
                )
                total_recovered += file.size
            continue

        # Skip non-duplicate operations on blocked or sensitive files
        if is_sensitive or (not is_allowed):
            continue

        # Skip source code actions from destructive alterations
        if category == "source_code":
            continue

        # 2. Screenshot Moves
        if category == "screenshot" and policy.allow_moves:
            parent_dir = Path(path_str).parent
            target_path = str(parent_dir / "Screenshots" / basename)
            actions.append(
                CleanupAction(
                    path=path_str,
                    action_type="move",
                    reasoning=f"Move screenshot to Screenshots folder: {target_path}",
                    action_reason=" screenshot management.",
                    requires_user_confirmation=False,
                    risk_level="low",
                    estimated_space_recovered=0,
                    safe_to_delete=False,
                    confidence=0.80,
                )
            )
            continue

        # 3. Compression Suggestions
        if (
            file.size > 1024 * 1024
            and file.extension.lower() in {".txt", ".log", ".csv"}
            and access_age_days >= 14
            and file.extension.lower() not in _COMPRESSED_EXTENSIONS
        ):
            recovered = int(file.size * 0.6)
            actions.append(
                CleanupAction(
                    path=path_str,
                    action_type="compress",
                    reasoning="Large text file that has not been accessed frequently.",
                    action_reason="Storage compression.",
                    requires_user_confirmation=True,
                    risk_level="low",
                    estimated_space_recovered=recovered,
                    safe_to_delete=False,
                    confidence=0.75,
                )
            )
            total_recovered += recovered
            continue

        # 4. Archive Suggestions
        if age_days > 30 and access_age_days >= 7 and policy.allow_moves:
            actions.append(
                CleanupAction(
                    path=path_str,
                    action_type="archive",
                    reasoning="File has not been modified for 30 days and access is low.",
                    action_reason="Archive storage allocation.",
                    requires_user_confirmation=False,
                    risk_level="low",
                    estimated_space_recovered=0,
                    safe_to_delete=False,
                    confidence=0.70,
                )
            )

    # General Comments
    reasoning_comments.append(
        f"Generated {len(actions)} optimization suggestions. "
        f"Planner is running in dry-run mode: dry_run=True. "
        f"Estimated storage recovery: {total_recovered} bytes. "
        f"Excluded all sensitive and excluded files."
    )

    action_plan = ActionPlan(
        actions=actions,
        reasoning=reasoning_comments,
        estimated_recovery=total_recovered,
        dry_run=policy.dry_run if safe_mode else True,
        total_actions=len(actions),
        total_sensitive_files=total_sensitive_count,
        total_duplicates_detected=total_duplicates_detected,
        safe_mode=safe_mode,
        search_mode=search_mode,
    )

    high_level_reasoning = (
        f"Created cleanup plan proposing {len(actions)} action(s) for a "
        f"total recovery of {total_recovered} bytes. Plan is currently a dry-run."
    )

    output_payload = OptimizationPlannerOutput(
        action_plan=action_plan,
        reasoning=high_level_reasoning,
        classified_files=node_input.classified_files,
        duplicate_groups=duplicate_groups,
        file_inventory=inventory,
        folder_scope_policy=policy,
        sensitive_files=node_input.sensitive_files,
        non_sensitive_files=node_input.non_sensitive_files,
        safe_mode=safe_mode,
        search_mode=search_mode,
    )

    # Route configuration
    if len(actions) == 0:
        return Event(
            output=output_payload,
            actions=EventActions(
                route=None,
            ),
        )

    if safe_mode:
        return Event(output=output_payload, actions=EventActions(route="execute"))
    else:
        return Event(output=output_payload, actions=EventActions())
