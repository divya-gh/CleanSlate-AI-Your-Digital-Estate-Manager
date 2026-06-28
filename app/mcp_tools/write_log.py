import json

from app.security.audit_logger import log_action


def write_log(entry: str) -> dict:
    """Writes an entry to the agent's audit log using the central audit logger."""
    try:
        # Try to parse entry as JSON to get structured fields
        data = json.loads(entry)
        if isinstance(data, dict):
            node = data.get("node", "MCP_Tool_write_log")
            action_type = data.get("action_type", "custom_log")
            path = data.get("path")
            is_sensitive = data.get("is_sensitive", False)
            hitl_status = data.get("hitl_status", "none")
            result = data.get("result", "info")
            reason = data.get("reason")

            log_action(
                node=node,
                action_type=action_type,
                path=path,
                is_sensitive=is_sensitive,
                hitl_status=hitl_status,
                result=result,
                reason=reason,
            )
            return {"status": "logged"}
    except Exception:
        pass

    # Fallback to logging raw entry string
    try:
        log_action(
            node="MCP_Tool_write_log",
            action_type="custom_log",
            path=None,
            is_sensitive=False,
            hitl_status="none",
            result="info",
            reason=entry,
        )
        return {"status": "logged"}
    except PermissionError:
        raise PermissionError("PermissionDenied: Unable to write to audit log")
    except Exception as e:
        raise e
