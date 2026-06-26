"""FileDiscoveryNode — ADK 2.0 Graph Workflow Node.

Scans allowed directories recursively, respects blocked paths, and collects
file metadata.  Optionally filters results by a search query.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from pydantic import BaseModel, Field

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


def file_discovery_node(node_input: FileDiscoveryInput) -> FileDiscoveryOutput:
    """FileDiscoveryNode — scans allowed paths and returns a file inventory.

    This function node follows the ADK 2.0 Workflow convention:
    - Accepts a typed Pydantic input (auto-converted from predecessor output).
    - Returns a typed Pydantic output for downstream consumption.
    """
    policy = node_input.folder_scope_policy
    search_query = node_input.search_query

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
