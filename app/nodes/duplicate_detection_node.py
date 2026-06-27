"""DuplicateDetectionNode — ADK 2.0 Graph Workflow Node.

Computes fast SHA-256 hashes of discovered files to detect exact duplicates
and uses heuristics (filename, size, extension, parent directory) to detect
near duplicates. Respects folder scope policies.
"""

from __future__ import annotations

import difflib
import hashlib
import os
import uuid
from pathlib import Path

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from pydantic import BaseModel, Field

from app.nodes.classification_node import ClassificationOutput, ClassifiedFile
from app.nodes.file_discovery_node import (
    FileMetadata,
    FolderScopePolicy,
    resolve_real_path,
)

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class DuplicateFileEntry(BaseModel):
    """Details of a file within a duplicate group."""

    path: str = Field(description="Absolute path to the duplicate file.")
    size: int = Field(description="Size in bytes.")
    hash: str = Field(description="SHA-256 hash or empty if hashing skipped.")
    similarity_score: float = Field(
        description="Similarity score (1.0 for exact duplicates, <1.0 for near duplicates)."
    )


class DuplicateGroup(BaseModel):
    """A group of files identified as exact or near duplicates."""

    group_id: str = Field(description="Unique ID for this duplicate group.")
    files: list[DuplicateFileEntry] = Field(description="List of files in the group.")
    reasoning: str = Field(
        description="Explanation of why these files are grouped together."
    )


class DuplicateDetectionOutput(BaseModel):
    """Output payload emitted by DuplicateDetectionNode."""

    duplicate_groups: list[DuplicateGroup] = Field(
        default_factory=list,
        description="List of duplicate groups identified.",
    )
    classified_files: list[ClassifiedFile] = Field(
        default_factory=list,
        description="List of classification results for every file (propagated downstream).",
    )
    file_inventory: list[FileMetadata] = Field(
        default_factory=list,
        description="List of metadata objects for every discovered file (propagated downstream).",
    )
    folder_scope_policy: FolderScopePolicy = Field(
        description="The folder scope policy used for discovery, propagated downstream.",
    )
    reasoning: str = Field(
        description="High-level summary of the duplicate detection run.",
    )
    safe_mode: bool = Field(
        default=False,
        description="Whether safe mode was active during duplicate detection.",
    )
    search_mode: bool = Field(
        default=False,
        description="Whether search mode was active during duplicate detection.",
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _is_path_allowed(path: str, policy: FolderScopePolicy) -> bool:
    """Check if the path is explicitly allowed and not blocked by policy."""
    resolved_path = os.path.normcase(os.path.abspath(path))

    # 1. Check blocked paths
    for bp in policy.blocked_paths:
        bp_resolved = os.path.normcase(os.path.abspath(bp))
        if resolved_path == bp_resolved or resolved_path.startswith(
            bp_resolved + os.sep
        ):
            return False

    # 2. Check allowed paths (must be under at least one allowed path if allowed_paths is not empty)
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


def _compute_sha256(path: str, policy: FolderScopePolicy) -> str:
    """Compute SHA-256 hash of a file locally in chunks.

    Never uploads file contents.
    """
    sha256 = hashlib.sha256()
    try:
        if _is_path_allowed(path, policy):
            with open(resolve_real_path(path), "rb") as f:  # nosemgrep
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        return ""
    except OSError:
        return ""


def _compute_near_duplicate_score(f1: FileMetadata, f2: FileMetadata) -> float:
    """Calculate similarity score between 0.0 and 1.0 based on heuristics:

    - Similar filenames (SequenceMatcher ratio)
    - Similar sizes (within 10% difference)
    - Same extension
    - Same parent folder
    """
    p1, p2 = Path(f1.path), Path(f2.path)

    # 1. Extension must match exactly
    if f1.extension.lower() != f2.extension.lower():
        return 0.0

    # 2. Filename similarity
    filename_sim = difflib.SequenceMatcher(
        None, p1.stem.lower(), p2.stem.lower()
    ).ratio()

    # 3. Size similarity
    if f1.size == 0 and f2.size == 0:
        size_sim = 1.0
    elif f1.size == 0 or f2.size == 0:
        size_sim = 0.0
    else:
        size_sim = 1.0 - (abs(f1.size - f2.size) / max(f1.size, f2.size))

    # 4. Parent directory match
    parent_sim = 1.0 if p1.parent == p2.parent else 0.0

    # Weighted average: filename (45%), size (35%), parent folder (20%)
    score = (0.45 * filename_sim) + (0.35 * size_sim) + (0.20 * parent_sim)
    return score


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def duplicate_detection_node(
    node_input: ClassificationOutput,
) -> DuplicateDetectionOutput:
    """DuplicateDetectionNode — detects exact and near duplicate files.

    Processes file_inventory from predecessor. For each eligible file,
    computes a fast SHA-256 hash to find exact duplicates and evaluates
    heuristics to find near-duplicates.
    """
    inventory = node_input.file_inventory
    policy = node_input.folder_scope_policy

    # Filter files based on folder scope policy
    allowed_files: list[FileMetadata] = []
    skipped_count = 0
    for file in inventory:
        if _is_path_allowed(file.path, policy):
            allowed_files.append(file)
        else:
            skipped_count += 1

    # 1. Exact duplicates: Compute hashes for allowed files
    hashes: dict[str, str] = {}  # path -> hash
    hash_groups: dict[str, list[FileMetadata]] = {}  # hash -> list of files

    for file in allowed_files:
        h = _compute_sha256(file.path, policy)
        if h:
            hashes[file.path] = h
            hash_groups.setdefault(h, []).append(file)

    groups: list[DuplicateGroup] = []
    processed_paths: set[str] = set()

    # Create exact duplicate groups
    for h, files in hash_groups.items():
        if len(files) > 1:
            group_id = str(uuid.uuid4())
            entries = [
                DuplicateFileEntry(
                    path=f.path,
                    size=f.size,
                    hash=h,
                    similarity_score=1.0,
                )
                for f in files
            ]
            for f in files:
                processed_paths.add(f.path)
            groups.append(
                DuplicateGroup(
                    group_id=group_id,
                    files=entries,
                    reasoning=(
                        f"Exact duplicates detected by identical SHA-256 hash: {h[:8]}..."
                    ),
                )
            )

    # 2. Near duplicates: Heuristic matching for remaining files
    remaining_files = [f for f in allowed_files if f.path not in processed_paths]

    # Simple transitive closure clustering for near duplicates
    near_threshold = 0.80
    used_in_near: set[str] = set()

    for i, f1 in enumerate(remaining_files):
        if f1.path in used_in_near:
            continue

        cluster: list[tuple[FileMetadata, float]] = [(f1, 1.0)]
        for f2 in remaining_files[i + 1 :]:
            if f2.path in used_in_near:
                continue

            score = _compute_near_duplicate_score(f1, f2)
            if score >= near_threshold:
                cluster.append((f2, score))

        if len(cluster) > 1:
            group_id = str(uuid.uuid4())
            entries: list[DuplicateFileEntry] = []
            for f, score in cluster:
                h = hashes.get(f.path, "")
                entries.append(
                    DuplicateFileEntry(
                        path=f.path,
                        size=f.size,
                        hash=h,
                        similarity_score=round(score, 3),
                    )
                )
                used_in_near.add(f.path)

            paths_str = ", ".join(Path(f.path).name for f, _ in cluster)
            groups.append(
                DuplicateGroup(
                    group_id=group_id,
                    files=entries,
                    reasoning=(
                        f"Near duplicates detected based on similar metadata for "
                        f"files [{paths_str}] (extension: {cluster[0][0].extension})."
                    ),
                )
            )

    reasoning = (
        f"Processed {len(allowed_files)} allowed file(s). "
        f"Skipped {skipped_count} file(s) outside allowed scope. "
        f"Identified {len(groups)} duplicate group(s) in total. "
        f"No file contents were uploaded."
    )

    output = DuplicateDetectionOutput(
        duplicate_groups=groups,
        classified_files=node_input.classified_files,
        file_inventory=inventory,
        folder_scope_policy=policy,
        safe_mode=node_input.safe_mode,
        search_mode=node_input.search_mode,
        reasoning=reasoning,
    )

    return Event(output=output, actions=EventActions(route="sensitive"))
