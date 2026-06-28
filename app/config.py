import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".cleanslate"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {"weekly_automation_enabled": False}


def load_config() -> dict:
    """Loads config.json. Creates it with defaults if missing."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(
            CONFIG_FILE, encoding="utf-8"
        ) as f:  # nosemgrep: no-file-content-reading, file-ops-must-use-folder-scope
            data = json.load(f)
            # Ensure correct keys exist
            if "weekly_automation_enabled" not in data:
                data["weekly_automation_enabled"] = False
            return data
    except Exception:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Saves the config dict to ~/.cleanslate/config.json."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        # Silently fail or log if unable to save
        pass


POLICY_FILE = CONFIG_DIR / "policy.json"


def load_policy() -> dict | None:
    """Loads the stored folder scope policy. Returns None if not configured."""
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
    """Saves the folder scope policy dict to ~/.cleanslate/policy.json."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(POLICY_FILE, "w", encoding="utf-8") as f:
            json.dump(policy_dict, f, indent=2)
    except Exception:
        pass


def reset_policy() -> None:
    """Clears the stored folder scope policy."""
    try:
        if POLICY_FILE.exists():
            POLICY_FILE.unlink()  # nosemgrep: no-direct-file-deletes
    except Exception:
        pass
