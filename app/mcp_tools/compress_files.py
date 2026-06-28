import os
import zipfile

from app.mcp_tools.utils import is_sensitive, validate_path_safety
from app.security.audit_logger import log_action


def compress_files(files: list[str], destination: str) -> dict:
    """Creates a ZIP archive of selected files, skipping sensitive items and validating paths."""
    # 1. Validate destination path safety
    validate_path_safety(destination)

    if os.path.exists(destination):
        raise ValueError("AlreadyExists: Destination archive already exists")

    # 2. Filter allowed files and identify sensitive skips
    allowed_files = []
    skipped_sensitive = []

    for f in files:
        try:
            validate_path_safety(f)
        except Exception:
            # Skip disallowed or unsafe paths
            continue

        if not os.path.exists(f):
            raise FileNotFoundError(f"FileNotFound: {f} not found")

        if is_sensitive(f):
            skipped_sensitive.append(f)
            # Log skipped sensitive file
            log_action(
                node="MCP_Tool_compress_files",
                action_type="compress_skip",
                path=f,
                is_sensitive=True,
                hitl_status="none",
                result="skipped",
                reason="Sensitive file skipped during compression",
            )
            continue
        allowed_files.append(f)

    if not allowed_files:
        raise ValueError(
            "NoFilesToCompress: All input files were skipped, missing, or sensitive"
        )

    try:
        # Pre-execution log
        log_action(
            node="MCP_Tool_compress_files",
            action_type="compress_planned",
            path=destination,
            is_sensitive=False,
            hitl_status="none",
            result="started",
            reason=f"Compressing {len(allowed_files)} file(s)",
        )

        dest_dir = os.path.dirname(destination)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)

        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zip_f:
            for f in allowed_files:
                # Add file under its basename to prevent full path exposure inside the ZIP
                zip_f.write(f, os.path.basename(f))

        # Post-execution log
        log_action(
            node="MCP_Tool_compress_files",
            action_type="compress",
            path=destination,
            is_sensitive=False,
            hitl_status="none",
            result="success",
            reason=f"Archived files: {', '.join(os.path.basename(x) for x in allowed_files)}",
        )

        return {
            "status": "compressed",
            "archive_path": destination,
            "skipped_sensitive": [os.path.basename(x) for x in skipped_sensitive],
        }
    except PermissionError:
        log_action(
            node="MCP_Tool_compress_files",
            action_type="compress",
            path=destination,
            is_sensitive=False,
            hitl_status="none",
            result="failed",
            reason="Permission denied",
        )
        raise PermissionError(f"PermissionDenied: Access denied to {destination}")
    except Exception as e:
        log_action(
            node="MCP_Tool_compress_files",
            action_type="compress",
            path=destination,
            is_sensitive=False,
            hitl_status="none",
            result="failed",
            reason=str(e),
        )
        raise e
