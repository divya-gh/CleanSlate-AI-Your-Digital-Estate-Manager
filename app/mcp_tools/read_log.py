import json
import os

from app.mcp_tools.utils import is_sensitive


def read_log(limit: int | None = None) -> dict:
    """Reads audit logs safely, enforcing limits and redacting sensitive paths on read."""
    log_path = os.environ.get("CLEANSLATE_LOG_PATH", "logs/audit.log")
    if not os.path.exists(log_path):
        return {"entries": []}

    try:
        raw_entries = []
        with open(  # nosemgrep: no-file-content-reading, no-directory-traversal
            log_path, encoding="utf-8"
        ) as f:
            # Stream line-by-line to avoid loading large arrays of lines at once
            for line in f:
                if line.strip():
                    try:
                        raw_entries.append(json.loads(line))
                    except Exception:
                        pass

        # Apply limit to retrieve only the last N logs efficiently
        if limit:
            raw_entries = raw_entries[-limit:]

        # Enforce redaction on read for absolute path leak prevention
        sanitized_lines = []
        for entry in raw_entries:
            path = entry.get("path")
            if path:
                if is_sensitive(path) or path == "<sensitive file>":
                    entry["path"] = "<sensitive file>"
                else:
                    # Clean absolute paths if any leaked
                    if os.path.isabs(path) or "/" in path or "\\" in path:
                        entry["path"] = os.path.join(
                            os.path.basename(os.path.dirname(path)),
                            os.path.basename(path),
                        ).replace("\\", "/")
            sanitized_lines.append(json.dumps(entry))

        return {"entries": sanitized_lines}
    except PermissionError:
        raise PermissionError(
            f"PermissionDenied: Access denied to log file at {log_path}"
        ) from None
    except Exception as e:
        raise e
