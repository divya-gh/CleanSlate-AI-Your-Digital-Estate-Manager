import os
import shutil

from app.mcp_tools.utils import (
    is_authenticated_folder,
    is_path_allowed_by_policy,
    is_sensitive,
)
from app.security.audit_logger import log_action


def move_to_authenticated_folder(source: str, destination: str) -> dict:
    """Moves a sensitive file to an authenticated secure folder."""
    # 1. Enforce folder scope policy
    if not is_path_allowed_by_policy(source):
        raise ValueError("PathNotAllowed: Source path is not allowed by policy")

    if not is_path_allowed_by_policy(destination):
        raise ValueError("PathNotAllowed: Destination path is not allowed by policy")

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

        shutil.move(source, destination)

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
        return {"status": "secured"}
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
