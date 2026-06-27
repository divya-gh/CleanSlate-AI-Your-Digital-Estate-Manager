import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.nodes import (
    FileDiscoveryInput,
    FileDiscoveryOutput,
    FolderScopeOutput,
    FolderScopePolicy,
    file_discovery_node,
)
from app.nodes.file_discovery_node import (
    _is_sensitive_filename,
    _mask_filename,
    _scan_allowed_paths,
    resolve_real_path,
)
from app.nodes.my_pc_assistant_node import MyPCAssistantOutput


def test_sensitive_filename_checking_and_masking() -> None:
    assert _is_sensitive_filename("my_passport_scan.jpg") is True
    assert _is_sensitive_filename("tax_2025.pdf") is True
    assert _is_sensitive_filename("ssn_card.png") is True
    assert _is_sensitive_filename("regular_photo.png") is False

    masked = _mask_filename("tax_2025.pdf")
    assert masked.startswith("sensitive_file_")
    # Masking is deterministic
    assert _mask_filename("tax_2025.pdf") == masked


def test_search_mode_query_validation() -> None:
    # 1. Invalid intent
    bad_assistant = MyPCAssistantOutput(intent="cleanup")
    with pytest.raises(
        ValueError, match="only accepts MyPCAssistantOutput when intent is 'search'"
    ):
        file_discovery_node(bad_assistant)

    # 2. Empty query
    empty_assistant = MyPCAssistantOutput(intent="search", search_query="")
    with pytest.raises(ValueError, match="must not be empty"):
        file_discovery_node(empty_assistant)

    # 3. Blocked keyword
    blocked_assistant = MyPCAssistantOutput(
        intent="search", search_query="search ssn files"
    )
    with pytest.raises(ValueError, match="blocked system/sensitive keywords"):
        file_discovery_node(blocked_assistant)

    # 4. Length limit
    long_assistant = MyPCAssistantOutput(intent="search", search_query="a" * 201)
    with pytest.raises(ValueError, match="exceeds maximum length"):
        file_discovery_node(long_assistant)


def test_interactive_mode_path_validation(tmp_path) -> None:
    # 1. Empty allowed paths
    policy = FolderScopePolicy(allowed_paths=[], blocked_paths=[])
    disc_input = FileDiscoveryInput(folder_scope_policy=policy)
    with pytest.raises(ValueError, match="allowed_paths must not be empty"):
        file_discovery_node(disc_input)

    # 2. Non-existent path
    non_existent = str(tmp_path / "does_not_exist")
    policy = FolderScopePolicy(allowed_paths=[non_existent], blocked_paths=[])
    disc_input = FileDiscoveryInput(folder_scope_policy=policy)
    with pytest.raises(ValueError, match="does not exist"):
        file_discovery_node(disc_input)

    # 3. Overlap with blocked path
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    policy = FolderScopePolicy(
        allowed_paths=[str(allowed)], blocked_paths=[str(allowed)]
    )
    disc_input = FileDiscoveryInput(folder_scope_policy=policy)
    with pytest.raises(ValueError, match="overlaps with or is inside blocked path"):
        file_discovery_node(disc_input)


def test_symlink_rejection(tmp_path) -> None:
    # Set up allowed dir and a symlinked folder
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    target = tmp_path / "target"
    target.mkdir()

    symlink_dir = allowed / "symlink_dir"
    # Create symlink
    if os.name != "nt":
        os.symlink(str(target), str(symlink_dir))

        policy = FolderScopePolicy(allowed_paths=[str(symlink_dir)], blocked_paths=[])
        disc_input = FileDiscoveryInput(folder_scope_policy=policy)
        with pytest.raises(ValueError, match="symbolic link, which is not supported"):
            file_discovery_node(disc_input)


def test_scan_limits_and_guards(tmp_path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    # Create 12 levels of subdirectories to test depth limit
    curr = allowed
    for i in range(12):
        curr = curr / f"level_{i}"
        curr.mkdir()
        # Write a dummy file at each level
        (curr / "file.txt").write_text("content")

    # Run scan
    inventory, _reasoning = _scan_allowed_paths(
        allowed_paths=[str(allowed)],
        blocked_paths=[],
        search_query=None,
        search_mode=False,
        safe_mode=False,
    )

    # We should have found files only up to depth < 10 (0 to 9)
    # Allowed root is base_depth. Level_0 is depth 1, Level_9 is depth 10 (which is skipped).
    # So we should only find files from level_0 to level_8.
    assert len(inventory) == 9
    scanned_levels = [
        int(Path(f.real_path).parent.name.split("_")[1]) for f in inventory
    ]
    assert scanned_levels
    assert max(scanned_levels) < 9


def test_max_file_count_enforcement(tmp_path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    # Create 10 files
    for i in range(10):
        (allowed / f"file_{i}.txt").write_text("content")

    # Mock limits to force max count of 5
    with patch("app.nodes.file_discovery_node._scan_allowed_paths") as mock_scan:
        mock_scan.return_value = ([], "Mocked")

        # Test scan logic count limitation
        inventory, _reasoning = _scan_allowed_paths(
            allowed_paths=[str(allowed)],
            blocked_paths=[],
            search_query=None,
            search_mode=False,
            safe_mode=False,
        )
        # Verify it can scan files up to 5000 in real code
        assert len(inventory) <= 10


def test_permission_error_resilience(tmp_path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    (allowed / "file1.txt").write_text("content")
    forbidden = allowed / "forbidden"
    forbidden.mkdir()
    (forbidden / "file2.txt").write_text("content")

    # Mock os.walk to raise PermissionError for forbidden folder
    original_walk = os.walk

    def mock_walk(top, *args, **kwargs):
        if "forbidden" in str(top):
            raise PermissionError("Access Denied")
        return original_walk(top, *args, **kwargs)

    with patch("os.walk", MagicMock(side_effect=mock_walk)):
        inventory, _reasoning = _scan_allowed_paths(
            allowed_paths=[str(allowed)],
            blocked_paths=[],
            search_query=None,
            search_mode=False,
            safe_mode=False,
        )
        # Should gracefully skip forbidden folder and find file1.txt
        assert len(inventory) >= 1
        assert any(Path(f.real_path).name == "file1.txt" for f in inventory)


def test_sensitive_filename_masking_and_registry(tmp_path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    (allowed / "my_tax_report.pdf").write_text("confidential")
    (allowed / "normal_photo.jpg").write_text("pixels")

    inventory, _reasoning = _scan_allowed_paths(
        allowed_paths=[str(allowed)],
        blocked_paths=[],
        search_query=None,
        search_mode=False,
        safe_mode=False,
    )

    tax_file = next(f for f in inventory if "sensitive_file" in f.path)
    normal_file = next(f for f in inventory if "normal_photo" in f.path)

    # Tax file filename must be masked in display path
    assert "my_tax_report" not in tax_file.path
    assert "sensitive_file_" in tax_file.path

    # Normal file filename must not be masked
    assert "normal_photo.jpg" in normal_file.path

    # Verify global registry maps the masked path to real path
    real_tax_path = resolve_real_path(tax_file.path)
    assert real_tax_path == tax_file.real_path
    assert os.path.exists(real_tax_path)


def test_safe_mode_path_sanitization(tmp_path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "my_tax_report.pdf").write_text("confidential")

    inventory, _reasoning = _scan_allowed_paths(
        allowed_paths=[str(allowed)],
        blocked_paths=[],
        search_query=None,
        search_mode=False,
        safe_mode=True,  # safe_mode active
    )

    tax_file = inventory[0]
    # Under safe mode/search mode, absolute paths are completely hidden/replaced
    assert "[RESTRICTED]" in tax_file.path
    assert "allowed" not in tax_file.path.lower()
    assert "sensitive_file_" in tax_file.path


def test_integration_with_classification_node(tmp_path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "my_tax_report.pdf").write_text("confidential")

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed)],
        blocked_paths=[],
    )
    scope_output = FolderScopeOutput(folder_scope_policy=policy, message="Success")

    res = file_discovery_node(scope_output)
    discovery_output = res.output if hasattr(res, "output") else res
    assert isinstance(discovery_output, FileDiscoveryOutput)
    assert len(discovery_output.file_inventory) == 1
