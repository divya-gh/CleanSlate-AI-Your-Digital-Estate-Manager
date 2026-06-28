import os
from datetime import datetime

from app.mcp_tools.utils import is_path_allowed_by_policy


def list_files(path: str) -> dict:
    """Lists files in a directory if allowed by policy."""
    if not is_path_allowed_by_policy(path):
        raise ValueError("PathNotAllowed: Path is not allowed by folder scope policy")

    if not os.path.exists(path):
        raise FileNotFoundError(f"PathNotFound: {path} not found")

    if not os.path.isdir(path):
        raise ValueError("PathInvalid: Must be a directory")

    files_list = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                # Ensure the entry itself is allowed by policy
                if not is_path_allowed_by_policy(entry.path):
                    continue
                try:
                    stat = entry.stat()
                    modified_at = (
                        datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z"
                    )
                    created_at = datetime.fromtimestamp(stat.st_ctime).isoformat() + "Z"
                    files_list.append(
                        {
                            "name": entry.name,
                            "path": entry.path,
                            "size": stat.st_size if entry.is_file() else 0,
                            "modified_at": modified_at,
                            "created_at": created_at,
                            "is_directory": entry.is_dir(),
                        }
                    )
                except Exception:
                    pass
    except PermissionError:
        raise PermissionError(f"PermissionDenied: Access denied to {path}")

    return {"files": files_list}
