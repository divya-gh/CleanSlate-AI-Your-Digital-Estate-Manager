import os

from app.config import load_policy
from app.mcp_tools.utils import SafetyViolationError, is_sensitive, validate_path_safety
from app.security.audit_logger import log_action


def delete_file(path: str, hitl_approved: bool = False) -> dict:
    """Deletes a file if allowed by policy, HITL approval, safe mode, and sensitivity rules."""
    # 1. Enforce folder scope policy and basic safety validations
    validate_path_safety(path)

    # 2. Check safe_mode from policy
    policy_dict = load_policy()
    if policy_dict and policy_dict.get("safe_mode", False):
        log_action(
            node="MCP_Tool_delete_file",
            action_type="delete_blocked",
            path=path,
            is_sensitive=False,
            hitl_status="none",
            result="failed",
            reason="safe_mode_blocked",
        )
        raise SafetyViolationError(
            "SafeModeActive: Deletes are forbidden when safe mode is enabled",
            {"safe_mode_blocked": True, "safe_mode": True},
        )

    # 3. Check sensitivity (never delete sensitive files)
    sensitive_file = is_sensitive(path)
    if sensitive_file:
        log_action(
            node="MCP_Tool_delete_file",
            action_type="delete_blocked",
            path=path,
            is_sensitive=True,
            hitl_status="none",
            result="failed",
            reason="sensitive_file_blocked",
        )
        raise SafetyViolationError(
            "SecurityViolation: Sensitive files cannot be deleted",
            {"blocked_by_sensitive": True},
        )

    # 4. Require HITL approval
    if not hitl_approved:
        raise SafetyViolationError(
            "HITLApprovalRequired: Interactive approval is required to delete files",
            {"hitl_required": True},
        )

    if not os.path.exists(path):
        raise FileNotFoundError(f"FileNotFound: {path} not found")

    if os.path.isdir(path):
        raise ValueError("PathInvalid: Must be a file, not a directory")

    try:
        # Pre-execution log
        log_action(
            node="MCP_Tool_delete_file",
            action_type="delete_planned",
            path=path,
            is_sensitive=False,
            hitl_status="approved",
            result="started",
            reason="User confirmed deletion",
        )

        os.unlink(path)  # nosemgrep: no-direct-file-deletes

        # Post-execution log
        log_action(
            node="MCP_Tool_delete_file",
            action_type="delete",
            path=path,
            is_sensitive=False,
            hitl_status="approved",
            result="success",
            reason="hitl_approved",
        )
        return {"status": "deleted"}
    except PermissionError:
        log_action(
            node="MCP_Tool_delete_file",
            action_type="delete",
            path=path,
            is_sensitive=False,
            hitl_status="approved",
            result="failed",
            reason="Permission denied",
        )
        raise PermissionError(f"PermissionDenied: Access denied to {path}")
    except Exception as e:
        log_action(
            node="MCP_Tool_delete_file",
            action_type="delete",
            path=path,
            is_sensitive=False,
            hitl_status="approved",
            result="failed",
            reason=str(e),
        )
        raise e
