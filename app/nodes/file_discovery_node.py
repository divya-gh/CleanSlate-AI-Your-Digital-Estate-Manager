"""FileDiscoveryNode — ADK 2.0 Graph Workflow Node.

Scans allowed directories recursively, respects blocked paths, and collects
file metadata.  Optionally filters results by a search query.
"""

from __future__ import annotations

import fnmatch
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.nodes.my_pc_assistant_node import MyPCAssistantOutput

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class FolderScopePolicy(BaseModel):
    """Defines which paths the node is allowed (or forbidden) to scan."""

    allowed_paths: list[str] = Field(
        description="List of absolute directory paths the node MAY scan recursively.",
    )
    blocked_paths: list[str] = Field(
        default_factory=list,
        description="List of absolute directory paths the node MUST NOT scan.",
    )
    safe_mode: bool = Field(
        default=False,
        description="Whether weekly organizer safe mode is active.",
    )
    dry_run: bool = Field(
        default=False,
        description="Whether weekly organizer is in dry-run mode.",
    )
    allow_deletes: bool = Field(
        default=True,
        description="Whether deletions are allowed in this flow.",
    )
    allow_compress: bool = Field(
        default=True,
        description="Whether compression is allowed in this flow.",
    )
    allow_archives: bool = Field(
        default=True,
        description="Whether archiving is allowed in this flow.",
    )
    allow_moves: bool = Field(
        default=True,
        description="Whether moving files is allowed in this flow.",
    )
    version: str = Field(
        default="1.0",
        description="Policy version.",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Policy creation timestamp.",
    )
    created_by: str = Field(
        default="FolderScopeNode",
        description="Policy creator.",
    )
    source: str = Field(
        default="interactive_cleanup",
        description="Policy source.",
    )


class FileDiscoveryInput(BaseModel):
    """Input payload consumed by FileDiscoveryNode."""

    folder_scope_policy: FolderScopePolicy
    search_query: str | None = Field(
        default=None,
        description="Optional filename pattern to filter discovered files (case-insensitive glob match).",
    )


class FileMetadata(BaseModel):
    """Metadata collected for a single discovered file."""

    path: str = Field(description="Absolute path to the file.")
    size: int = Field(description="File size in bytes.")
    extension: str = Field(
        description="File extension including the leading dot (e.g. '.txt')."
    )
    last_modified: float = Field(description="Last-modified timestamp (epoch seconds).")
    last_accessed: float = Field(description="Last-accessed timestamp (epoch seconds).")


class FileDiscoveryOutput(BaseModel):
    """Output payload emitted by FileDiscoveryNode."""

    file_inventory: list[FileMetadata] = Field(
        default_factory=list,
        description="List of metadata objects for every discovered file.",
    )
    folder_scope_policy: FolderScopePolicy = Field(
        description="The folder scope policy used for discovery, propagated downstream.",
    )
    reasoning: str = Field(
        description="Human-readable explanation of what the node did and why.",
    )


# ---------------------------------------------------------------------------
# Core scanning logic (pure function — easy to unit-test)
# ---------------------------------------------------------------------------


def _is_blocked(candidate: str, blocked_paths: list[str]) -> bool:
    """Return True if *candidate* falls under any blocked path."""
    candidate_resolved = os.path.normcase(os.path.abspath(candidate))
    for bp in blocked_paths:
        bp_resolved = os.path.normcase(os.path.abspath(bp))
        if candidate_resolved == bp_resolved or candidate_resolved.startswith(
            bp_resolved + os.sep
        ):
            return True
    return False


def _scan_allowed_paths(
    allowed_paths: list[str],
    blocked_paths: list[str],
    search_query: str | None,
) -> tuple[list[FileMetadata], str]:
    """Walk *allowed_paths* and collect file metadata.

    Returns a tuple of (file_inventory, reasoning_text).
    """
    inventory: list[FileMetadata] = []
    scanned_dirs = 0
    skipped_dirs = 0

    for allowed in allowed_paths:
        allowed_abs = os.path.abspath(allowed)

        if not os.path.isdir(allowed_abs):
            continue

        for dirpath, dirnames, filenames in os.walk(allowed_abs, topdown=True):
            # Prune blocked sub-trees in-place so os.walk won't descend into them.
            dirnames[:] = [
                d
                for d in dirnames
                if not _is_blocked(os.path.join(dirpath, d), blocked_paths)
            ]
            scanned_dirs += 1

            for fname in filenames:
                full_path = os.path.join(dirpath, fname)

                # Double-check the file itself isn't under a blocked path.
                if _is_blocked(full_path, blocked_paths):
                    skipped_dirs += 1
                    continue

                # Optional search filter (case-insensitive glob).
                if search_query and not fnmatch.fnmatch(
                    fname.lower(), search_query.lower()
                ):
                    continue

                try:
                    stat = os.stat(full_path)
                except OSError:
                    continue

                ext = Path(full_path).suffix
                inventory.append(
                    FileMetadata(
                        path=full_path,
                        size=stat.st_size,
                        extension=ext,
                        last_modified=stat.st_mtime,
                        last_accessed=stat.st_atime,
                    )
                )

    # Build reasoning summary
    filter_note = (
        f"Applied search filter '{search_query}'."
        if search_query
        else "No search filter applied; all files included."
    )
    reasoning = (
        f"Scanned {scanned_dirs} directories across {len(allowed_paths)} allowed path(s). "
        f"Skipped {skipped_dirs} blocked entries. "
        f"Discovered {len(inventory)} file(s). "
        f"{filter_note}"
    )

    return inventory, reasoning


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def file_discovery_node(
    node_input: Any,
) -> FileDiscoveryOutput:
    """FileDiscoveryNode — scans allowed paths and returns a file inventory.

    This function node follows the ADK 2.0 Workflow convention:
    - Accepts a typed Pydantic input (auto-converted from predecessor output).
    - Returns a typed Pydantic output for downstream consumption.
    """
    if type(node_input).__name__ == "FolderScopeOutput":
        policy = getattr(node_input, "folder_scope_policy", None)
        if not policy:
            raise ValueError("FolderScopePolicy is missing in FolderScopeOutput.")
        node_input = FileDiscoveryInput(
            folder_scope_policy=policy,
            search_query=None,
        )

    if isinstance(node_input, MyPCAssistantOutput):
        if node_input.intent != "search":
            raise ValueError(
                f"FileDiscoveryNode only accepts MyPCAssistantOutput when intent is 'search'. Got: {node_input.intent}"
            )
        q = node_input.search_query
        if not q or not q.strip():
            raise ValueError("search_query must not be empty.")

        q_lower = q.lower()
        blocked_keywords = {
            "system",
            "windows",
            "system32",
            "programdata",
            "appdata",
            "ssn",
            "password",
            "tax",
            "banking",
        }
        if any(kw in q_lower for kw in blocked_keywords):
            raise ValueError("search_query contains blocked system/sensitive keywords.")

        if len(q) > 200:
            raise ValueError("search_query exceeds maximum length of 200 characters.")

        # Construct a default policy allowing the current working directory
        policy = FolderScopePolicy(
            allowed_paths=[os.getcwd()],
            blocked_paths=[],
        )
        node_input = FileDiscoveryInput(
            folder_scope_policy=policy,
            search_query=q,
        )

    policy = node_input.folder_scope_policy
    search_query = node_input.search_query

    # Enforce validation checks on policy
    if not policy.allowed_paths:
        raise ValueError("allowed_paths must not be empty.")

    for ap in policy.allowed_paths:
        # Check path existence without reading contents or following symlinks
        if not os.path.exists(ap):
            raise ValueError(f"Allowed path '{ap}' does not exist.")
        if os.path.islink(ap):
            raise ValueError(
                f"Allowed path '{ap}' is a symbolic link, which is not supported."
            )

        # Check for overlaps with blocked paths
        for bp in policy.blocked_paths:
            if ap == bp or ap.startswith(bp + os.sep):
                raise ValueError(
                    f"Allowed path '{ap}' overlaps with or is inside blocked path '{bp}'."
                )

    inventory, reasoning = _scan_allowed_paths(
        allowed_paths=policy.allowed_paths,
        blocked_paths=policy.blocked_paths,
        search_query=search_query,
    )

    return FileDiscoveryOutput(
        file_inventory=inventory,
        folder_scope_policy=policy,
        reasoning=reasoning,
    )


FolderScopePolicy.model_rebuild()
