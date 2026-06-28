import os

from app.mcp_tools.utils import is_path_allowed_by_policy


def create_folder(path: str) -> dict:
    """Creates a folder if the target path and its parents are allowed by policy."""
    # 1. Enforce folder scope policy
    if not is_path_allowed_by_policy(path):
        raise ValueError("PathNotAllowed: Path is not allowed by folder scope policy")

    if os.path.exists(path):
        if os.path.isdir(path):
            raise ValueError("AlreadyExists: Directory already exists")
        else:
            raise ValueError("AlreadyExists: A file with this name already exists")

    # Verify parent directory is also allowed
    parent = os.path.dirname(path)
    if parent and not is_path_allowed_by_policy(parent):
        raise ValueError("PathNotAllowed: Parent directory path is not allowed")

    try:
        os.makedirs(path, exist_ok=True)
        return {"status": "created"}
    except PermissionError:
        raise PermissionError(f"PermissionDenied: Access denied to {path}")
