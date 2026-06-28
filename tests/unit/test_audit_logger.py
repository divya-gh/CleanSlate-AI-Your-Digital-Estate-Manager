import json
import os
from datetime import datetime

import pytest

from app.security.audit_logger import LOG_PATH, log_action


@pytest.fixture(autouse=True)
def clean_audit_log():
    """Fixture to ensure the audit log file is clean before and after each test."""
    if os.path.exists(LOG_PATH):
        try:
            os.remove(LOG_PATH)
        except OSError:
            pass
    yield
    if os.path.exists(LOG_PATH):
        try:
            os.remove(LOG_PATH)
        except OSError:
            pass


def test_log_action_non_sensitive_path():
    """Test that a non-sensitive absolute path is redacted to parent/basename."""
    test_path = os.path.abspath("some_folder/my_file.txt")
    log_action(
        node="TestNode",
        action_type="move",
        path=test_path,
        is_sensitive=False,
        hitl_status="approved",
        result="success",
        reason="Testing non-sensitive path redaction.",
    )

    assert os.path.exists(LOG_PATH)
    with open(LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])

        assert entry["node"] == "TestNode"
        assert entry["action_type"] == "move"
        assert entry["hitl_status"] == "approved"
        assert entry["result"] == "success"
        assert entry["reason"] == "Testing non-sensitive path redaction."

        # Verify path redaction (only parent/basename, never absolute path)
        assert entry["path"] == "some_folder/my_file.txt"
        assert "cleanslate-pc-assistant" not in entry["path"]
        assert ":" not in entry["path"]


def test_log_action_sensitive_path():
    """Test that sensitive files are completely redacted to '<sensitive file>'."""
    test_path = os.path.abspath("sensitive_data/confidential.pdf")
    log_action(
        node="TestNode",
        action_type="delete",
        path=test_path,
        is_sensitive=True,
        hitl_status="not_required",
        result="success",
        reason="Testing sensitive path redaction.",
        backup_path=os.path.abspath("rollback_dir/confidential.pdf"),
    )

    assert os.path.exists(LOG_PATH)
    with open(LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
        entry = json.loads(lines[0])

        assert entry["path"] == "<sensitive file>"
        assert entry["backup_path"] == "<sensitive backup>"


def test_log_action_append_only():
    """Test that log entries append to the file rather than overwriting it."""
    log_action(
        node="NodeA",
        action_type="archive",
        path="foo/bar.txt",
        is_sensitive=False,
        hitl_status="approved",
        result="success",
    )
    log_action(
        node="NodeB",
        action_type="compress",
        path="baz/qux.txt",
        is_sensitive=False,
        hitl_status="approved",
        result="success",
    )

    with open(LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 2
        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])

        assert entry1["node"] == "NodeA"
        assert entry2["node"] == "NodeB"


def test_log_action_timestamps():
    """Test that timestamps are valid UTC ISO-formatted strings."""
    log_action(
        node="TestNode",
        action_type="plan",
        path=None,
        is_sensitive=False,
        hitl_status="not_required",
        result="success",
    )

    with open(LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
        entry = json.loads(lines[0])

        timestamp_str = entry["timestamp"]
        # Should be ISO formatted UTC string
        dt = datetime.fromisoformat(timestamp_str)
        assert dt.tzinfo is not None
