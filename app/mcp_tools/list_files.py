import os
from datetime import datetime

from app.mcp_tools.utils import validate_path_safety


def list_files(path: str) -> dict:
    """Lists files in a directory if allowed by policy, blocking symlinks/junctions/traversals."""
    validate_path_safety(path)

    if not os.path.exists(path):
        raise FileNotFoundError(f"PathNotFound: {path} not found")

    if not os.path.isdir(path):
        raise ValueError("PathInvalid: Must be a directory")

    files_list = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    # Validate safety of each item
                    validate_path_safety(entry.path)

                    stat = entry.stat()
                    modified_at = (
                        datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z"
                    )
                    created_at = datetime.fromtimestamp(stat.st_ctime).isoformat() + "Z"

                    # Normalize path to be relative to the queried directory
                    rel_path = os.path.relpath(entry.path, path).replace("\\", "/")

                    files_list.append(
                        {
                            "name": entry.name,
                            "path": rel_path,
                            "size": stat.st_size if entry.is_file() else 0,
                            "modified_at": modified_at,
                            "created_at": created_at,
                            "is_directory": entry.is_dir(),
                        }
                    )
                except Exception:
                    # Skip symlinks/junctions/blocked files inside list
                    continue
    except PermissionError:
        raise PermissionError(f"PermissionDenied: Access denied to {path}")

    return {"files": files_list}
