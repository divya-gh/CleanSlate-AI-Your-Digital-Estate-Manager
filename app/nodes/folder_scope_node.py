"""FolderScopeNode — ADK 2.0 Graph Workflow Node.

Manages interactive folder scope configuration for CleanSlate AI.
Ensures that allowed and blocked paths are explicitly configured by the user
and validated against strict safety boundaries without disk/OS access.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.events.request_input import RequestInput
from pydantic import BaseModel, Field

from app.nodes.file_discovery_node import FolderScopePolicy

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class FolderScopeInput(BaseModel):
    """Input payload consumed by FolderScopeNode."""

    cleanup_intent: bool = Field(
        description="Whether cleanup intent has been explicitly detected."
    )
    user_query: str | None = Field(
        default=None, description="The user query associated with this request."
    )
    session_id: str | None = Field(
        default=None, description="Optional session identifier."
    )
    timestamp: datetime | None = Field(
        default_factory=datetime.utcnow, description="Timestamp of the query."
    )


class FolderScopeOutput(BaseModel):
    """Output payload emitted by FolderScopeNode."""

    folder_scope_policy: FolderScopePolicy | None = Field(
        default=None,
        description="The constructed folder scope policy, if cleanup is requested.",
    )
    message: str = Field(description="conversational or status message.")
    validation_errors: list[str] | None = Field(
        default=None, description="Detailed user-friendly validation errors."
    )

    # SummaryOutput compatibility fields (so the UI can render conversational fallback)
    total_actions: int = Field(default=0, description="Summary compatibility.")
    successful_actions: int = Field(default=0, description="Summary compatibility.")
    failed_actions: int = Field(default=0, description="Summary compatibility.")
    skipped_actions: int = Field(default=0, description="Summary compatibility.")
    estimated_recovery: int = Field(default=0, description="Summary compatibility.")
    dry_run: bool = Field(default=False, description="Summary compatibility.")
    sensitive_files_protected: int = Field(
        default=0, description="Summary compatibility."
    )
    rollback_supported_actions: int = Field(
        default=0, description="Summary compatibility."
    )
    rollback_unsupported_actions: int = Field(
        default=0, description="Summary compatibility."
    )
    human_readable_report: str = Field(default="", description="Summary compatibility.")
    errors: list[str] | None = Field(default=None, description="Summary compatibility.")


# ---------------------------------------------------------------------------
# Safety lists & path checks (String normalization only — no disk scanning)
# ---------------------------------------------------------------------------

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
    "system",
    "library",
}


def _get_default_system_paths() -> list[str]:
    """Generates cross-platform default system directories based on env and defaults."""
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

    # Normalize slashes & casing (lowercase)
    normalized = []
    for p in system_paths:
        norm = p.replace("\\", "/").rstrip("/").lower()
        if norm and norm not in normalized:
            normalized.append(norm)
    return normalized


def _get_agent_internal_blocked_paths() -> list[str]:
    """Generates internal agent and cleanup folders relative to current working directory."""
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


def _normalize_path_string(path: str) -> str:
    """Performs strict string-only path normalization without disk or OS access."""
    s = path.strip().replace("\\", "/").rstrip("/")
    if not s:
        return "/"
    return s.lower()


def _validate_single_path(path: str, is_allowed: bool) -> str:
    """Validates single path format and checks against system components list."""
    s = path.strip()
    if not s:
        raise ValueError("The path entry must not be empty.")

    # Check for variables
    if "%" in s or "$" in s:
        raise ValueError(
            "Paths must not contain environment variables (e.g. %APPDATA% or $HOME)."
        )

    # Check for wildcards
    if "*" in s or "?" in s:
        raise ValueError("Paths must not contain wildcards.")

    # Check for directory traversal
    normalized_slashes = s.replace("\\", "/")
    parts = normalized_slashes.split("/")
    if ".." in parts or "." in parts:
        raise ValueError(
            "Paths must not contain parent directory traversal ('.') or ('..')."
        )

    # Must be absolute path
    is_absolute = False
    if normalized_slashes.startswith("/"):
        is_absolute = True
    elif len(normalized_slashes) >= 2 and normalized_slashes[1] == ":":
        if len(normalized_slashes) == 2 or normalized_slashes[2] == "/":
            is_absolute = True

    if not is_absolute:
        raise ValueError(
            "Paths must be absolute (e.g. starting with C:/ on Windows or / on Unix)."
        )

    cleaned = _normalize_path_string(s)

    # Allowed paths specific system checks
    if is_allowed:
        # Check system directory bounds
        system_paths = _get_default_system_paths()
        for sp in system_paths:
            if cleaned == sp:
                raise ValueError(f"Path matches the protected system folder '{path}'.")
            if cleaned.startswith(sp + "/"):
                raise ValueError(
                    f"Path is inside the protected system folder '{path}'."
                )
            if sp.startswith(cleaned + "/"):
                raise ValueError(
                    f"Path contains or is a parent of the protected system folder '{path}'."
                )

        # Check path parts
        for part in cleaned.split("/"):
            if part in _SYSTEM_COMPONENTS:
                raise ValueError(f"Path contains protected system component '{part}'.")

    return cleaned


def _parse_paths(input_val: Any) -> list[str]:
    """Splits comma/newline-separated strings or formats list values."""
    if not input_val:
        return []
    if isinstance(input_val, list):
        return [str(item).strip() for item in input_val if str(item).strip()]
    if isinstance(input_val, str):
        parts = []
        for p in re.split(r",|\n", input_val):
            p_strip = p.strip().strip("'\"")
            if p_strip:
                parts.append(p_strip)
        return parts
    return []


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node (HITL / Resumable Async Generator)
# ---------------------------------------------------------------------------


async def folder_scope_node(
    ctx: Context,
    node_input: FolderScopeInput,
) -> Any:
    """FolderScopeNode — handles interactive allowed and blocked folder setup."""
    if not node_input.cleanup_intent:
        msg = "Cleanup intent not detected. Folder scope not requested."
        output = FolderScopeOutput(
            folder_scope_policy=None,
            message=msg,
            human_readable_report=msg,
        )
        yield Event(output=output, actions=EventActions(route=None))
        return

    # Check for allowed_paths in resume_inputs
    if not ctx.resume_inputs or "allowed_paths" not in ctx.resume_inputs:
        msg = (
            "Please enter the folders you allow the assistant to scan, separated by commas.\n"
            "Examples of safe folders:\n"
            "  Windows: C:\\Users\\YourName\\Desktop, C:\\Users\\YourName\\Documents, C:\\Users\\YourName\\Downloads\n"
            "  Mac/Linux: /Users/YourName/Desktop, /Users/YourName/Documents\n"
            "WARNING: Do not include system folders (e.g., C:\\Windows or C:\\Program Files) as they are protected."
        )
        yield RequestInput(
            interrupt_id="allowed_paths",
            message=msg,
        )
        return

    # Check for blocked_paths in resume_inputs
    if "blocked_paths" not in ctx.resume_inputs:
        msg = (
            "Please enter any folders the assistant must never touch (comma-separated).\n"
            "Note: System folders and agent internal folders are blocked automatically."
        )
        yield RequestInput(
            interrupt_id="blocked_paths",
            message=msg,
        )
        return

    # Extract raw inputs
    raw_allowed = ctx.resume_inputs["allowed_paths"]
    raw_blocked = ctx.resume_inputs["blocked_paths"]

    allowed_list = _parse_paths(raw_allowed)
    blocked_list = _parse_paths(raw_blocked)

    errors: list[str] = []
    norm_allowed: list[str] = []
    norm_blocked: list[str] = []

    # Validate allowed paths
    if not allowed_list:
        errors.append("You must specify at least one allowed path.")
    else:
        for ap in allowed_list:
            try:
                cleaned = _validate_single_path(ap, is_allowed=True)
                if cleaned not in norm_allowed:
                    norm_allowed.append(cleaned)
            except ValueError as e:
                errors.append(f"Allowed path '{ap}' is invalid: {e!s}")

    # Validate blocked paths
    for bp in blocked_list:
        try:
            cleaned = _validate_single_path(bp, is_allowed=False)
            if cleaned not in norm_blocked:
                norm_blocked.append(cleaned)
        except ValueError as e:
            errors.append(f"Blocked path '{bp}' is invalid: {e!s}")

    # Handle duplicates/overlap checks
    if not errors:
        # Populate implicit system blocked paths & internal folders
        default_system = _get_default_system_paths()
        agent_internal = _get_agent_internal_blocked_paths()
        all_implicit_blocks = default_system + agent_internal

        for ib in all_implicit_blocks:
            if ib not in norm_blocked:
                norm_blocked.append(ib)

        # Check allowed path overlap with blocked paths
        for ap in norm_allowed:
            for bp in norm_blocked:
                if ap == bp or ap.startswith(bp + "/"):
                    errors.append(
                        f"Allowed path '{ap}' overlaps with or is inside blocked/system path '{bp}'."
                    )

    # If validation errors occur, clear the invalid fields and re-prompt
    if errors:
        # Human-friendly prefix
        hr_message = (
            "We found some issues with your configured folders. Please fix the following errors:\n"
            + "\n".join(f" - {err}" for err in errors)
        )
        output = FolderScopeOutput(
            folder_scope_policy=None,
            message="Validation failed.",
            validation_errors=errors,
            human_readable_report=hr_message,
        )

        # Clear only invalid fields in ctx.resume_inputs to support correction
        # If allowed_list had errors, clear it.
        has_allowed_errors = any(
            "Allowed path" in err or "allowed path" in err for err in errors
        )
        has_blocked_errors = any("Blocked path" in err for err in errors)

        if has_allowed_errors:
            ctx.resume_inputs.pop("allowed_paths", None)
        if has_blocked_errors:
            ctx.resume_inputs.pop("blocked_paths", None)

        yield Event(output=output, actions=EventActions(route="scope_invalid"))
        return

    # Construct the validated policy
    now = datetime.utcnow()
    policy = FolderScopePolicy(
        allowed_paths=norm_allowed,
        blocked_paths=norm_blocked,
        safe_mode=False,
        dry_run=False,
        allow_deletes=True,
        allow_moves=True,
        allow_archives=True,
        allow_compress=True,
        version="1.0",
        created_at=now,
        created_by="FolderScopeNode",
        source="interactive_cleanup",
    )

    success_msg = f"Folder scope successfully configured. Allowed: {len(norm_allowed)} | Blocked: {len(norm_blocked)}"
    output = FolderScopeOutput(
        folder_scope_policy=policy,
        message=success_msg,
        human_readable_report=success_msg,
    )

    yield Event(output=output, actions=EventActions(route="scope_ok"))
