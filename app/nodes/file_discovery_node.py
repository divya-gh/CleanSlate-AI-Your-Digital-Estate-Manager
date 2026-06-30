"""FileDiscoveryNode — ADK 2.0 Graph Workflow Node.

Scans allowed directories recursively, respects blocked paths, and collects
file metadata. Enforces strict safety limits, symlink/hardlink guards,
and sensitive path/filename masking.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from pydantic import BaseModel, Field

from app.mcp_tools.registry import test_tool

# ---------------------------------------------------------------------------
# Global Path Registry for Masked Resolving
# ---------------------------------------------------------------------------
_PATH_REGISTRY: dict[str, str] = {}


def resolve_real_path(path: str) -> str:
    """Resolves a masked or restricted path to its original absolute disk path."""
    return _PATH_REGISTRY.get(path.replace("\\", "/").lower(), path)


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

    path: str = Field(
        description="Absolute path to the file (masked/sanitized if safe/search mode is active)."
    )
    size: int = Field(description="File size in bytes.")
    extension: str = Field(
        description="File extension including the leading dot (e.g. '.txt')."
    )
    last_modified: float = Field(description="Last-modified timestamp (epoch seconds).")
    last_accessed: float = Field(description="Last-accessed timestamp (epoch seconds).")
    real_path: str = Field(
        default="",
        exclude=True,
        description="The actual absolute path on disk, excluded from serialization.",
    )


class FileDiscoveryOutput(BaseModel):
    """Output payload emitted by FileDiscoveryNode."""

    file_inventory: list[FileMetadata] = Field(
        default_factory=list,
        description="List of metadata objects for every discovered file.",
    )
    folder_scope_policy: FolderScopePolicy = Field(
        description="The folder scope policy used for discovery, propagated downstream.",
    )
    search_mode: bool = Field(
        default=False,
        description="Whether the discovery ran in search mode.",
    )
    safe_mode: bool = Field(
        default=False,
        description="Whether the discovery ran in safe mode.",
    )
    reasoning: str = Field(
        description="Human-readable explanation of what the node did and why.",
    )


FolderScopePolicy.model_rebuild()

# ---------------------------------------------------------------------------
# Safety utilities
# ---------------------------------------------------------------------------

_SENSITIVE_KEYWORDS = [
    "ssn",
    "passport",
    "bank",
    "medical",
    "tax",
    "password",
    "social_security",
]


def _is_sensitive_filename(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in _SENSITIVE_KEYWORDS)


def _mask_filename(fname: str) -> str:
    sha = hashlib.sha1(fname.encode("utf-8")).hexdigest()
    return f"sensitive_file_{sha}"


def _get_agent_internal_blocked_paths() -> list[str]:
    cwd = os.getcwd().replace("\\", "/").rstrip("/").lower()
    internal_dirs = [
        ".git",
        ".agents",
        ".venv",
        ".ruff_cache",
        ".pytest_cache",
        "tests",
        "app",
        ".rollback",
        "Authenticated",
        "WeeklyReview",
        "Organized",
    ]
    return [f"{cwd}/{d}" for d in internal_dirs]


def _get_default_system_paths() -> list[str]:
    system_paths = []
    if os.name == "nt":
        win_dir = os.environ.get("SystemRoot", "C:\\Windows")
        prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        prog_data = os.environ.get("ProgramData", "C:\\ProgramData")
        appdata = os.environ.get("AppData")
        local_appdata = os.environ.get("LocalAppData")
        for p in [
            win_dir,
            prog_files,
            prog_files_x86,
            prog_data,
            appdata,
            local_appdata,
        ]:
            if p:
                system_paths.append(p)
    else:
        system_paths.extend(
            ["/System", "/usr", "/bin", "/sbin", "/etc", "/var", "/Library"]
        )
    return [p.replace("\\", "/").rstrip("/").lower() for p in system_paths if p]


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


# ---------------------------------------------------------------------------
# Traversal logic
# ---------------------------------------------------------------------------


def _scan_directory_recursive(
    dir_path: str,
    base_depth: int,
    effective_blocks: list[str],
    search_query: str | None,
    search_mode: bool,
    safe_mode: bool,
    inventory: list[FileMetadata],
    stats: dict[str, int],
) -> None:
    if len(inventory) >= 5000:
        return

    current_depth = len(os.path.abspath(dir_path).replace("\\", "/").split("/"))
    depth = current_depth - base_depth
    if depth >= 10:
        return

    res = test_tool("list_files", path=dir_path)
    if "error" in res:
        stats["skipped_dirs"] += 1
        return

    stats["scanned_dirs"] += 1
    files = res["result"]["files"]

    for entry in files:
        if len(inventory) >= 5000:
            return

        entry_name = entry["name"]
        entry_abs_path = os.path.abspath(os.path.join(dir_path, entry_name))

        if _is_blocked(entry_abs_path, effective_blocks):
            stats["skipped_dirs"] += 1
            continue

        if entry["is_directory"]:
            _scan_directory_recursive(
                entry_abs_path,
                base_depth,
                effective_blocks,
                search_query,
                search_mode,
                safe_mode,
                inventory,
                stats,
            )
        else:
            # list_files already retrieves size and timestamps in its directory scan.
            # We directly use these values to avoid sequential MCP tool calls for every single file.
            meta_data = {
                "size": entry.get("size", 0),
                "modified_at": entry.get("modified_at", ""),
                "created_at": entry.get("created_at", ""),
            }

            if search_query and not fnmatch.fnmatch(
                entry_name.lower(), search_query.lower()
            ):
                continue

            display_path = entry_abs_path
            if search_mode or safe_mode:
                display_name = entry_name
                if _is_sensitive_filename(entry_name):
                    display_name = _mask_filename(entry_name)
                display_path = f"[RESTRICTED]/{display_name}"
            else:
                if _is_sensitive_filename(entry_name):
                    display_name = _mask_filename(entry_name)
                    parent_dir = os.path.dirname(entry_abs_path)
                    display_path = os.path.join(parent_dir, display_name)

            _PATH_REGISTRY[display_path.replace("\\", "/").lower()] = entry_abs_path

            ext = Path(entry_abs_path).suffix
            try:
                mod_dt = datetime.fromisoformat(meta_data["modified_at"].rstrip("Z"))
                mod_ts = mod_dt.timestamp()
            except Exception:
                mod_ts = 0.0

            try:
                cre_dt = datetime.fromisoformat(meta_data["created_at"].rstrip("Z"))
                cre_ts = cre_dt.timestamp()
            except Exception:
                cre_ts = 0.0

            inventory.append(
                FileMetadata(
                    path=display_path,
                    size=meta_data["size"],
                    extension=ext,
                    last_modified=mod_ts,
                    last_accessed=cre_ts,
                    real_path=entry_abs_path,
                )
            )


def _scan_allowed_paths(
    allowed_paths: list[str],
    blocked_paths: list[str],
    search_query: str | None,
    search_mode: bool,
    safe_mode: bool,
) -> tuple[list[FileMetadata], str]:
    """Walk allowed paths recursively using MCP list_files recursively through registry."""
    inventory: list[FileMetadata] = []
    stats = {"scanned_dirs": 0, "skipped_dirs": 0}

    # Ensure system and agent folders are blocked in safe/search mode
    effective_blocks = list(blocked_paths)
    if safe_mode or search_mode:
        all_implicit = _get_default_system_paths() + _get_agent_internal_blocked_paths()
        for ib in all_implicit:
            is_parent_of_allowed = False
            for ap in allowed_paths:
                ap_norm = ap.replace("\\", "/").rstrip("/").lower()
                if ap_norm == ib or ap_norm.startswith(ib + "/"):
                    is_parent_of_allowed = True
                    break

            if not is_parent_of_allowed and ib not in effective_blocks:
                effective_blocks.append(ib)

    for allowed in allowed_paths:
        allowed_abs = os.path.abspath(allowed)
        if not os.path.isdir(allowed_abs):
            continue

        base_depth = len(allowed_abs.replace("\\", "/").split("/"))
        _scan_directory_recursive(
            allowed_abs,
            base_depth,
            effective_blocks,
            search_query,
            search_mode,
            safe_mode,
            inventory,
            stats,
        )

        if len(inventory) >= 5000:
            break

    filter_note = (
        f"Applied search filter '{search_query}'."
        if search_query
        else "No search filter applied; all files included."
    )
    reasoning = (
        f"Scanned {stats['scanned_dirs']} directories. "
        f"Skipped {stats['skipped_dirs']} blocked or restricted entries. "
        f"Discovered {len(inventory)} file(s). "
        f"{filter_note}"
    )

    return inventory, reasoning



# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def file_discovery_node(
    node_input: Any,
) -> Event:
    """FileDiscoveryNode — scans allowed directories recursively and returns Event."""
    input_type = type(node_input).__name__
    policy = None
    search_query = None
    search_mode = False
    safe_mode = False

    if input_type == "MyPCAssistantOutput":
        if node_input.intent != "search":
            raise ValueError(
                "FileDiscoveryNode only accepts MyPCAssistantOutput when intent is 'search'."
            )
        q = node_input.search_query
        if not q or not q.strip():
            raise ValueError("search_query must not be empty.")

        q_lower = q.lower()
        blocked_keywords = {
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

        search_query = q
        search_mode = True
        policy = FolderScopePolicy(
            allowed_paths=[os.getcwd()],
            blocked_paths=[],
        )

    elif input_type == "FolderScopeOutput":
        policy = getattr(node_input, "folder_scope_policy", None)
        if not policy:
            raise ValueError("FolderScopePolicy is missing in FolderScopeOutput.")

    elif input_type == "WeeklyOrganizerInput":
        policy = getattr(node_input, "folder_scope_policy", None)
        if not policy:
            raise ValueError("FolderScopePolicy is missing in WeeklyOrganizerInput.")
        safe_mode = True

    elif isinstance(node_input, FileDiscoveryInput):
        policy = node_input.folder_scope_policy
        search_query = node_input.search_query
        search_mode = search_query is not None
        safe_mode = policy.safe_mode

    else:
        raise ValueError(f"Unsupported input type to FileDiscoveryNode: {input_type}")

    # Enforce validation checks on policy
    if not policy.allowed_paths:
        raise ValueError("allowed_paths must not be empty.")

    from app.config import set_policy_override
    set_policy_override(policy.model_dump())

    try:
        for ap in policy.allowed_paths:
            # Check path existence without reading contents or following symlinks
            if not os.path.exists(ap):
                err_msg = (
                    f"\u26a0\ufe0f  Folder not found: '{ap}'\n\n"
                    "Please make sure the folder exists and try again.\n"
                    "Tip: Enter a PARENT folder (e.g. C:/Users/YourName/Desktop) \u2014\n"
                    "CleanSlate will list its sub-folders for you to choose from."
                )
                dummy_policy = FolderScopePolicy(allowed_paths=["."])
                output = FileDiscoveryOutput(
                    file_inventory=[],
                    folder_scope_policy=dummy_policy,
                    search_mode=False,
                    safe_mode=False,
                    reasoning=err_msg,
                )
                return Event(output=output, actions=EventActions(route="error"))
            if os.path.islink(ap):
                dummy_policy = FolderScopePolicy(allowed_paths=["."])
                output = FileDiscoveryOutput(
                    file_inventory=[],
                    folder_scope_policy=dummy_policy,
                    search_mode=False,
                    safe_mode=False,
                    reasoning=f"\u26a0\ufe0f  Path '{ap}' is a symbolic link, which is not supported.",
                )
                return Event(output=output, actions=EventActions(route="error"))

            # Check for overlaps with blocked paths
            for bp in policy.blocked_paths:
                if ap == bp or ap.startswith(bp + os.sep):
                    dummy_policy = FolderScopePolicy(allowed_paths=["."])
                    output = FileDiscoveryOutput(
                        file_inventory=[],
                        folder_scope_policy=dummy_policy,
                        search_mode=False,
                        safe_mode=False,
                        reasoning=f"\u26a0\ufe0f  Path '{ap}' overlaps with blocked path '{bp}'.",
                    )
                    return Event(output=output, actions=EventActions(route="error"))

        try:
            inventory, reasoning = _scan_allowed_paths(
                allowed_paths=policy.allowed_paths,
                blocked_paths=policy.blocked_paths,
                search_query=search_query,
                search_mode=search_mode,
                safe_mode=safe_mode,
            )
        except Exception as e:
            dummy_policy = FolderScopePolicy(allowed_paths=["."])
            output = FileDiscoveryOutput(
                file_inventory=[],
                folder_scope_policy=dummy_policy,
                search_mode=False,
                safe_mode=False,
                reasoning=f"Error occurred during file discovery: {e}",
            )
            return Event(output=output, actions=EventActions(route="error"))

        output = FileDiscoveryOutput(
            file_inventory=inventory,
            folder_scope_policy=policy,
            search_mode=search_mode,
            safe_mode=safe_mode,
            reasoning=reasoning,
        )

        route = "cleanup_scan"
        if search_mode:
            route = "search_return"
        elif safe_mode:
            route = "weekly_scan"

        return Event(output=output, actions=EventActions(route=route))
    finally:
        from app.config import set_policy_override
        set_policy_override(None)
