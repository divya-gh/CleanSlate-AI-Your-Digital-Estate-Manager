import os
import shutil
from unittest.mock import MagicMock

from app.nodes.execution_node import ExecutionLogEntry, ExecutionOutput
from app.nodes.file_discovery_node import FolderScopePolicy
from app.nodes.sensitive_detection_node import SensitiveFileEntry
from app.nodes.summary_node import summary_node


def test_summary_aggregation_dry_run() -> None:
    policy = FolderScopePolicy(
        allowed_paths=["/allowed"],
        blocked_paths=["/allowed/blocked"],
    )

    sensitive_files = [
        SensitiveFileEntry(
            path="/allowed/sensitive.txt",
            sensitive=True,
            sensitivity_type="banking",
            confidence=0.95,
            reasoning="banking statement",
        )
    ]

    log_entries = [
        ExecutionLogEntry(
            path="/allowed/dup.txt",
            action_type="delete",
            status="success",
            timestamp=12345.67,
            reasoning="redundant file",
            dry_run=True,
            original_path="/allowed/dup.txt",
            new_path=None,
            backup_path="/allowed/.rollback/dup.txt",
            rollback_supported=True,
        ),
        ExecutionLogEntry(
            path="/allowed/sensitive.txt",
            action_type="delete",
            status="failure",
            timestamp=12345.67,
            reasoning="Runtime Safety Check: Sensitive files must never be deleted.",
            dry_run=True,
            original_path="/allowed/sensitive.txt",
            new_path=None,
            backup_path=None,
            rollback_supported=False,
        ),
        ExecutionLogEntry(
            path="/allowed/blocked/file.txt",
            action_type="delete",
            status="failure",
            timestamp=12345.67,
            reasoning="Runtime Safety Check: Target path is inside blocked directories.",
            dry_run=True,
            original_path="/allowed/blocked/file.txt",
            new_path=None,
            backup_path=None,
            rollback_supported=False,
        ),
        ExecutionLogEntry(
            path="/allowed/compress_me.txt",
            action_type="compress",
            status="success",
            timestamp=12345.68,
            reasoning="large log",
            dry_run=True,
            original_path="/allowed/compress_me.txt",
            new_path="/allowed/compress_me.txt.zip",
            backup_path=None,
            rollback_supported=False,
        ),
    ]

    node_input = ExecutionOutput(
        execution_log=log_entries,
        reasoning="Executed batch",
        original_path="",
        new_path=None,
        backup_path=None,
        rollback_supported=False,
        dry_run=True,
        rollback_enabled=True,
        folder_scope_policy=policy,
        sensitive_files=sensitive_files,
        estimated_recovery=5000,
    )

    output = summary_node(node_input)

    # 1. Verification of Aggregates
    assert output.total_actions == 4
    assert output.successful_actions == 2
    assert output.skipped_actions == 2  # Blocked by safety checks
    assert output.failed_actions == 0
    assert output.estimated_recovery == 5000
    assert output.dry_run is True
    assert output.sensitive_files_protected == 1
    assert output.rollback_supported_actions == 1
    assert output.rollback_unsupported_actions == 3

    # 2. Verification of Safety Filters
    report = output.human_readable_report
    assert "• Dry-Run Active:           True" in report
    assert "All protected safely" in report
    assert "/allowed/blocked/file.txt" not in report
    assert "a protected file" in report
    assert "♻️ ROLLBACK CAPABILITY" in report
    assert "🧪 DRY-RUN MODE" in report

    # Check absolute system/blocked path leaks are prevented
    assert "/allowed/blocked/file.txt" not in report

    # Check sensitive files leaks are prevented
    assert "sensitive.txt" not in report
    assert "banking" not in report
    assert "banking statement" not in report
    assert "• Sensitive Files Protected: 1" in report


def test_summary_real_run_failed_action() -> None:
    policy = FolderScopePolicy(
        allowed_paths=["/allowed"],
        blocked_paths=[],
    )

    log_entries = [
        ExecutionLogEntry(
            path="/allowed/missing.txt",
            action_type="delete",
            status="failure",
            timestamp=12345.67,
            reasoning="File not found on disk at time of execution.",
            dry_run=False,
            original_path="/allowed/missing.txt",
            new_path=None,
            backup_path=None,
            rollback_supported=False,
        )
    ]

    node_input = ExecutionOutput(
        execution_log=log_entries,
        reasoning="Failed batch",
        original_path="",
        new_path=None,
        backup_path=None,
        rollback_supported=False,
        dry_run=False,
        rollback_enabled=True,
        folder_scope_policy=policy,
        sensitive_files=[],
        estimated_recovery=0,
    )

    output = summary_node(node_input)

    assert output.total_actions == 1
    assert output.successful_actions == 0
    assert output.failed_actions == 1
    assert output.skipped_actions == 0
    assert output.dry_run is False
    assert len(output.errors) == 1
    assert "missing.txt" in output.errors[0]
    assert "Dry Run Mode" not in output.human_readable_report


def test_summary_pure_reporting(monkeypatch) -> None:
    policy = FolderScopePolicy(
        allowed_paths=["/allowed"],
        blocked_paths=[],
    )

    node_input = ExecutionOutput(
        execution_log=[],
        reasoning="Empty batch",
        original_path="",
        new_path=None,
        backup_path=None,
        rollback_supported=False,
        dry_run=False,
        rollback_enabled=True,
        folder_scope_policy=policy,
        sensitive_files=[],
        estimated_recovery=0,
    )

    # Mock critical file-modifying methods
    mock_remove = MagicMock()
    mock_move = MagicMock()
    monkeypatch.setattr(os, "remove", mock_remove)
    monkeypatch.setattr(shutil, "move", mock_move)

    # Run the node
    summary_node(node_input)

    # Assert no destructive/modifying methods were invoked
    mock_remove.assert_not_called()
    mock_move.assert_not_called()
