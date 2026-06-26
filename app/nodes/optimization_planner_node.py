"""OptimizationPlannerNode — ADK 2.0 Graph Workflow Node.

Generates a recommended cleanup action plan (move, archive, compress, delete)
based on classification, duplicates, and sensitive files, respecting
the folder scope policy and safety constraints.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.nodes.file_discovery_node import FolderScopePolicy
from app.nodes.sensitive_detection_node import SensitiveDetectionOutput

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


class OptimizationPlannerOutput(BaseModel):
    """Output payload emitted by OptimizationPlannerNode."""

    action_plan: ActionPlan = Field(description="The generated action plan.")
    reasoning: str = Field(
        description="High-level reasoning summary of the planner node."
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
    """Check if the path falls inside common system or package manager folders."""
    parts = Path(path).parts
    for part in parts:
        if part.lower() in _SYSTEM_COMPONENTS:
            return True
    return False


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def optimization_planner_node(
    node_input: SensitiveDetectionOutput,
) -> OptimizationPlannerOutput:
    """OptimizationPlannerNode — generates recommended cleanup action plan."""
    inventory = node_input.file_inventory
    policy = node_input.folder_scope_policy
    duplicate_groups = node_input.duplicate_groups
    classified_lookup = {cf.path: cf for cf in node_input.classified_files}
    sensitive_lookup = {sf.path: sf for sf in node_input.sensitive_files}

    actions: list[CleanupAction] = []
    reasoning_comments: list[str] = []
    total_recovered = 0

    # Build maps for quick duplicates checks
    duplicate_paths: set[str] = set()
    paths_to_delete: set[str] = set()

    for group in duplicate_groups:
        # Keep the first file, suggest deleting the remaining ones
        if len(group.files) > 1:
            primary_file = group.files[0]
            duplicate_paths.add(primary_file.path)
            for dup_entry in group.files[1:]:
                duplicate_paths.add(dup_entry.path)
                paths_to_delete.add(dup_entry.path)

    # Process all discovered files
    for file in inventory:
        path_str = file.path
        is_allowed = _is_path_allowed(path_str, policy)
        is_system = _is_system_folder(path_str)

        # Sensitive check
        sf = sensitive_lookup.get(path_str)
        is_sensitive = sf.sensitive if sf else False

        # Category and extension
        cf = classified_lookup.get(path_str)
        category = cf.category if cf else "misc"

        # Determine safety constraints for deleting
        is_safe_to_delete = is_allowed and (not is_sensitive) and (not is_system)

        # 1. Suggest Delete for duplicates (keeping one primary copy)
        if path_str in paths_to_delete:
            if is_safe_to_delete:
                reason = "Exact or near duplicate of another file in inventory."
                actions.append(
                    CleanupAction(
                        path=path_str,
                        action_type="delete",
                        reasoning=reason,
                        estimated_space_recovered=file.size,
                        safe_to_delete=True,
                        confidence=0.95,
                    )
                )
                total_recovered += file.size
            else:
                reasoning_comments.append(
                    f"Skipped duplicate suggestion for '{Path(path_str).name}': "
                    f"sensitive={is_sensitive}, allowed={is_allowed}, system={is_system}."
                )
            continue

        # Skip planning other active actions on sensitive, blocked, or system files
        if is_sensitive or (not is_allowed) or is_system:
            continue

        # 2. Suggest Move for screenshots (organize them into a cleaner folder structure)
        if category == "screenshot":
            # Suggest moving screenshots to an archive or dedicated subfolder
            parent_dir = Path(path_str).parent
            target_path = str(parent_dir / "Screenshots" / Path(path_str).name)
            actions.append(
                CleanupAction(
                    path=path_str,
                    action_type="move",
                    reasoning=f"Organize screenshot into dedicated subfolder '{target_path}'.",
                    estimated_space_recovered=0,
                    safe_to_delete=False,
                    confidence=0.80,
                )
            )
            continue

        # Calculate file age
        now = time.time()
        age_days = (now - file.last_modified) / 86400.0
        access_age_days = (now - file.last_accessed) / 86400.0

        # 3. Suggest Compress for large text files that are old but accessed occasionally
        if file.size > 1024 * 1024 and file.extension.lower() in {
            ".txt",
            ".log",
            ".csv",
        }:
            # Older than 14 days
            if age_days > 14:
                reason = (
                    "Large text/log file older than 14 days; compressing saves space."
                )
                # Estimate 60% compression recovery
                recovered = int(file.size * 0.6)
                actions.append(
                    CleanupAction(
                        path=path_str,
                        action_type="compress",
                        reasoning=reason,
                        estimated_space_recovered=recovered,
                        safe_to_delete=False,
                        confidence=0.75,
                    )
                )
                total_recovered += recovered
                continue

        # 4. Suggest Archive for old miscellaneous/media files that haven't been accessed
        if access_age_days > 90:
            actions.append(
                CleanupAction(
                    path=path_str,
                    action_type="archive",
                    reasoning="File has not been accessed in over 90 days; move to archive folder.",
                    estimated_space_recovered=0,
                    safe_to_delete=False,
                    confidence=0.70,
                )
            )

    # General reasoning comments
    reasoning_comments.append(
        f"Generated {len(actions)} optimization suggestions. "
        f"Planner is running in dry-run mode: dry_run=True. "
        f"Estimated storage recovery: {total_recovered} bytes. "
        f"Excluded all sensitive and blocked files."
    )

    action_plan = ActionPlan(
        actions=actions,
        reasoning=reasoning_comments,
        estimated_recovery=total_recovered,
        dry_run=True,
    )

    high_level_reasoning = (
        f"Created cleanup plan proposing {len(actions)} action(s) for a "
        f"total recovery of {total_recovered} bytes. Plan is currently a dry-run."
    )

    return OptimizationPlannerOutput(
        action_plan=action_plan,
        reasoning=high_level_reasoning,
    )
