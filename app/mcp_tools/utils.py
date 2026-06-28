import os
import re
from pathlib import Path

from app.config import load_policy
from app.nodes.file_discovery_node import FolderScopePolicy
from app.nodes.sensitive_detection_node import (
    _SENSITIVE_EXTENSIONS,
    _SENSITIVE_KEYWORDS,
)

# Standard system directory pattern to match Semgrep no-system-folder-access
SYSTEM_DIR_PATTERN = re.compile(
    r".*[\/\\](Windows|System32|Program Files|Library|usr)([\/\\]|$)",
    re.IGNORECASE,
)


def is_path_allowed_by_policy(path: str | Path) -> bool:
    """Checks if a path is allowed under the current persistent policy and rejects system folders."""
    path_str = str(path)

    # 1. Block system folders
    if SYSTEM_DIR_PATTERN.match(path_str):
        return False

    # 2. Check policy configuration
    policy_dict = load_policy()
    if not policy_dict:
        # Default to False if no policy exists (safety first)
        return False
    try:
        policy = FolderScopePolicy.model_validate(policy_dict)
        resolved_path = os.path.normcase(os.path.abspath(path_str))

        # Check blocked paths
        for bp in policy.blocked_paths:
            bp_resolved = os.path.normcase(os.path.abspath(bp))
            if resolved_path == bp_resolved or resolved_path.startswith(
                bp_resolved + os.sep
            ):
                return False

        # Check allowed paths
        if not policy.allowed_paths:
            return False

        for ap in policy.allowed_paths:
            ap_resolved = os.path.normcase(os.path.abspath(ap))
            if resolved_path == ap_resolved or resolved_path.startswith(
                ap_resolved + os.sep
            ):
                return True
        return False
    except Exception:
        return False


def is_sensitive(path: str | Path) -> bool:
    """Detects if a file or directory path contains sensitive indicators."""
    path_str = str(path).lower()
    basename = os.path.basename(path_str)

    if "sensitive_file_" in basename:
        return True

    if any(kw in basename for kw in _SENSITIVE_KEYWORDS):
        return True

    _, ext = os.path.splitext(basename)
    if ext in _SENSITIVE_EXTENSIONS:
        return True

    parent_dir = os.path.basename(os.path.dirname(path_str))
    if any(kw in parent_dir for kw in _SENSITIVE_KEYWORDS):
        return True

    return False


def is_authenticated_folder(path: str | Path) -> bool:
    """Checks if the destination path matches an authenticated secure folder."""
    path_str = str(path).lower()
    # Check environment variable override or name indicator
    secure_env = os.environ.get("CLEANSLATE_SECURE_FOLDER", "").lower()
    if secure_env and secure_env in path_str:
        return True
    return "authenticated" in path_str or "secure" in path_str
