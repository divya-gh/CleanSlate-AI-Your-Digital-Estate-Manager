import hashlib
import os

from app.mcp_tools.utils import SafetyViolationError, is_sensitive, validate_path_safety


def compute_hash(path: str) -> dict:
    """Computes SHA256 hash using streaming chunked reading with size limits."""
    validate_path_safety(path)

    if is_sensitive(path):
        raise ValueError("SensitiveFileError: Cannot compute hash of sensitive files")

    if not os.path.exists(path):
        raise FileNotFoundError(f"FileNotFound: {path} not found")

    if os.path.isdir(path):
        raise ValueError("PathInvalid: Must be a file, not a directory")

    # Check file size limit (2GB)
    file_size = os.path.getsize(path)
    max_size = 2 * 1024 * 1024 * 1024
    if file_size > max_size:
        raise SafetyViolationError(
            "FileTooLargeError: File exceeds maximum supported size of 2GB",
            {"file_too_large": True, "max_supported_size": "2GB"},
        )

    sha256 = hashlib.sha256()
    chunk_size = 65536
    try:
        # fmt: off
        with open(path, "rb") as f:  # nosemgrep: no-file-content-reading, file-ops-must-use-folder-scope, no-directory-traversal
        # fmt: on
            while True:
                # nosemgrep: no-file-content-reading
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256.update(chunk)
        return {
            "sha256": sha256.hexdigest(),
            "hash_method": "sha256_streaming",
            "chunk_size": chunk_size,
        }
    except PermissionError:
        raise PermissionError(f"PermissionDenied: Access denied to {path}")
    except Exception as e:
        # Prevent exposing raw bytes or partial contents in string conversion
        raise RuntimeError(
            f"HashCalculationFailed: Error calculating hash: {type(e).__name__}"
        )
