import hashlib
import os

from app.mcp_tools.utils import is_path_allowed_by_policy, is_sensitive


def compute_hash(path: str) -> dict:
    """Computes SHA256 hash using streaming chunked reading."""
    # 1. Scope and sensitive checks first
    if not is_path_allowed_by_policy(path):
        raise ValueError("PathNotAllowed: Path is not allowed by folder scope policy")

    if is_sensitive(path):
        raise ValueError("SensitiveFileError: Cannot compute hash of sensitive files")

    if not os.path.exists(path):
        raise FileNotFoundError(f"FileNotFound: {path} not found")

    if os.path.isdir(path):
        raise ValueError("PathInvalid: Must be a file, not a directory")

    sha256 = hashlib.sha256()
    try:
        # fmt: off
        with open(path, "rb") as f:  # nosemgrep: no-file-content-reading, file-ops-must-use-folder-scope
        # fmt: on
            while True:
                # nosemgrep: no-file-content-reading
                chunk = f.read(8192)
                if not chunk:
                    break
                sha256.update(chunk)
        return {"sha256": sha256.hexdigest()}
    except PermissionError:
        raise PermissionError(f"PermissionDenied: Access denied to {path}")
