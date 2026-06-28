import json
from unittest.mock import MagicMock, patch

import pytest

from app.cli import (
    cmd_cleanup,
    cmd_logs,
    cmd_search,
    cmd_weekly_disable,
    cmd_weekly_enable,
    cmd_weekly_run,
)
from app.nodes.file_discovery_node import FolderScopePolicy


@pytest.fixture(autouse=True)
def mock_config_paths(tmp_path, monkeypatch):
    """Fixture to isolate config, policy, and execution log paths for tests."""
    mock_dir = tmp_path / ".cleanslate"
    mock_dir.mkdir()

    mock_config = mock_dir / "config.json"
    mock_policy = mock_dir / "policy.json"
    mock_last_exec = mock_dir / "last_execution.json"

    monkeypatch.setattr("app.config.CONFIG_DIR", mock_dir)
    monkeypatch.setattr("app.config.CONFIG_FILE", mock_config)
    monkeypatch.setattr("app.config.POLICY_FILE", mock_policy)

    monkeypatch.setattr("app.cli.CONFIG_DIR", mock_dir)
    monkeypatch.setattr("app.cli.LAST_EXEC_FILE", mock_last_exec)

    yield mock_dir, mock_config, mock_policy, mock_last_exec


def test_cli_weekly_enable_sets_flag(mock_config_paths):
    """Assert cleanslate weekly enable updates config.json."""
    _, mock_config, _, _ = mock_config_paths

    # Run the weekly enable command
    cmd_weekly_enable()

    assert mock_config.exists()
    with open(mock_config, encoding="utf-8") as f:
        data = json.load(f)
    assert data["weekly_automation_enabled"] is True


def test_cli_weekly_disable_sets_flag(mock_config_paths):
    """Assert cleanslate weekly disable updates config.json."""
    _, mock_config, _, _ = mock_config_paths

    # Write enabled state first
    with open(mock_config, "w", encoding="utf-8") as f:
        json.dump({"weekly_automation_enabled": True}, f)

    # Run the weekly disable command
    cmd_weekly_disable()

    with open(mock_config, encoding="utf-8") as f:
        data = json.load(f)
    assert data["weekly_automation_enabled"] is False


@patch("app.cli.weekly_organizer_node")
@patch("app.cli.file_discovery_node")
@patch("app.cli.classification_node")
@patch("app.cli.duplicate_detection_node")
@patch("app.cli.sensitive_detection_node")
@patch("app.cli.optimization_planner_node")
@patch("app.cli.summary_node")
def test_cli_weekly_run_respects_flag(
    mock_summary,
    mock_planner,
    mock_sensitive,
    mock_dedupe,
    mock_classify,
    mock_discovery,
    mock_organizer,
    mock_config_paths,
    capsys,
):
    """Assert cleanslate weekly-run early exits if disabled or runs nodes if enabled."""
    _mock_dir, mock_config, mock_policy, _ = mock_config_paths

    # 1. Test Disabled Case
    with open(mock_config, "w", encoding="utf-8") as f:
        json.dump({"weekly_automation_enabled": False}, f)

    with pytest.raises(SystemExit) as excinfo:
        cmd_weekly_run()
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "Weekly automation disabled." in captured.out
    assert not mock_organizer.called

    # 2. Test Enabled Case (when no pre-approved policy exists)
    with open(mock_config, "w", encoding="utf-8") as f:
        json.dump({"weekly_automation_enabled": True}, f)

    with pytest.raises(SystemExit) as excinfo:
        cmd_weekly_run()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "No pre-approved folder scope policy found." in captured.out

    # 3. Test Enabled and Policy Configured (WeeklyOrganizerNode triggers pipeline)
    # Write a dummy policy
    policy_data = {
        "allowed_paths": ["/tmp/allowed"],
        "blocked_paths": ["/tmp/blocked"],
        "safe_mode": True,
    }
    with open(mock_policy, "w", encoding="utf-8") as f:
        json.dump(policy_data, f)

    # Configure mock returns
    mock_organizer_event = MagicMock()
    mock_organizer_event.actions.route = "run"
    mock_organizer_event.output = MagicMock()
    mock_organizer.return_value = mock_organizer_event

    mock_disc_event = MagicMock()
    mock_disc_event.output = MagicMock()
    mock_discovery.return_value = mock_disc_event

    mock_classify_event = MagicMock()
    mock_classify_event.output = MagicMock()
    mock_classify.return_value = mock_classify_event

    mock_dedupe_out = MagicMock()
    mock_dedupe.return_value = mock_dedupe_out

    mock_sens_event = MagicMock()
    mock_sens_event.output = MagicMock()
    mock_sensitive.return_value = mock_sens_event

    mock_plan_event = MagicMock()
    mock_plan_event.actions.route = "no_actions"
    mock_plan_event.output.actions = []
    mock_plan_event.output.folder_scope_policy = FolderScopePolicy(
        allowed_paths=["/tmp/allowed"]
    )
    mock_plan_event.output.sensitive_files = []
    mock_planner.return_value = mock_plan_event

    mock_summary_out = MagicMock()
    mock_summary_out.human_readable_report = "Weekly Clean Report: OK"
    mock_summary.return_value = mock_summary_out

    cmd_weekly_run()
    captured = capsys.readouterr()
    assert "Weekly Clean Report: OK" in captured.out
    assert mock_organizer.called


@patch("app.cli.file_discovery_node")
def test_cli_search(mock_discovery, mock_config_paths, capsys):
    """Assert cleanslate search runs FileDiscoveryNode and outputs metadata."""
    _, _, mock_policy, _ = mock_config_paths

    # Setup dummy policy
    policy_data = {"allowed_paths": ["/tmp/allowed"], "blocked_paths": []}
    with open(mock_policy, "w", encoding="utf-8") as f:
        json.dump(policy_data, f)

    mock_file = MagicMock()
    mock_file.path = "/tmp/allowed/report.pdf"
    mock_file.size = 2048
    mock_file.model_dump.return_value = {
        "path": "/tmp/allowed/report.pdf",
        "size": 2048,
    }

    mock_event = MagicMock()
    mock_event.output.file_inventory = [mock_file]
    mock_discovery.return_value = mock_event

    # 1. Plain Text Output
    cmd_search("report")
    captured = capsys.readouterr()
    assert "Discovered 1 matching files:" in captured.out
    assert "report.pdf" in captured.out

    # 2. JSON Output
    cmd_search("report", json_opt=True)
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert len(res) == 1
    assert res[0]["path"] == "/tmp/allowed/report.pdf"


@patch("app.cli.file_discovery_node")
@patch("app.cli.classification_node")
@patch("app.cli.duplicate_detection_node")
@patch("app.cli.sensitive_detection_node")
@patch("app.cli.optimization_planner_node")
@patch("app.cli.summary_node")
@patch("builtins.input", return_value="yes")
def test_cli_cleanup_dry_run(
    mock_input,
    mock_summary,
    mock_planner,
    mock_sensitive,
    mock_dedupe,
    mock_classify,
    mock_discovery,
    mock_config_paths,
    capsys,
):
    """Assert cleanslate cleanup with --dry-run triggers dry run executions."""
    _, _, mock_policy, _ = mock_config_paths

    policy_data = {"allowed_paths": ["/tmp/allowed"], "blocked_paths": []}
    with open(mock_policy, "w", encoding="utf-8") as f:
        json.dump(policy_data, f)

    mock_discovery.return_value = MagicMock()
    mock_classify.return_value = MagicMock()
    mock_dedupe.return_value = MagicMock()
    mock_sensitive.return_value = MagicMock()

    from app.nodes.hitl_approval_node import CleanupAction

    action = CleanupAction(
        path="/tmp/allowed/junk.txt",
        action_type="delete",
        reasoning="temp file",
        estimated_space_recovered=500,
        safe_to_delete=True,
        confidence=0.9,
    )

    mock_plan_event = MagicMock()
    mock_plan_event.actions.route = "execute"
    mock_plan_event.output.actions = [action]
    mock_plan_event.output.folder_scope_policy = FolderScopePolicy(
        allowed_paths=["/tmp/allowed"]
    )
    mock_plan_event.output.sensitive_files = []
    mock_plan_event.output.estimated_space_recovered = 500
    mock_planner.return_value = mock_plan_event

    mock_summary_out = MagicMock()
    mock_summary_out.human_readable_report = "Dry-run report summary details."
    mock_summary.return_value = mock_summary_out

    cmd_cleanup(dry_run=True)
    captured = capsys.readouterr()
    assert "Proposed Optimization Plan" in captured.out
    assert "Dry-run report summary details." in captured.out


def test_cli_logs_limit(tmp_path, monkeypatch, capsys):
    """Assert cleanslate logs respects limit options."""
    mock_log = tmp_path / "audit.log"
    monkeypatch.setenv("CLEANSLATE_LOG_PATH", str(mock_log))

    # Write dummy logs
    with open(mock_log, "w", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "timestamp": "2026-06-27T22:00:00Z",
                    "node": "NodeA",
                    "action_type": "move",
                    "result": "success",
                }
            )
            + "\n"
        )
        f.write(
            json.dumps(
                {
                    "timestamp": "2026-06-27T22:01:00Z",
                    "node": "NodeB",
                    "action_type": "delete",
                    "result": "skipped",
                }
            )
            + "\n"
        )

    # Limit to 1
    cmd_logs(limit=1)
    captured = capsys.readouterr()
    assert "Showing last 1 log entries" in captured.out
    assert "NodeB" in captured.out
    assert "NodeA" not in captured.out
