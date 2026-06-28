import mimetypes
import os
from datetime import datetime

from app.mcp_tools.utils import is_sensitive, validate_path_safety


def read_file_metadata(path: str) -> dict:
    """Retrieves file metadata without opening the file, enforcing safety checks."""
    validate_path_safety(path)

    if is_sensitive(path):
        raise ValueError(
            "SensitiveFileError: Cannot retrieve metadata for sensitive files"
        )

    if not os.path.exists(path):
        raise FileNotFoundError(f"FileNotFound: {path} not found")

    if os.path.isdir(path):
        raise ValueError("PathInvalid: Must be a file, not a directory")

    try:
        stat = os.stat(path)
        modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z"
        created_at = datetime.fromtimestamp(stat.st_ctime).isoformat() + "Z"

        _, extension = os.path.splitext(path)
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            mime_type = "application/octet-stream"

        return {
            "size": stat.st_size,
            "modified_at": modified_at,
            "created_at": created_at,
            "extension": extension,
            "mime_type": mime_type,
        }
    except PermissionError:
        raise PermissionError(f"PermissionDenied: Access denied to {path}")
