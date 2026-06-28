from app.mcp_tools import TOOLS
from app.mcp_tools.utils import is_path_allowed_by_policy
from app.security.audit_logger import log_action

TOOL_SCHEMAS = {
    "list_files": {"path": str},
    "read_file_metadata": {"path": str},
    "compute_hash": {"path": str},
    "move_file": {"source": str, "destination": str},
    "delete_file": {"path": str, "hitl_approved": bool},
    "create_folder": {"path": str},
    "compress_files": {"files": list, "destination": str},
    "write_log": {"entry": str},
    "read_log": {"limit": int},
    "move_to_authenticated_folder": {"source": str, "destination": str},
}

TOOL_DESCRIPTIONS = {
    "list_files": "List files in a directory within allowed folder scope.",
    "read_file_metadata": "Retrieve metadata (size, timestamps, MIME type) without opening file contents.",
    "compute_hash": "Compute SHA256 hash for duplicate detection using streaming chunked reads.",
    "move_file": "Move a file from source to destination respecting folder scope and sensitive policies.",
    "delete_file": "Delete a file requiring HITL approval, safe mode checks, and sensitive path validation.",
    "create_folder": "Create a folder under allowed directories.",
    "compress_files": "Create a ZIP archive of selected files, skipping sensitive files.",
    "write_log": "Write an entry to the central audit log.",
    "read_log": "Retrieve audit logs for summaries with limits and redactions.",
    "move_to_authenticated_folder": "Secure sensitive files to authenticated directories.",
}


def get_tool(name: str):
    """Retrieves a registered tool function by name."""
    if name not in TOOLS:
        raise KeyError(f"Tool '{name}' is not registered.")
    return TOOLS[name]


def list_tools() -> list[dict]:
    """Returns metadata for all registered tools."""
    list_res = []
    for name in TOOLS:
        list_res.append(
            {
                "name": name,
                "description": TOOL_DESCRIPTIONS.get(name, ""),
                "parameters": TOOL_SCHEMAS.get(name, {}),
            }
        )
    return list_res


def test_tool(name: str, **kwargs) -> dict:
    """Safely validates, logs, and executes a tool for test/CLI wrappers."""
    # 1. Check if tool exists
    if name not in TOOLS:
        return {
            "status": "error",
            "error_code": "UnknownTool",
            "message": f"Tool '{name}' is not registered.",
        }

    schema = TOOL_SCHEMAS[name]
    validated_args = {}

    # 2. Schema validation
    for key, expected_type in schema.items():
        if key not in kwargs:
            # Handle optional args with defaults
            if name == "delete_file" and key == "hitl_approved":
                validated_args["hitl_approved"] = False
                continue
            if name == "read_log" and key == "limit":
                validated_args["limit"] = None
                continue
            return {
                "status": "error",
                "error_code": "MissingArgument",
                "message": f"Missing required argument: '{key}'",
            }

        val = kwargs[key]
        if expected_type is int:
            if val is None:
                validated_args[key] = None
            else:
                try:
                    validated_args[key] = int(val)
                except Exception:
                    return {
                        "status": "error",
                        "error_code": "InvalidArgumentType",
                        "message": f"Argument '{key}' must be an integer.",
                    }
        elif expected_type is bool:
            if isinstance(val, str):
                validated_args[key] = val.lower() in ("true", "yes", "1", "y")
            elif isinstance(val, bool):
                validated_args[key] = val
            else:
                return {
                    "status": "error",
                    "error_code": "InvalidArgumentType",
                    "message": f"Argument '{key}' must be a boolean.",
                }
        elif expected_type is list:
            if isinstance(val, str):
                validated_args[key] = [x.strip() for x in val.split(",") if x.strip()]
            elif isinstance(val, list):
                validated_args[key] = val
            else:
                return {
                    "status": "error",
                    "error_code": "InvalidArgumentType",
                    "message": f"Argument '{key}' must be a list or comma-separated string.",
                }
        else:
            if not isinstance(val, str):
                return {
                    "status": "error",
                    "error_code": "InvalidArgumentType",
                    "message": f"Argument '{key}' must be a string.",
                }
            validated_args[key] = val

    # 3. Policy checks on arguments
    for key, val in validated_args.items():
        if key in ("path", "source", "destination"):
            if val and not is_path_allowed_by_policy(val):
                return {
                    "status": "error",
                    "error_code": "PathNotAllowed",
                    "message": f"Path '{val}' violates the folder scope policy.",
                }
        elif key == "files" and isinstance(val, list):
            for f in val:
                if not is_path_allowed_by_policy(f):
                    return {
                        "status": "error",
                        "error_code": "PathNotAllowed",
                        "message": f"Path '{f}' violates the folder scope policy.",
                    }

    # 4. Log the test invocation
    log_action(
        node="ToolRegistry_test_tool",
        action_type="test_invocation",
        path=validated_args.get("path") or validated_args.get("source"),
        is_sensitive=False,
        hitl_status="none",
        result="started",
        reason=f"Testing tool {name}",
    )

    # 5. Call the tool safely
    try:
        tool_func = TOOLS[name]
        res = tool_func(**validated_args)

        log_action(
            node="ToolRegistry_test_tool",
            action_type="test_invocation",
            path=validated_args.get("path") or validated_args.get("source"),
            is_sensitive=False,
            hitl_status="none",
            result="success",
            reason=f"Tested tool {name} successfully",
        )
        return {"status": "success", "result": res}
    except Exception as e:
        log_action(
            node="ToolRegistry_test_tool",
            action_type="test_invocation",
            path=validated_args.get("path") or validated_args.get("source"),
            is_sensitive=False,
            hitl_status="none",
            result="failed",
            reason=f"Tool execution failed: {e}",
        )
        return {
            "status": "error",
            "error_code": type(e).__name__,
            "message": str(e),
        }
