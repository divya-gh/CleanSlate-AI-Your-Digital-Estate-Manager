import json
import os
from datetime import UTC, datetime

LOG_PATH = os.environ.get("CLEANSLATE_LOG_PATH", "logs/audit.log")


def log_action(
    node: str,
    action_type: str,
    path: str | None,
    is_sensitive: bool,
    hitl_status: str,
    result: str,
    reason: str | None = None,
    rollback_supported: bool | None = None,
    rollback_enabled: bool | None = None,
    approved_actions_count: int | None = None,
    rejected_actions_count: int | None = None,
    hitl_required: bool | None = None,
    backup_path: str | None = None,
    rollback_reason: str | None = None,
    plan_id: str | None = None,
    session_id: str | None = None,
    safety_override_reason: str | None = None,
) -> None:
    """Logs structured audit events to a JSONL format securely, redacting absolute paths."""
    timestamp = datetime.now(UTC).isoformat()

    # Path redaction rules
    # 1. Sensitive files must be completely masked to "<sensitive file>"
    # 2. Non-sensitive files must only reveal parent folder + basename (never absolute paths)
    if is_sensitive:
        redacted_path = "<sensitive file>"
    elif path:
        # Normalize and split to get last two segments
        norm_path = os.path.normpath(path)
        parts = norm_path.split(os.sep)
        if len(parts) >= 2:
            redacted_path = os.path.join(parts[-2], parts[-1]).replace("\\", "/")
        else:
            redacted_path = norm_path
    else:
        redacted_path = None

    # Handle backup_path redaction
    if backup_path:
        if is_sensitive:
            redacted_backup = "<sensitive backup>"
        else:
            norm_b = os.path.normpath(backup_path)
            b_parts = norm_b.split(os.sep)
            if len(b_parts) >= 2:
                redacted_backup = os.path.join(b_parts[-2], b_parts[-1]).replace(
                    "\\", "/"
                )
            else:
                redacted_backup = norm_b
    else:
        redacted_backup = None

    entry = {
        "timestamp": timestamp,
        "node": node,
        "action_type": action_type,
        "path": redacted_path,
        "hitl_status": hitl_status,
        "result": result,
        "reason": reason,
    }

    # Add optional context parameters
    if rollback_supported is not None:
        entry["rollback_supported"] = rollback_supported
    if rollback_enabled is not None:
        entry["rollback_enabled"] = rollback_enabled
    if approved_actions_count is not None:
        entry["approved_actions_count"] = approved_actions_count
    if rejected_actions_count is not None:
        entry["rejected_actions_count"] = rejected_actions_count
    if hitl_required is not None:
        entry["hitl_required"] = hitl_required
    if redacted_backup is not None:
        entry["backup_path"] = redacted_backup
    if rollback_reason is not None:
        entry["rollback_reason"] = rollback_reason
    if plan_id is not None:
        entry["plan_id"] = plan_id
    if session_id is not None:
        entry["session_id"] = session_id
    if safety_override_reason is not None:
        entry["safety_override_reason"] = safety_override_reason

    log_file_path = os.environ.get("CLEANSLATE_LOG_PATH", LOG_PATH)
    log_dir = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    with (
        open(log_file_path, "a", encoding="utf-8") as f
    ):  # nosemgrep: no-file-content-reading, file-ops-must-use-folder-scope (Justified: Log writing is a system audit command)
        f.write(json.dumps(entry) + "\n")
