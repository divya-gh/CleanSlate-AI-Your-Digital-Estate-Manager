import os
import shutil

from app.mcp_tools.utils import (
    is_authenticated_folder,
    is_sensitive,
    validate_path_safety,
)
from app.security.audit_logger import log_action


def move_to_authenticated_folder(source: str, destination: str) -> dict:
    """Moves a sensitive file to an authenticated secure folder with atomic fallback."""
    # 1. Enforce path safety validations
    validate_path_safety(source)
    validate_path_safety(destination)

    if not os.path.exists(source):
        raise FileNotFoundError(f"FileNotFound: {source} not found")

    # 2. Enforce sensitive rules
    if not is_sensitive(source):
        raise ValueError(
            "SecurityViolation: Only files identified as sensitive can be moved to the secure folder"
        )

    if not is_authenticated_folder(destination):
        raise ValueError(
            "SecurityViolation: Destination is not an authenticated secure folder"
        )

    atomic_fallback_used = False
    try:
        # Pre-execution log
        log_action(
            node="MCP_Tool_move_to_authenticated_folder",
            action_type="secure_planned",
            path=source,
            is_sensitive=True,
            hitl_status="none",
            result="started",
            reason=f"Securing to {destination}",
        )

        dest_dir = os.path.dirname(destination)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)

        try:
            os.replace(source, destination)
        except OSError:
            # nosemgrep: no-unsafe-shutil-move (Justified: os.replace failed, falling back safely)
            shutil.move(source, destination)
            atomic_fallback_used = True

        # Post-execution log
        log_action(
            node="MCP_Tool_move_to_authenticated_folder",
            action_type="secure",
            path=destination,
            is_sensitive=True,
            hitl_status="none",
            result="success",
            reason=f"Secured from {source}",
        )
        return {
            "status": "secured",
            "atomic_fallback_used": atomic_fallback_used,
        }
    except PermissionError:
        log_action(
            node="MCP_Tool_move_to_authenticated_folder",
            action_type="secure",
            path=source,
            is_sensitive=True,
            hitl_status="none",
            result="failed",
            reason="Permission denied",
        )
        raise PermissionError(f"PermissionDenied: Access denied to {source}")
    except Exception as e:
        log_action(
            node="MCP_Tool_move_to_authenticated_folder",
            action_type="secure",
            path=source,
            is_sensitive=True,
            hitl_status="none",
            result="failed",
            reason=str(e),
        )
        raise e
