import re
from app.mcp_tools.list_files import list_files
from app.mcp_tools.read_file_metadata import read_file_metadata
from app.mcp_tools.compute_hash import compute_hash
from app.mcp_tools.move_file import move_file
from app.mcp_tools.delete_file import delete_file
from app.mcp_tools.create_folder import create_folder
from app.mcp_tools.compress_files import compress_files
from app.mcp_tools.write_log import write_log
from app.mcp_tools.read_log import read_log
from app.mcp_tools.move_to_authenticated_folder import move_to_authenticated_folder
from app.security.audit_logger import log_action

def normalize_name(name: str) -> str:
    """Normalizes tool name from formats like camelCase, kebab-case, or spaces to snake_case."""
    name = name.strip()
    # camelCase -> snake_case
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = name.lower().replace("-", "_").replace(" ", "_")
    return name

TOOLS = {
    "list_files": {
        "fn": list_files,
        "description": "List files in a directory within allowed folder scope.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The directory path to list"}
            },
            "required": ["path"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "path": {"type": "string"},
                            "is_dir": {"type": "boolean"},
                            "size": {"type": "integer"},
                        },
                    },
                }
            },
        },
    },
    "read_file_metadata": {
        "fn": read_file_metadata,
        "description": "Retrieve metadata (size, timestamps, MIME type) without opening file contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The file path to query"}
            },
            "required": ["path"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "size": {"type": "integer"},
                "created_at": {"type": "string"},
                "modified_at": {"type": "string"},
                "extension": {"type": "string"},
                "mime_type": {"type": "string"},
            },
        },
    },
    "compute_hash": {
        "fn": compute_hash,
        "description": "Compute SHA256 hash for duplicate detection using streaming chunked reads.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The file path to hash"}
            },
            "required": ["path"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"sha256": {"type": "string"}},
        },
    },
    "move_file": {
        "fn": move_file,
        "description": "Move a file from source to destination respecting folder scope and sensitive policies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source path"},
                "destination": {"type": "string", "description": "Destination path"},
            },
            "required": ["source", "destination"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"status": {"type": "string"}, "destination": {"type": "string"}},
        },
    },
    "delete_file": {
        "fn": delete_file,
        "description": "Delete a file requiring HITL approval, safe mode checks, and sensitive path validation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to delete"},
                "hitl_approved": {"type": "boolean", "description": "Whether HITL approval is granted"},
            },
            "required": ["path"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"status": {"type": "string"}, "path": {"type": "string"}},
        },
    },
    "create_folder": {
        "fn": create_folder,
        "description": "Create a folder under allowed directories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Folder path to create"}
            },
            "required": ["path"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"status": {"type": "string"}},
        },
    },
    "compress_files": {
        "fn": compress_files,
        "description": "Create a ZIP archive of selected files, skipping sensitive files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of files to compress",
                },
                "destination": {"type": "string", "description": "Destination zip file path"},
            },
            "required": ["files", "destination"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"status": {"type": "string"}, "archive": {"type": "string"}},
        },
    },
    "write_log": {
        "fn": write_log,
        "description": "Write an entry to the central audit log.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entry": {"type": "string", "description": "JSON string containing structured log details"}
            },
            "required": ["entry"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"status": {"type": "string"}},
        },
    },
    "read_log": {
        "fn": read_log,
        "description": "Retrieve audit logs for summaries with limits and redactions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max number of entries to return"}
            },
            "required": [],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
        },
    },
    "move_to_authenticated_folder": {
        "fn": move_to_authenticated_folder,
        "description": "Secure sensitive files to authenticated directories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Sensitive source file path"},
                "destination": {"type": "string", "description": "Authenticated folder destination path"},
            },
            "required": ["source", "destination"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"status": {"type": "string"}, "destination": {"type": "string"}},
        },
    },
}

def get_tool(name: str):
    """Retrieves a registered tool metadata object by name (supporting normalization)."""
    norm = normalize_name(name)
    if norm not in TOOLS:
        raise KeyError(f"Tool '{name}' is not registered.")
    return TOOLS[norm]["fn"]

def list_tools() -> list[dict]:
    """Returns metadata for all registered tools."""
    list_res = []
    for name, metadata in TOOLS.items():
        list_res.append({
            "name": name,
            "description": metadata["description"],
            "input_schema": metadata["input_schema"],
            "output_schema": metadata["output_schema"],
        })
    return list_res

def test_tool(name: str, **kwargs) -> dict:
    """Safely validates input schema, normalizes names, and executes a tool."""
    norm = normalize_name(name)
    
    # 1. Availability check
    if norm not in TOOLS:
        return {
            "error": {
                "type": "ToolNotFound",
                "message": f"Tool '{name}' is not registered.",
                "details": {"requested_name": name, "normalized_name": norm},
            }
        }

    tool_meta = TOOLS[norm]
    input_schema = tool_meta["input_schema"]
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    validated_args = {}

    # 2. Reject unknown keys
    for k in kwargs:
        if k not in properties:
            return {
                "error": {
                    "type": "SchemaError",
                    "message": f"Unexpected argument: '{k}'",
                    "details": {"unknown_key": k},
                }
            }

    # 3. Schema validation & type coercion
    for key, prop_info in properties.items():
        expected_type_str = prop_info["type"]
        
        if key not in kwargs:
            # Handle optional args with defaults
            if norm == "delete_file" and key == "hitl_approved":
                validated_args["hitl_approved"] = False
                continue
            if norm == "read_log" and key == "limit":
                validated_args["limit"] = None
                continue
            
            if key in required:
                return {
                    "error": {
                        "type": "SchemaError",
                        "message": f"Missing required argument: '{key}'",
                        "details": {"missing_key": key},
                    }
                }
            continue

        val = kwargs[key]
        
        # Type coercion
        if expected_type_str == "integer":
            if val is None:
                validated_args[key] = None
            else:
                try:
                    validated_args[key] = int(val)
                except (ValueError, TypeError):
                    return {
                        "error": {
                            "type": "SchemaError",
                            "message": f"Argument '{key}' must be an integer.",
                            "details": {"key": key, "invalid_value": val},
                        }
                    }
        elif expected_type_str == "boolean":
            if isinstance(val, str):
                validated_args[key] = val.lower() in ("true", "yes", "1", "y")
            elif isinstance(val, bool):
                validated_args[key] = val
            else:
                return {
                    "error": {
                        "type": "SchemaError",
                        "message": f"Argument '{key}' must be a boolean.",
                        "details": {"key": key, "invalid_value": val},
                    }
                }
        elif expected_type_str == "array":
            if isinstance(val, str):
                validated_args[key] = [x.strip() for x in val.split(",") if x.strip()]
            elif isinstance(val, list):
                validated_args[key] = val
            else:
                return {
                    "error": {
                        "type": "SchemaError",
                        "message": f"Argument '{key}' must be an array or list.",
                        "details": {"key": key, "invalid_value": val},
                    }
                }
        else:  # string
            if not isinstance(val, str):
                return {
                    "error": {
                        "type": "SchemaError",
                        "message": f"Argument '{key}' must be a string.",
                        "details": {"key": key, "invalid_value": val},
                    }
                }
            validated_args[key] = val

    # 4. Log invocation start
    log_action(
        node="ToolRegistry_test_tool",
        action_type="test_invocation",
        path=validated_args.get("path") or validated_args.get("source"),
        is_sensitive=False,
        hitl_status="none",
        result="started",
        reason=f"Testing tool {norm}",
    )

    # 5. Call the tool safely (Pure Registry - safety and policy checks executed inside the tool function itself)
    try:
        tool_func = tool_meta["fn"]
        res = tool_func(**validated_args)
        
        log_action(
            node="ToolRegistry_test_tool",
            action_type="test_invocation",
            path=validated_args.get("path") or validated_args.get("source"),
            is_sensitive=False,
            hitl_status="none",
            result="success",
            reason=f"Tested tool {norm} successfully",
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
            "error": {
                "type": "ToolError",
                "message": str(e),
                "details": {"exception_class": type(e).__name__, "normalized_name": norm},
            }
        }
