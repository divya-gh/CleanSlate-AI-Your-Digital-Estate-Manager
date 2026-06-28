import os
import shutil

from app.mcp_tools.utils import (
    is_authenticated_folder,
    is_sensitive,
    validate_path_safety,
)
from app.security.audit_logger import log_action


def move_file(source: str, destination: str) -> dict:
    """Moves a file safely from source to destination, with atomic replace fallback."""
    # 1. Enforce path safety validations on both paths
    validate_path_safety(source)
    validate_path_safety(destination)

    if not os.path.exists(source):
        raise FileNotFoundError(f"FileNotFound: {source} not found")

    # 2. Check sensitivity rules
    source_sensitive = is_sensitive(source)
    dest_authenticated = is_authenticated_folder(destination)

    if source_sensitive and not dest_authenticated:
        raise ValueError(
            "SecurityViolation: Sensitive files can only be moved to authenticated secure folders"
        )

    atomic_fallback_used = False
    try:
        # Pre-execution log
        log_action(
            node="MCP_Tool_move_file",
            action_type="move_planned",
            path=source,
            is_sensitive=source_sensitive,
            hitl_status="none",
            result="started",
            reason=f"Moving to {destination}",
        )

        dest_dir = os.path.dirname(destination)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)

        try:
            os.replace(source, destination)
        except OSError:
            # nosemgrep: no-unsafe-shutil-move (Justified: os.replace failed due to cross-device link, falling back safely)
            shutil.move(source, destination)
            atomic_fallback_used = True

        # Post-execution log
        log_action(
            node="MCP_Tool_move_file",
            action_type="move",
            path=destination,
            is_sensitive=source_sensitive,
            hitl_status="none",
            result="success",
            reason=f"Moved from {source}",
        )
        return {
            "status": "success",
            "atomic_fallback_used": atomic_fallback_used,
        }
    except PermissionError:
        log_action(
            node="MCP_Tool_move_file",
            action_type="move",
            path=source,
            is_sensitive=source_sensitive,
            hitl_status="none",
            result="failed",
            reason="Permission denied",
        )
        raise PermissionError(f"PermissionDenied: Access denied to {source}")
    except Exception as e:
        log_action(
            node="MCP_Tool_move_file",
            action_type="move",
            path=source,
            is_sensitive=source_sensitive,
            hitl_status="none",
            result="failed",
            reason=str(e),
        )
        raise e
