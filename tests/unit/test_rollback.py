from app.nodes.execution_node import ExecutionLogEntry, ExecutionOutput
from app.nodes.file_discovery_node import FolderScopePolicy
from app.nodes.rollback_node import rollback_node


def test_rollback_dry_run() -> None:
    policy = FolderScopePolicy(
        allowed_paths=["/allowed"],
        blocked_paths=["/allowed/blocked"],
    )

    log_entries = [
        ExecutionLogEntry(
            path="/allowed/delete_me.txt",
            action_type="delete",
            status="success",
            timestamp=123.45,
            reasoning="redundant",
            dry_run=False,
            original_path="/allowed/delete_me.txt",
            backup_path="/allowed/.rollback/delete_me.txt",
            rollback_supported=True,
        ),
        ExecutionLogEntry(
            path="/allowed/move_me.txt",
            action_type="move",
            status="success",
            timestamp=123.45,
            reasoning="organize",
            dry_run=False,
            original_path="/allowed/move_me.txt",
            new_path="/allowed/Organized/move_me.txt",
            rollback_supported=True,
        ),
        ExecutionLogEntry(
            path="/allowed/compress_me.txt",
            action_type="compress",
            status="success",
            timestamp=123.45,
            reasoning="large file",
            dry_run=False,
            original_path="/allowed/compress_me.txt",
            new_path="/allowed/compress_me.txt.zip",
            rollback_supported=False,
        ),
    ]

    node_input = ExecutionOutput(
        execution_log=log_entries,
        reasoning="Ran execution",
        dry_run=True,
        folder_scope_policy=policy,
        sensitive_files=[],
    )

    output = rollback_node(node_input)
    summary = output.rollback_summary

    assert summary.attempted == 2
    assert summary.succeeded == 2
    assert summary.failed == 0
    assert summary.unsupported == 1
    assert summary.dry_run is True
    assert "[Simulated] Restored" in summary.human_readable_report
    assert "delete_me.txt" in summary.human_readable_report
    assert "move_me.txt" in summary.human_readable_report
    # Ensure absolute path /allowed/ is not in the human readable report
    assert "/allowed/" not in summary.human_readable_report


def test_rollback_real_run(tmp_path) -> None:
    allowed_dir = tmp_path / "allowed"
    blocked_dir = tmp_path / "blocked"
    allowed_dir.mkdir()
    blocked_dir.mkdir()

    # Create dummy file destinations
    orig_delete = allowed_dir / "delete_me.txt"
    backup_delete = allowed_dir / ".rollback" / "delete_me.txt"
    backup_delete.parent.mkdir(parents=True, exist_ok=True)
    backup_delete.write_text("deleted content")

    orig_move = allowed_dir / "move_me.txt"
    new_move = allowed_dir / "Organized" / "move_me.txt"
    new_move.parent.mkdir(parents=True, exist_ok=True)
    new_move.write_text("moved content")

    orig_archive = allowed_dir / "archive_me.txt"
    new_archive = allowed_dir / "Archive" / "archive_me.txt"
    new_archive.parent.mkdir(parents=True, exist_ok=True)
    new_archive.write_text("archived content")

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[str(blocked_dir)],
    )

    log_entries = [
        ExecutionLogEntry(
            path=str(orig_delete),
            action_type="delete",
            status="success",
            timestamp=123.45,
            reasoning="redundant",
            dry_run=False,
            original_path=str(orig_delete),
            backup_path=str(backup_delete),
            rollback_supported=True,
        ),
        ExecutionLogEntry(
            path=str(orig_move),
            action_type="move",
            status="success",
            timestamp=123.45,
            reasoning="organize",
            dry_run=False,
            original_path=str(orig_move),
            new_path=str(new_move),
            rollback_supported=True,
        ),
        ExecutionLogEntry(
            path=str(orig_archive),
            action_type="archive",
            status="success",
            timestamp=123.45,
            reasoning="organize",
            dry_run=False,
            original_path=str(orig_archive),
            new_path=str(new_archive),
            rollback_supported=True,
        ),
    ]

    node_input = ExecutionOutput(
        execution_log=log_entries,
        reasoning="Ran execution",
        dry_run=False,
        folder_scope_policy=policy,
        sensitive_files=[],
    )

    output = rollback_node(node_input)
    summary = output.rollback_summary

    assert summary.attempted == 3
    assert summary.succeeded == 3
    assert summary.failed == 0
    assert summary.dry_run is False

    # Check files restored
    assert orig_delete.exists()
    assert orig_delete.read_text() == "deleted content"
    # Verify backup file NOT deleted (audit check)
    assert backup_delete.exists()

    assert orig_move.exists()
    assert orig_move.read_text() == "moved content"
    assert not new_move.exists()

    assert orig_archive.exists()
    assert orig_archive.read_text() == "archived content"
    assert not new_archive.exists()


def test_rollback_overwrite_prevention(tmp_path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    orig_delete = allowed_dir / "delete_me.txt"
    orig_delete.write_text("existing occupier")  # Occupies original path

    backup_delete = allowed_dir / ".rollback" / "delete_me.txt"
    backup_delete.parent.mkdir(parents=True, exist_ok=True)
    backup_delete.write_text("deleted content")

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[],
    )

    log_entries = [
        ExecutionLogEntry(
            path=str(orig_delete),
            action_type="delete",
            status="success",
            timestamp=123.45,
            reasoning="redundant",
            dry_run=False,
            original_path=str(orig_delete),
            backup_path=str(backup_delete),
            rollback_supported=True,
        )
    ]

    node_input = ExecutionOutput(
        execution_log=log_entries,
        reasoning="Ran execution",
        dry_run=False,
        folder_scope_policy=policy,
        sensitive_files=[],
    )

    output = rollback_node(node_input)
    summary = output.rollback_summary

    assert summary.failed == 1
    assert summary.succeeded == 0
    # Existing file should NOT be overwritten
    assert orig_delete.read_text() == "existing occupier"
    assert len(output.errors) == 1
    assert "Overwrite prevention" in output.errors[0]


def test_rollback_missing_backup_gracefully(tmp_path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    orig_delete = allowed_dir / "delete_me.txt"
    # No backup exists

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[],
    )

    log_entries = [
        ExecutionLogEntry(
            path=str(orig_delete),
            action_type="delete",
            status="success",
            timestamp=123.45,
            reasoning="redundant",
            dry_run=False,
            original_path=str(orig_delete),
            backup_path=str(allowed_dir / ".rollback" / "delete_me.txt"),
            rollback_supported=True,
        )
    ]

    node_input = ExecutionOutput(
        execution_log=log_entries,
        reasoning="Ran execution",
        dry_run=False,
        folder_scope_policy=policy,
        sensitive_files=[],
    )

    output = rollback_node(node_input)
    summary = output.rollback_summary

    assert summary.failed == 1
    assert not orig_delete.exists()
    assert len(output.errors) == 1
    assert (
        "FileNotFoundError" in output.errors[0]
        or "not found" in output.errors[0].lower()
    )


def test_rollback_safety_guards(tmp_path) -> None:
    allowed_dir = tmp_path / "allowed"
    blocked_dir = tmp_path / "blocked"
    allowed_dir.mkdir()
    blocked_dir.mkdir()

    # Under blocked path
    orig_blocked = blocked_dir / "blocked.txt"
    # Outside allowed
    orig_outside = tmp_path / "outside.txt"

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[str(blocked_dir)],
    )

    log_entries = [
        ExecutionLogEntry(
            path=str(orig_blocked),
            action_type="delete",
            status="success",
            timestamp=123.45,
            reasoning="redundant",
            dry_run=False,
            original_path=str(orig_blocked),
            backup_path=str(allowed_dir / "backup1.txt"),
            rollback_supported=True,
        ),
        ExecutionLogEntry(
            path=str(orig_outside),
            action_type="delete",
            status="success",
            timestamp=123.45,
            reasoning="redundant",
            dry_run=False,
            original_path=str(orig_outside),
            backup_path=str(allowed_dir / "backup2.txt"),
            rollback_supported=True,
        ),
    ]

    node_input = ExecutionOutput(
        execution_log=log_entries,
        reasoning="Ran execution",
        dry_run=False,
        folder_scope_policy=policy,
        sensitive_files=[],
    )

    output = rollback_node(node_input)
    summary = output.rollback_summary

    assert summary.failed == 2
    assert summary.succeeded == 0
    assert len(output.errors) == 2
    assert "outside" in output.errors[0]
    assert "blocked" in output.errors[1]


def test_rollback_recreate_parent_directory(tmp_path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    # Original path is inside a nested folder that got removed
    nested_dir = allowed_dir / "nested" / "folder"
    orig_path = nested_dir / "file.txt"

    backup_path = allowed_dir / ".rollback" / "file.txt"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text("nested content")

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[],
    )

    log_entries = [
        ExecutionLogEntry(
            path=str(orig_path),
            action_type="delete",
            status="success",
            timestamp=123.45,
            reasoning="redundant",
            dry_run=False,
            original_path=str(orig_path),
            backup_path=str(backup_path),
            rollback_supported=True,
        )
    ]

    node_input = ExecutionOutput(
        execution_log=log_entries,
        reasoning="Ran execution",
        dry_run=False,
        folder_scope_policy=policy,
        sensitive_files=[],
    )

    output = rollback_node(node_input)
    summary = output.rollback_summary

    assert summary.succeeded == 1
    assert orig_path.exists()
    assert orig_path.read_text() == "nested content"
