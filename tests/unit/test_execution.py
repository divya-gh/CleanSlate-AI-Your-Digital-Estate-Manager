import zipfile
from unittest.mock import patch

from app.nodes.execution_node import execution_node
from app.nodes.file_discovery_node import FolderScopePolicy
from app.nodes.hitl_approval_node import CleanupAction, HITLApprovalOutput
from app.nodes.sensitive_detection_node import SensitiveFileEntry


@patch("app.nodes.execution_node.test_tool")
def test_execution_dry_run(mock_test_tool) -> None:
    mock_test_tool.return_value = {"result": {"sha256": "abc"}, "status": "success"}

    policy = FolderScopePolicy(
        allowed_paths=["/allowed"],
        blocked_paths=["/allowed/blocked"],
    )

    actions = [
        CleanupAction(
            path="/allowed/dup.txt",
            action_type="delete",
            reasoning="duplicate",
            estimated_space_recovered=1000,
            safe_to_delete=True,
            confidence=0.95,
        )
    ]

    node_input = HITLApprovalOutput(
        approved_actions=actions,
        folder_scope_policy=policy,
        sensitive_files=[],
        dry_run=True,
        reasoning="User approved",
    )

    output = execution_node(node_input).output
    assert len(output.execution_log) == 1
    log = output.execution_log[0]
    assert log.path == "/allowed/dup.txt"
    assert log.status == "success"
    assert log.dry_run is True
    assert "Dry-run simulation" in log.reasoning
    assert mock_test_tool.called


def test_execution_real_run(tmp_path) -> None:
    # 1. Setup folders
    allowed_dir = tmp_path / "allowed"
    blocked_dir = tmp_path / "blocked"
    allowed_dir.mkdir()
    blocked_dir.mkdir()

    # Files on disk
    file_delete = allowed_dir / "delete_me.txt"
    file_move = allowed_dir / "move_me.txt"
    file_compress = allowed_dir / "compress_me.txt"
    file_archive = allowed_dir / "archive_me.txt"
    file_blocked = blocked_dir / "blocked_file.txt"
    file_sensitive = allowed_dir / "sensitive_delete.txt"
    file_untouched = allowed_dir / "untouched.txt"

    file_delete.write_text("delete contents")
    file_move.write_text("move contents")
    file_compress.write_text("compress contents")
    file_archive.write_text("archive contents")
    file_blocked.write_text("blocked contents")
    file_sensitive.write_text("sensitive contents")
    file_untouched.write_text("untouched contents")

    # Define policy
    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[str(blocked_dir)],
    )

    # Actions list
    actions = [
        # Successful delete
        CleanupAction(
            path=str(file_delete),
            action_type="delete",
            reasoning="redundant",
            estimated_space_recovered=100,
            safe_to_delete=True,
            confidence=0.95,
        ),
        # Successful move
        CleanupAction(
            path=str(file_move),
            action_type="move",
            reasoning="organize",
            estimated_space_recovered=0,
            safe_to_delete=False,
            confidence=0.8,
        ),
        # Successful compress
        CleanupAction(
            path=str(file_compress),
            action_type="compress",
            reasoning="large text",
            estimated_space_recovered=50,
            safe_to_delete=False,
            confidence=0.75,
        ),
        # Successful archive
        CleanupAction(
            path=str(file_archive),
            action_type="archive",
            reasoning="old file",
            estimated_space_recovered=0,
            safe_to_delete=False,
            confidence=0.70,
        ),
        # FAILED: sensitive file deletion guard
        CleanupAction(
            path=str(file_sensitive),
            action_type="delete",
            reasoning="sensitive delete",
            estimated_space_recovered=100,
            safe_to_delete=True,
            confidence=0.95,
        ),
        # FAILED: blocked path guard
        CleanupAction(
            path=str(file_blocked),
            action_type="delete",
            reasoning="blocked delete",
            estimated_space_recovered=100,
            safe_to_delete=True,
            confidence=0.95,
        ),
    ]

    sensitive_files = [
        SensitiveFileEntry(
            path=str(file_sensitive),
            sensitive=True,
            sensitivity_type="tax",
            confidence=0.95,
            reasoning="tax info",
        )
    ]

    node_input = HITLApprovalOutput(
        approved_actions=actions,
        folder_scope_policy=policy,
        sensitive_files=sensitive_files,
        dry_run=False,
        reasoning="Approved",
    )

    # Execute Node (dry_run=False)
    output = execution_node(node_input).output

    # Assertions on logs
    assert len(output.execution_log) == 6
    log_lookup = {entry.path: entry for entry in output.execution_log}

    # Delete assertion
    delete_log = log_lookup[str(file_delete)]
    assert delete_log.status == "success"
    assert not file_delete.exists()
    assert delete_log.original_path == str(file_delete)
    assert delete_log.new_path is None
    assert delete_log.backup_path == str(allowed_dir / ".rollback" / "delete_me.txt")
    assert delete_log.rollback_supported is True
    assert (allowed_dir / ".rollback" / "delete_me.txt").exists()
    assert (
        allowed_dir / ".rollback" / "delete_me.txt"
    ).read_text() == "delete contents"

    # Move assertion
    move_log = log_lookup[str(file_move)]
    assert move_log.status == "success"
    assert not file_move.exists()
    assert (allowed_dir / "Organized" / "move_me.txt").exists()
    assert move_log.original_path == str(file_move)
    assert move_log.new_path == str(allowed_dir / "Organized" / "move_me.txt")
    assert move_log.backup_path is None
    assert move_log.rollback_supported is True

    # Compress assertion
    compress_log = log_lookup[str(file_compress)]
    assert compress_log.status == "success"
    assert not file_compress.exists()
    zip_file = allowed_dir / "compress_me.txt.zip"
    assert zip_file.exists()
    with zipfile.ZipFile(zip_file, "r") as zf:
        assert "compress_me.txt" in zf.namelist()
    assert compress_log.original_path == str(file_compress)
    assert compress_log.new_path == str(zip_file)
    assert compress_log.backup_path is None
    assert compress_log.rollback_supported is False

    # Archive assertion
    archive_log = log_lookup[str(file_archive)]
    assert archive_log.status == "success"
    assert not file_archive.exists()
    assert (allowed_dir / "Archive" / "archive_me.txt").exists()
    assert archive_log.original_path == str(file_archive)
    assert archive_log.new_path == str(allowed_dir / "Archive" / "archive_me.txt")
    assert archive_log.backup_path is None
    assert archive_log.rollback_supported is True

    # Sensitive delete double-guard assertion
    assert log_lookup[str(file_sensitive)].status == "failure"
    assert (
        "sensitive files must never be deleted"
        in log_lookup[str(file_sensitive)].reasoning.lower()
    )
    assert file_sensitive.exists()

    # Blocked double-guard assertion
    assert log_lookup[str(file_blocked)].status == "failure"
    assert "blocked directories" in log_lookup[str(file_blocked)].reasoning.lower()
    assert file_blocked.exists()

    # Double guard untouched file: should never have been touched
    assert file_untouched.exists()

    # Node output verification
    assert output.dry_run is False
    assert output.rollback_enabled is True


def test_execution_never_touches_unapproved_files(tmp_path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    file_approved = allowed_dir / "approved.txt"
    file_unapproved = allowed_dir / "unapproved.txt"

    file_approved.write_text("approved content")
    file_unapproved.write_text("unapproved content")

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[],
    )

    # Only approved.txt is in approved_actions
    actions = [
        CleanupAction(
            path=str(file_approved),
            action_type="delete",
            reasoning="approved action",
            estimated_space_recovered=len("approved content"),
            safe_to_delete=True,
            confidence=1.0,
        )
    ]

    node_input = HITLApprovalOutput(
        approved_actions=actions,
        folder_scope_policy=policy,
        sensitive_files=[],
        dry_run=False,
        reasoning="Runapproved",
    )

    output = execution_node(node_input).output

    # approved.txt should be deleted
    assert not file_approved.exists()
    # unapproved.txt MUST NOT be touched
    assert file_unapproved.exists()
    assert file_unapproved.read_text() == "unapproved content"

    # Assert log does not contain unapproved file
    assert any(log.path == str(file_approved) for log in output.execution_log)
    assert not any(log.path == str(file_unapproved) for log in output.execution_log)
