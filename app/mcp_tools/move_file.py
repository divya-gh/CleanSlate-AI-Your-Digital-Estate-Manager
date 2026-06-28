import os
import shutil

from app.mcp_tools.utils import (
    is_authenticated_folder,
    is_path_allowed_by_policy,
    is_sensitive,
)
from app.security.audit_logger import log_action


def move_file(source: str, destination: str) -> dict:
    """Moves a file safely from source to destination, checking folder policies and sensitivity rules."""
    # 1. Enforce folder scope policy on both paths
    if not is_path_allowed_by_policy(source):
        raise ValueError("PathNotAllowed: Source is not allowed by folder scope policy")

    if not is_path_allowed_by_policy(destination):
        raise ValueError(
            "PathNotAllowed: Destination is not allowed by folder scope policy"
        )

    if not os.path.exists(source):
        raise FileNotFoundError(f"FileNotFound: {source} not found")

    # 2. Check sensitivity rules
    source_sensitive = is_sensitive(source)
    dest_authenticated = is_authenticated_folder(destination)

    if source_sensitive and not dest_authenticated:
        raise ValueError(
            "SecurityViolation: Sensitive files can only be moved to authenticated secure folders"
        )

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

        # Atomic move or copy/delete
        dest_dir = os.path.dirname(destination)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)

        shutil.move(source, destination)

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
        return {"status": "success"}
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
