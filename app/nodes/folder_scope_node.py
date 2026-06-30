"""FolderScopeNode — ADK 2.0 Graph Workflow Node.

Manages interactive folder scope configuration for CleanSlate AI.
Ensures that allowed and blocked paths are explicitly configured by the user
and validated against strict safety boundaries without disk/OS access.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from typing import Any

from pydantic import model_validator

from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.events.request_input import RequestInput
from pydantic import BaseModel, ConfigDict, Field

from app.nodes.file_discovery_node import FolderScopePolicy

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class FolderScopeInput(BaseModel):
    """Input payload consumed by FolderScopeNode.

    This schema is a strict superset of MyPCAssistantOutput so that ADK's
    internal TypeAdapter.validate_python() can coerce the upstream node's
    output directly into this schema without a model_validator (which ADK
    bypasses when validating model-instance-to-model-instance).

    from_attributes=True (ORM mode) lets Pydantic read the MyPCAssistantOutput
    instance's attributes directly instead of requiring exact type identity.
    The node derives `cleanup_intent` from `intent` at runtime.
    """

    model_config = ConfigDict(from_attributes=True)

    # --- Own fields (may be absent when coming from MyPCAssistantOutput) ---
    cleanup_intent: bool = Field(
        default=False,
        description="Whether cleanup intent has been explicitly detected."
    )
    user_query: str | None = Field(
        default=None, description="The user query associated with this request."
    )
    session_id: str | None = Field(
        default=None, description="Optional session identifier."
    )
    timestamp: datetime | None = Field(
        default=None, description="Timestamp of the query."
    )

    # --- MyPCAssistantOutput passthrough fields (all optional with defaults) ---
    intent: str | None = Field(
        default=None,
        description="Upstream intent from MyPCAssistantNode ('cleanup', 'search', etc.)."
    )
    search_query: str | None = Field(default=None)
    explanation_request: str | None = Field(default=None)
    cleanup_intent_reasoning: str | None = Field(default=None)
    conversational_response: str | None = Field(default=None)
    total_actions: int = Field(default=0)
    successful_actions: int = Field(default=0)
    failed_actions: int = Field(default=0)
    skipped_actions: int = Field(default=0)
    estimated_recovery: int = Field(default=0)
    dry_run: bool = Field(default=False)
    sensitive_files_protected: int = Field(default=0)
    rollback_supported_actions: int = Field(default=0)
    rollback_unsupported_actions: int = Field(default=0)
    human_readable_report: str = Field(default="")
    errors: list[str] | None = Field(default=None)


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

def _get_default_safe_suggestions() -> str:
    """Returns OS-appropriate safe folder suggestions, preferring OneDrive paths on Windows."""
    if os.name == "nt":
        username = os.environ.get("USERNAME") or os.environ.get("USER", "YourName")
        base = f"C:/Users/{username}"
        onedrive_base = f"C:/Users/{username}/OneDrive"

        # Prefer OneDrive paths if they exist (common with Microsoft 365)
        if os.path.isdir(onedrive_base):
            return (
                f"  \u2705  {onedrive_base}/Desktop\n"
                f"  \u2705  {onedrive_base}/Documents\n"
                f"  \u2705  {base}/Downloads\n"
                f"  \u2705  {onedrive_base}/Pictures\n"
                f"  \u2705  {onedrive_base}/Videos"
            )
        return (
            f"  \u2705  {base}/Desktop\n"
            f"  \u2705  {base}/Documents\n"
            f"  \u2705  {base}/Downloads\n"
            f"  \u2705  {base}/Pictures\n"
            f"  \u2705  {base}/Videos"
        )
    else:
        username = os.environ.get("USER", "YourName")
        base = f"/Users/{username}"
        return (
            f"  \u2705  {base}/Desktop\n"
            f"  \u2705  {base}/Documents\n"
            f"  \u2705  {base}/Downloads\n"
            f"  \u2705  {base}/Pictures\n"
            f"  \u2705  {base}/Videos"
        )


def _hash_secret(value: str) -> str:
    """Returns a SHA-256 hex digest of a secret string (no file I/O)."""
    return hashlib.sha256(value.strip().encode()).hexdigest()  # nosemgrep


def _list_subfolders(parent_path: str) -> list[str]:
    """List direct subdirectories of parent_path (metadata-only, max 50).

    Returns a sorted list of absolute paths using forward slashes.
    Never recurses, never reads file contents.
    """
    import json as _json  # noqa: F401 (used by callers via __CHECKBOX_SELECT__ protocol)
    try:
        entries = []
        with os.scandir(parent_path) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    entries.append(entry.path.replace("\\", "/"))
                if len(entries) >= 50:
                    break
        return sorted(entries)
    except (OSError, PermissionError):
        return []


async def folder_scope_node(
    ctx: Context,
    node_input: FolderScopeInput,
) -> Any:
    """FolderScopeNode — full guided organize flow with HITL path, PIN, and weekly organizer setup.

    With rerun_on_resume=True, ADK replays from my_pc_assistant_node (the
    entry node) on every turn.  My_pc_assistant_node captures ctx.resume_inputs
    and stores them in session state via state_delta.  This node reads
    answers from ctx.session.state so multi-turn HITL answers accumulate
    correctly across replays.
    """
    # Read accumulated prior answers from session state.
    # With rerun_on_resume=True, ADK replays from the entry node and passes
    # new_message.text as node_input.user_query.  We use the user's text as
    # the answer for whatever the CURRENT step expects, and persist it.
    ri: dict = {}
    try:
        ri = dict(ctx.session.state)
    except AttributeError:
        pass

    user_answer = (node_input.user_query or "").strip()
    # _was_already_active = True means this is a RESUME turn (the flag existed BEFORE this turn).
    # On the initial "organize my computer" turn, organize_flow_active is set by
    # my_pc_assistant_node's state_delta WITHIN this same run, so it may appear
    # in ri (from session state snapshot), but it shouldn't be treated as a resume.
    # We detect a true resume by checking if any STEP key is still missing AND
    # the flag was already set before this run started.
    _was_already_active = bool(ri.get("organize_flow_active", False))

    # New step order for ORGANIZE_MODE:
    #   parent_folder → subfolder_selections → user_pin →
    #   security_question → security_answer → weekly_organizer
    _STEP_ORDER = ["parent_folder", "subfolder_selections", "user_pin",
                   "security_question", "security_answer", "weekly_organizer"]
    _any_step_missing = any(s not in ri for s in _STEP_ORDER)
    _is_resume_turn = _was_already_active and _any_step_missing and user_answer

    # ------------------------------------------------------------------ #
    # Handle special signals from the UI                                   #
    # ------------------------------------------------------------------ #
    # __RESCAN__ — user clicked "Scan a different folder" in the checkbox widget.
    # Clear path state so step 1 re-asks for a new parent folder.
    if _is_resume_turn and user_answer == "__RESCAN__":
        yield Event(actions=EventActions(state_delta={
            "parent_folder": None,
            "subfolder_selections": None,
        }))
        # Remove from ri so step 1 fires again
        ri.pop("parent_folder", None)
        ri.pop("subfolder_selections", None)
        # Re-show step 1 immediately (fall through, don't count as answered)
        _is_resume_turn = False

    # "use this folder" — user wants to organize the parent folder directly
    # when no subfolders were found; inject a synthetic selection.
    if _is_resume_turn and user_answer.strip().lower() == "use this folder":
        import json as _json_uf
        parent_val = ri.get("parent_folder", "")
        if parent_val and "parent_folder" in ri and "subfolder_selections" not in ri:
            synth = _json_uf.dumps({"organized": [parent_val], "never_touch": []})
            ri["subfolder_selections"] = synth
            yield Event(actions=EventActions(state_delta={"subfolder_selections": synth}))
            _is_resume_turn = False  # synthetic — don't re-advance step order

    # ------------------------------------------------------------------ #
    # CRITICAL: Only persist the ONE newly-answered step per resume turn. #
    # Persisting ALL answered steps on every rerun triggers an infinite   #
    # state_delta cascade (rerun_on_resume fires again each time).        #
    # ------------------------------------------------------------------ #
    if _is_resume_turn:
        for step in _STEP_ORDER:
            if step not in ri:
                ri[step] = user_answer
                # Persist ONLY this new answer — nothing else
                yield Event(actions=EventActions(state_delta={step: user_answer}))
                break

    # Derive cleanup_intent from the upstream 'intent' field if not set directly.
    is_cleanup = node_input.cleanup_intent or node_input.intent == "cleanup"

    if not is_cleanup:
        msg = "Cleanup intent not detected. Folder scope not requested."
        output = FolderScopeOutput(
            folder_scope_policy=None,
            message=msg,
            human_readable_report=msg,
        )
        yield Event(output=output, actions=EventActions(route="scope_invalid"))
        return

    # ------------------------------------------------------------------ #
    # STEP 1 — Ask for the parent folder (with suggestions + blocked list)#
    # ------------------------------------------------------------------ #
    if "parent_folder" not in ri:
        suggestions = _get_default_safe_suggestions()
        system_blocked = _get_default_system_paths()
        blocked_preview = "\n".join(
            f"  \u26d4  {p}" for p in system_blocked[:6]
        ) + ("\n  ... (and more system folders)" if len(system_blocked) > 6 else "")

        username = os.environ.get("USERNAME") or os.environ.get("USER", "YourName")
        example = f"C:/Users/{username}/Downloads" if os.name == "nt" else f"/Users/{username}/Downloads"

        msg = (
            "\U0001f9f9 Great! Let\u2019s get your computer organized safely.\n"
            + "\u2500" * 60 + "\n\n"
            "\U0001f4c2 Suggested safe folders you can organize:\n"
            + suggestions + "\n\n"
            "\u26d4 Automatically blocked (system folders \u2014 never touched):\n"
            + blocked_preview + "\n\n"
            "\U0001f512 Sensitive files found during cleanup will be moved to\n"
            "   your secure Authenticated folder automatically.\n\n"
            + "\u2500" * 60 + "\n"
            "Please type the folder you want me to organize\n"
            f"(e.g. C:/Users/{username}/Desktop \u2014 I\u2019ll list its sub-folders so you can pick which ones to clean):"
        )
        yield RequestInput(interrupt_id="parent_folder", message=msg)
        return

    # ------------------------------------------------------------------ #
    # STEP 2 — List subfolders → send checkbox widget                    #
    # ------------------------------------------------------------------ #
    if "subfolder_selections" not in ri:
        import json as _json
        parent = ri["parent_folder"].strip().replace("\\", "/").rstrip("/")

        # Validate the parent path first
        try:
            _validate_single_path(parent, is_allowed=True)
        except ValueError as e:
            yield Event(
                output=FolderScopeOutput(
                    folder_scope_policy=None,
                    message="Invalid folder path.",
                    human_readable_report=f"\u26a0\ufe0f  Invalid path: {e}\nPlease enter a valid absolute path.",
                ),
                actions=EventActions(route="scope_invalid", state_delta={"parent_folder": None}),
            )
            yield RequestInput(
                interrupt_id="parent_folder",
                message=f"\u26a0\ufe0f  Invalid path: {e}\n\nPlease type a valid absolute folder path:",
            )
            return

        subfolders = _list_subfolders(parent)

        if not subfolders:
            # No subfolders at all — use the folder itself as the single target,
            # but first ask the user if they want to re-enter a different path.
            username = os.environ.get("USERNAME") or os.environ.get("USER", "YourName")
            onedrive_hint = ""
            if os.name == "nt" and "onedrive" not in parent.lower():
                onedrive_base = f"C:/Users/{username}/OneDrive"
                if os.path.isdir(onedrive_base):
                    onedrive_hint = (
                        f"\n\n\U0001f4a1 Tip: Your OneDrive folders are at:\n"
                        f"   {onedrive_base}/Desktop\n"
                        f"   {onedrive_base}/Documents"
                    )
            retry_msg = (
                f"\U0001f4c2 No sub-folders found inside:\n   {parent}\n\n"
                "This folder has no sub-folders to select from. You can:\n"
                f"  \u2022 Type a DIFFERENT parent path to scan its sub-folders"
                + onedrive_hint + "\n"
                f"  \u2022 Or type \"use this folder\" to organize {parent} directly"
            )
            # Clear parent_folder so the user can re-enter
            yield Event(actions=EventActions(state_delta={"parent_folder": None}))
            yield RequestInput(interrupt_id="parent_folder", message=retry_msg)
            return
        else:
            # Emit __CHECKBOX_SELECT__ so the chat UI renders interactive checkboxes.
            # Include the count so the UI can show it.
            checkbox_payload = _json.dumps({
                "parent": parent,
                "subfolders": subfolders,
                "count": len(subfolders),
            })
            msg = (
                "__CHECKBOX_SELECT__\n"
                + checkbox_payload + "\n"
                "Select which folders to organize and which to leave untouched:"
            )
            yield RequestInput(interrupt_id="subfolder_selections", message=msg)
            return

    # ------------------------------------------------------------------ #
    # Parse subfolder_selections → derive organize & never_touch lists   #
    # ------------------------------------------------------------------ #
    import json as _json2
    selections_raw = ri.get("subfolder_selections", "{}")
    try:
        if isinstance(selections_raw, str) and selections_raw.startswith("{"):
            sel = _json2.loads(selections_raw)
        else:
            sel = {"organized": [selections_raw], "never_touch": []}
    except Exception:
        sel = {"organized": [], "never_touch": []}

    norm_allowed: list[str] = []
    norm_blocked: list[str] = []
    errors: list[str] = []

    for ap in sel.get("organized", []):
        try:
            cleaned = _validate_single_path(ap, is_allowed=True)
            if cleaned not in norm_allowed:
                norm_allowed.append(cleaned)
        except ValueError as e:
            errors.append(f"Folder '{ap}' is invalid: {e!s}")

    for bp in sel.get("never_touch", []):
        try:
            cleaned = _validate_single_path(bp, is_allowed=False)
            if cleaned not in norm_blocked:
                norm_blocked.append(cleaned)
        except ValueError as e:
            errors.append(f"Blocked folder '{bp}' is invalid: {e!s}")

    if not norm_allowed:
        errors.append("You must select at least one folder to organize.")

    if errors:
        hr_message = (
            "\u26a0\ufe0f  We found some issues:\n"
            + "\n".join(f"  \u2022 {err}" for err in errors)
        )
        yield Event(
            output=FolderScopeOutput(
                folder_scope_policy=None,
                message="Validation failed.",
                validation_errors=errors,
                human_readable_report=hr_message,
            ),
            actions=EventActions(route="scope_invalid", state_delta={"subfolder_selections": None}),
        )
        return

    # Merge in default system blocked paths
    default_system = _get_default_system_paths()
    agent_internal = _get_agent_internal_blocked_paths()
    for ib in default_system + agent_internal:
        if ib not in norm_blocked:
            norm_blocked.append(ib)

    # ------------------------------------------------------------------ #
    # STEP 3 — Create a 4-digit PIN                                      #
    # ------------------------------------------------------------------ #
    if "user_pin" not in ri:
        msg = (
            "\U0001f511 Security Setup\n"
            "\u2500" * 60 + "\n\n"
            "Please create a 4-digit PIN to protect access to your\n"
            "authenticated secure folder.\n\n"
            "Your PIN will be stored securely (hashed) and never shown again.\n\n"
            "Enter your 4-digit PIN (digits only, e.g. 1234):"
        )
        yield RequestInput(interrupt_id="user_pin", message=msg)
        return

    # Validate PIN
    pin_raw = str(ri["user_pin"]).strip()
    if not re.fullmatch(r"\d{4}", pin_raw):
        yield Event(
            output=FolderScopeOutput(
                folder_scope_policy=None,
                message="Invalid PIN.",
                human_readable_report="\u26a0\ufe0f  Invalid PIN. A PIN must be exactly 4 digits (0\u20139).",
            ),
            actions=EventActions(
                route="scope_invalid",
                state_delta={"user_pin": None},
            ),
        )
        yield RequestInput(
            interrupt_id="user_pin",
            message="\u26a0\ufe0f  Invalid PIN. A PIN must be exactly 4 digits (0\u20139).\nPlease try again:",
        )
        return

    # ------------------------------------------------------------------ #
    # STEP 4 — Security question                                          #
    # ------------------------------------------------------------------ #
    _security_questions = [
        "What is the name of your first pet?",
        "What was the name of your elementary school?",
        "What is your mother's maiden name?",
        "What city were you born in?",
        "What was the make of your first car?",
    ]

    if "security_question" not in ri:
        numbered = "\n".join(f"  {i + 1}. {q}" for i, q in enumerate(_security_questions))
        msg = (
            "\U0001f513 Security Question\n"
            "\u2500" * 60 + "\n\n"
            "Choose a security question so you can recover your PIN later:\n\n"
            + numbered + "\n\n"
            "Type the NUMBER of your chosen question (1\u20135):"
        )
        yield RequestInput(interrupt_id="security_question", message=msg)
        return

    sq_raw = str(ri["security_question"]).strip()
    sq_index: int | None = None
    for i in range(1, 6):
        if sq_raw.startswith(str(i)):
            sq_index = i - 1
            break
    if sq_index is None:
        yield Event(
            output=FolderScopeOutput(
                folder_scope_policy=None,
                message="Invalid security question selection.",
                human_readable_report="\u26a0\ufe0f  Please enter a number 1\u20135.",
            ),
            actions=EventActions(
                route="scope_invalid",
                state_delta={"security_question": None},
            ),
        )
        yield RequestInput(
            interrupt_id="security_question",
            message="\u26a0\ufe0f  Please enter a number 1\u20135 to choose your security question:",
        )
        return

    chosen_question = _security_questions[sq_index]

    if "security_answer" not in ri:
        msg = (
            f"\U0001f4dd Your security question:\n   \"{chosen_question}\"\n\n"
            "Please type your answer (case-insensitive, stored securely):"
        )
        yield RequestInput(interrupt_id="security_answer", message=msg)
        return

    # ------------------------------------------------------------------ #
    # STEP 5 — Weekly Organizer — render a toggle button widget          #
    # ------------------------------------------------------------------ #
    if "weekly_organizer" not in ri:
        import json as _json3
        toggle_payload = _json3.dumps({
            "question": "\U0001f4c5 Enable the Weekly Organizer?",
            "description": "Automatically clean up your chosen folders once a week.",
            "options": [
                {"label": "\u2705 Enable Weekly Organizer", "value": "enable"},
                {"label": "\u274c Disable for now",        "value": "disable"},
            ],
        })
        msg = "__TOGGLE_SELECT__\n" + toggle_payload
        yield RequestInput(interrupt_id="weekly_organizer", message=msg)
        return

    weekly_raw = str(ri["weekly_organizer"]).strip().lower()
    weekly_enabled = weekly_raw in ("enable", "yes", "y", "on", "true", "1")

    # ------------------------------------------------------------------ #
    # All steps complete — build policy and store session state          #
    # ------------------------------------------------------------------ #
    pin_hash = _hash_secret(pin_raw)
    answer_hash = _hash_secret(str(ri["security_answer"]))

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

    weekly_status = "\U0001f7e2 Enabled" if weekly_enabled else "\U0001f534 Disabled"
    success_msg = (
        "\u2705 Setup complete! Here\u2019s your configuration summary:\n"
        "\u2500" * 60 + "\n\n"
        f"\U0001f4c2 Folders to organize ({len(norm_allowed)}):\n"
        + "\n".join(f"  \u2022 {p}" for p in norm_allowed) + "\n\n"
        f"\U0001f511 PIN protected: Yes (stored securely)\n"
        f"\U0001f513 Security question: {chosen_question}\n"
        f"\U0001f4c5 Weekly Organizer: {weekly_status}\n\n"
        "Starting scan now\u2026"
    )

    output = FolderScopeOutput(
        folder_scope_policy=policy,
        message=success_msg,
        human_readable_report=success_msg,
    )

    yield Event(
        output=output,
        actions=EventActions(
            route="scope_ok",
            state_delta={
                "pin_hash": pin_hash,
                "security_question": chosen_question,
                "security_answer_hash": answer_hash,
                "weekly_organizer_enabled": weekly_enabled,
                "organize_flow_active": False,  # clear flag — flow complete
            },
        ),
    )
