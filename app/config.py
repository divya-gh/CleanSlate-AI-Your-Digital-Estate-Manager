import json
import os
import tempfile
from pathlib import Path

CONFIG_DIR = Path.home() / ".cleanslate"
CONFIG_FILE = CONFIG_DIR / "config.json"
POLICY_FILE = CONFIG_DIR / "policy.json"

DEFAULT_CONFIG = {"weekly_automation_enabled": False}


def ensure_config_dir() -> None:
    """Ensures ~/.cleanslate directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _save_file_atomic(path: Path, data_dict: dict) -> None:
    """Writes a dictionary to a path atomically by writing to a temp file and renaming it."""
    ensure_config_dir()
    tmp_path = None
    try:
        fd, tmp_file = tempfile.mkstemp(dir=CONFIG_DIR, suffix=".tmp", text=True)
        tmp_path = Path(tmp_file)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()  # nosemgrep: no-direct-file-deletes
            except Exception:
                pass
        raise e


def ensure_default_config() -> None:
    """Ensures config.json exists with default schema."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)


def ensure_default_policy() -> None:
    """Ensures policy.json exists with a basic structure if missing."""
    if not POLICY_FILE.exists():
        save_policy({"allowed_paths": [], "blocked_paths": [], "safe_mode": False})


def load_config() -> dict:
    """Loads config.json. Auto-repairs missing keys or creates it with defaults."""
    ensure_config_dir()
    ensure_default_config()
    try:
        with open(
            CONFIG_FILE, encoding="utf-8"
        ) as f:  # nosemgrep: no-file-content-reading, file-ops-must-use-folder-scope
            data = json.load(f)
        repaired = False
        if not isinstance(data, dict):
            data = {}
            repaired = True
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
                repaired = True
        if repaired:
            save_config(data)
        return data
    except Exception:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Saves the config dict atomically."""
    try:
        _save_file_atomic(CONFIG_FILE, config)
    except Exception:
        pass


_POLICY_OVERRIDE: dict | None = None


def set_policy_override(policy_dict: dict | None) -> None:
    """Sets a temporary in-memory policy override, useful for testing and node operations."""
    global _POLICY_OVERRIDE
    _POLICY_OVERRIDE = policy_dict


def load_policy() -> dict | None:
    """Loads the stored folder scope policy. Returns None if not configured."""
    global _POLICY_OVERRIDE
    if _POLICY_OVERRIDE is not None:
        return _POLICY_OVERRIDE
    ensure_config_dir()
    if not POLICY_FILE.exists():
        return None
    try:
        with open(
            POLICY_FILE, encoding="utf-8"
        ) as f:  # nosemgrep: no-file-content-reading, file-ops-must-use-folder-scope
            return json.load(f)
    except Exception:
        return None


def save_policy(policy_dict: dict) -> None:
    """Saves the folder scope policy dict atomically."""
    try:
        _save_file_atomic(POLICY_FILE, policy_dict)
    except Exception:
        pass


def reset_policy() -> None:
    """Clears the stored folder scope policy."""
    try:
        if POLICY_FILE.exists():
            POLICY_FILE.unlink()  # nosemgrep: no-direct-file-deletes
    except Exception:
        pass
