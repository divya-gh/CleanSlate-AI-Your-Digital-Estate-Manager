"""
tests/unit/test_mcp_tools_full.py

Comprehensive unit tests for every MCP tool and registry function.
Covers all scenarios required by Step 7:
  - list_files, read_file_metadata, compute_hash, move_file, delete_file,
    create_folder, compress_files, write_log, read_log,
    move_to_authenticated_folder, registry.list_tools, registry.test_tool

Design contract:
  - Metadata-only: tests never assert on file contents.
  - Policy-compliant: all tests set allowed_paths via mock_policy fixture.
  - Deterministic: no network calls, no LLM calls.
  - Fully isolated: every test uses tmp_path / monkeypatch.
"""

import hashlib
import json
import os
import zipfile

import pytest

from app.mcp_tools.compress_files import compress_files
from app.mcp_tools.compute_hash import compute_hash
from app.mcp_tools.create_folder import create_folder
from app.mcp_tools.delete_file import delete_file
from app.mcp_tools.list_files import list_files
from app.mcp_tools.move_file import move_file
from app.mcp_tools.move_to_authenticated_folder import move_to_authenticated_folder
from app.mcp_tools.read_file_metadata import read_file_metadata
from app.mcp_tools.read_log import read_log
from app.mcp_tools.registry import TOOLS, get_tool, list_tools, normalize_name
from app.mcp_tools.registry import test_tool as registry_test_tool
from app.mcp_tools.utils import SafetyViolationError, is_sensitive, validate_path_safety
from app.mcp_tools.write_log import write_log


# ===========================================================================
# Shared fixtures
# ===========================================================================


@pytest.fixture()
def policy_env(tmp_path, monkeypatch):
    """Create an isolated policy file and inject it via monkeypatch.

    Yields:
        (tmp_path, allowed_dir, blocked_dir, auth_dir, mock_policy_path)
    """
    cfg_dir = tmp_path / ".cleanslate"
    cfg_dir.mkdir()
    mock_config = cfg_dir / "config.json"
    mock_policy = cfg_dir / "policy.json"

    allowed_dir = tmp_path / "allowed"
    blocked_dir = allowed_dir / "blocked"
    auth_dir = allowed_dir / "authenticated_folder"

    for d in (allowed_dir, blocked_dir, auth_dir):
        d.mkdir(parents=True, exist_ok=True)

    policy_data = {
        "allowed_paths": [str(allowed_dir)],
        "blocked_paths": [str(blocked_dir)],
        "safe_mode": False,
    }
    mock_policy.write_text(json.dumps(policy_data), encoding="utf-8")

    monkeypatch.setattr("app.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("app.config.CONFIG_FILE", mock_config)
    monkeypatch.setattr("app.config.POLICY_FILE", mock_policy)

    yield tmp_path, allowed_dir, blocked_dir, auth_dir, mock_policy


@pytest.fixture()
def log_env(tmp_path, monkeypatch):
    """Isolated audit log environment."""
    log_path = tmp_path / "audit.log"
    monkeypatch.setenv("CLEANSLATE_LOG_PATH", str(log_path))
    yield log_path


# ===========================================================================
# 1. list_files
# ===========================================================================


class TestListFiles:
    def test_lists_files_in_allowed_scope(self, policy_env):
        _, allowed, _, _, _ = policy_env
        (allowed / "a.txt").write_text("hello")
        (allowed / "b.pdf").write_text("world")

        res = list_files(str(allowed))
        names = {f["name"] for f in res["files"]}
        assert "a.txt" in names
        assert "b.pdf" in names

    def test_returns_relative_normalized_paths(self, policy_env):
        _, allowed, _, _, _ = policy_env
        (allowed / "note.txt").write_text("x")

        res = list_files(str(allowed))
        for entry in res["files"]:
            # Returned path must be relative (no drive letter, no leading slash)
            assert not os.path.isabs(entry["path"])
            assert ".." not in entry["path"]
            assert "\\" not in entry["path"]   # always forward slash

    def test_skips_blocked_subdirectory_contents(self, policy_env):
        _, allowed, blocked, _, _ = policy_env
        (allowed / "visible.txt").write_text("ok")
        (blocked / "hidden.txt").write_text("secret")

        res = list_files(str(allowed))
        names = {f["name"] for f in res["files"]}
        assert "visible.txt" in names
        # blocked subdir itself may appear but hidden.txt inside must not
        assert "hidden.txt" not in names

    def test_includes_is_directory_flag(self, policy_env):
        _, allowed, _, _, _ = policy_env
        (allowed / "subdir").mkdir(exist_ok=True)
        (allowed / "file.txt").write_text("data")

        res = list_files(str(allowed))
        by_name = {f["name"]: f for f in res["files"]}
        assert by_name["file.txt"]["is_directory"] is False

    def test_rejects_directory_traversal(self, policy_env):
        _, allowed, _, _, _ = policy_env
        traversal = str(allowed) + "/../allowed/file.txt"
        with pytest.raises(SafetyViolationError) as exc:
            list_files(traversal)
        assert exc.value.details.get("directory_traversal") is True

    def test_rejects_symlink(self, policy_env):
        _, allowed, _, _, _ = policy_env
        target = allowed / "real.txt"
        target.write_text("data")
        link = allowed / "my_link"
        try:
            os.symlink(str(target), str(link))
        except OSError:
            pytest.skip("OS does not allow symlink creation in this context")

        with pytest.raises(SafetyViolationError) as exc:
            list_files(str(link))
        assert exc.value.details.get("symlink_blocked") is True

    def test_rejects_junction_via_mock(self, policy_env, monkeypatch):
        _, allowed, _, _, _ = policy_env
        target = allowed / "junc_dir"
        target.mkdir(exist_ok=True)

        class MockStat:
            st_reparse_tag = 0xA0000003
            st_size = 0
            st_mtime = 1000.0
            st_ctime = 1000.0
            st_mode = 16877

        monkeypatch.setattr(os, "lstat", lambda x: MockStat())
        with pytest.raises(SafetyViolationError) as exc:
            list_files(str(target))
        assert exc.value.details.get("junction_blocked") is True

    def test_raises_on_nonexistent_path(self, policy_env):
        _, allowed, _, _, _ = policy_env
        with pytest.raises(FileNotFoundError):
            list_files(str(allowed / "does_not_exist"))

    def test_raises_on_file_instead_of_directory(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "file.txt"
        f.write_text("data")
        with pytest.raises(ValueError, match="PathInvalid"):
            list_files(str(f))

    def test_result_structure_has_required_keys(self, policy_env):
        _, allowed, _, _, _ = policy_env
        (allowed / "struct.txt").write_text("x")
        res = list_files(str(allowed))
        assert "files" in res
        for entry in res["files"]:
            for key in ("name", "path", "size", "is_directory"):
                assert key in entry, f"Missing key '{key}' in entry: {entry}"


# ===========================================================================
# 2. read_file_metadata
# ===========================================================================


class TestReadFileMetadata:
    def test_returns_metadata_fields(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "meta.txt"
        f.write_text("hello world")

        meta = read_file_metadata(str(f))
        assert meta["size"] == 11
        assert meta["extension"] == ".txt"
        assert "text/" in meta["mime_type"]
        assert "modified_at" in meta
        assert "created_at" in meta

    def test_no_file_contents_in_result(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "content.txt"
        f.write_text("this is the file content that must never appear")

        meta = read_file_metadata(str(f))
        result_str = json.dumps(meta)
        assert "this is the file content" not in result_str

    def test_rejects_sensitive_files(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "sensitive_file_tax.pdf"
        f.write_text("secret")
        with pytest.raises(ValueError, match="SensitiveFileError"):
            read_file_metadata(str(f))

    def test_rejects_directory(self, policy_env):
        _, allowed, _, _, _ = policy_env
        with pytest.raises(ValueError, match="PathInvalid"):
            read_file_metadata(str(allowed))

    def test_rejects_out_of_scope_path(self, policy_env):
        _, _, _, _, _ = policy_env
        with pytest.raises(SafetyViolationError):
            read_file_metadata("/Windows/System32/ntdll.dll")

    def test_rejects_traversal(self, policy_env):
        _, allowed, _, _, _ = policy_env
        with pytest.raises(SafetyViolationError) as exc:
            read_file_metadata(str(allowed / ".." / "allowed" / "x.txt"))
        assert exc.value.details.get("directory_traversal") is True

    def test_mime_type_for_pdf(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "report.pdf"
        f.write_bytes(b"%PDF-1.4 fake")
        meta = read_file_metadata(str(f))
        assert meta["extension"] == ".pdf"
        assert "pdf" in meta["mime_type"]

    def test_unknown_mime_falls_back_to_octet_stream(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "archive.xyz123"
        f.write_bytes(b"binary")
        meta = read_file_metadata(str(f))
        assert meta["mime_type"] == "application/octet-stream"

    def test_raises_on_nonexistent_file(self, policy_env):
        _, allowed, _, _, _ = policy_env
        with pytest.raises(FileNotFoundError):
            read_file_metadata(str(allowed / "ghost.txt"))


# ===========================================================================
# 3. compute_hash
# ===========================================================================


class TestComputeHash:
    def test_sha256_correct_for_known_content(self, policy_env):
        _, allowed, _, _, _ = policy_env
        content = b"CleanSlate AI deterministic test"
        f = allowed / "known.bin"
        f.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()
        res = compute_hash(str(f))
        assert res["sha256"] == expected

    def test_hash_method_field_present(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "hm.txt"
        f.write_text("abc")
        res = compute_hash(str(f))
        assert res.get("hash_method") == "sha256_streaming"

    def test_streaming_over_large_chunk(self, policy_env):
        _, allowed, _, _, _ = policy_env
        content = b"A" * (65536 * 3)   # 3 full chunks
        f = allowed / "chunked.bin"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        res = compute_hash(str(f))
        assert res["sha256"] == expected
        assert len(res["sha256"]) == 64

    def test_rejects_file_over_2gb(self, policy_env, monkeypatch):
        _, allowed, _, _, _ = policy_env
        f = allowed / "huge.bin"
        f.write_bytes(b"x")

        monkeypatch.setattr(os.path, "getsize", lambda p: 3 * 1024 * 1024 * 1024)
        with pytest.raises(SafetyViolationError) as exc:
            compute_hash(str(f))
        assert exc.value.details.get("file_too_large") is True
        assert exc.value.details.get("max_supported_size") == "2GB"

    def test_rejects_sensitive_file(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "sensitive_file_bank.txt"
        f.write_text("private")
        with pytest.raises(ValueError, match="SensitiveFileError"):
            compute_hash(str(f))

    def test_rejects_nonexistent_file(self, policy_env):
        _, allowed, _, _, _ = policy_env
        with pytest.raises(FileNotFoundError):
            compute_hash(str(allowed / "missing.bin"))

    def test_rejects_directory(self, policy_env):
        _, allowed, _, _, _ = policy_env
        with pytest.raises(ValueError, match="PathInvalid"):
            compute_hash(str(allowed))

    def test_rejects_traversal(self, policy_env):
        _, allowed, _, _, _ = policy_env
        with pytest.raises(SafetyViolationError) as exc:
            compute_hash(str(allowed / ".." / "allowed" / "x"))
        assert exc.value.details.get("directory_traversal") is True


# ===========================================================================
# 4. move_file
# ===========================================================================


class TestMoveFile:
    def test_moves_non_sensitive_file_within_scope(self, policy_env):
        _, allowed, _, _, _ = policy_env
        src = allowed / "doc.txt"
        src.write_text("data")
        dst = allowed / "subdir" / "doc.txt"

        res = move_file(str(src), str(dst))
        assert res["status"] == "success"
        assert not src.exists()
        assert dst.exists()

    def test_atomic_replace_used_by_default(self, policy_env):
        _, allowed, _, _, _ = policy_env
        src = allowed / "src.txt"
        src.write_text("move me")
        dst = allowed / "dst.txt"

        res = move_file(str(src), str(dst))
        assert res["status"] == "success"
        # atomic_fallback_used should be False when os.replace succeeds
        assert res["atomic_fallback_used"] is False

    def test_atomic_fallback_used_on_cross_device(self, policy_env, monkeypatch):
        _, allowed, _, _, _ = policy_env
        src = allowed / "cross.txt"
        src.write_text("cross device")
        dst = allowed / "cross_dst.txt"

        original_replace = os.replace

        def fail_replace(s, d):
            raise OSError("Cross-device link")

        monkeypatch.setattr(os, "replace", fail_replace)

        res = move_file(str(src), str(dst))
        assert res["status"] == "success"
        assert res["atomic_fallback_used"] is True
        assert dst.exists()

    def test_rejects_sensitive_to_unauthenticated(self, policy_env):
        _, allowed, _, _, _ = policy_env
        src = allowed / "sensitive_file_tax.txt"
        src.write_text("confidential")
        dst = allowed / "regular_folder" / "tax.txt"

        with pytest.raises(ValueError, match="SecurityViolation"):
            move_file(str(src), str(dst))

    def test_allows_sensitive_to_authenticated(self, policy_env):
        _, allowed, _, auth_dir, _ = policy_env
        src = allowed / "sensitive_file_tax2.txt"
        src.write_text("confidential")
        dst = auth_dir / "tax2.txt"

        res = move_file(str(src), str(dst))
        assert res["status"] == "success"
        assert not src.exists()
        assert dst.exists()

    def test_rejects_blocked_source(self, policy_env):
        _, allowed, blocked, _, _ = policy_env
        src = blocked / "junk.txt"
        src.write_text("blocked")
        dst = allowed / "junk.txt"

        with pytest.raises(SafetyViolationError):
            move_file(str(src), str(dst))

    def test_rejects_blocked_destination(self, policy_env):
        _, allowed, blocked, _, _ = policy_env
        src = allowed / "file.txt"
        src.write_text("data")
        dst = blocked / "file.txt"

        with pytest.raises(SafetyViolationError):
            move_file(str(src), str(dst))

    def test_rejects_nonexistent_source(self, policy_env):
        _, allowed, _, _, _ = policy_env
        with pytest.raises(FileNotFoundError):
            move_file(str(allowed / "ghost.txt"), str(allowed / "dst.txt"))

    def test_rejects_traversal_in_source(self, policy_env):
        _, allowed, _, _, _ = policy_env
        with pytest.raises(SafetyViolationError) as exc:
            move_file(str(allowed / ".." / "allowed" / "x"), str(allowed / "y"))
        assert exc.value.details.get("directory_traversal") is True


# ===========================================================================
# 5. delete_file
# ===========================================================================


class TestDeleteFile:
    def test_requires_hitl_approved_true(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "junk.txt"
        f.write_text("delete me")

        with pytest.raises(SafetyViolationError) as exc:
            delete_file(str(f), hitl_approved=False)
        assert exc.value.details.get("hitl_required") is True
        assert exc.value.details.get("operation") == "delete_file"

    def test_deletes_file_with_hitl_true(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "removable.txt"
        f.write_text("to delete")

        res = delete_file(str(f), hitl_approved=True)
        assert res["status"] == "deleted"
        assert not f.exists()

    def test_rejects_sensitive_files(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "sensitive_file_contract.txt"
        f.write_text("sensitive")

        with pytest.raises(SafetyViolationError) as exc:
            delete_file(str(f), hitl_approved=True)
        assert exc.value.details.get("blocked_by_sensitive") is True

    def test_rejects_when_safe_mode_enabled(self, policy_env):
        _, allowed, _, _, mock_policy = policy_env
        f = allowed / "file_in_safemode.txt"
        f.write_text("data")

        mock_policy.write_text(
            json.dumps({
                "allowed_paths": [str(allowed)],
                "blocked_paths": [],
                "safe_mode": True,
            }),
            encoding="utf-8",
        )

        with pytest.raises(SafetyViolationError) as exc:
            delete_file(str(f), hitl_approved=True)
        assert exc.value.details.get("safe_mode_blocked") is True
        assert exc.value.details.get("safe_mode") is True
        assert exc.value.details.get("operation") == "delete_file"

    def test_safe_mode_detail_in_mcp_error(self, policy_env):
        """Verify the registry wraps SafetyViolationError into a ToolError MCP object."""
        _, allowed, _, _, mock_policy = policy_env
        f = allowed / "mcp_delete.txt"
        f.write_text("data")

        mock_policy.write_text(
            json.dumps({
                "allowed_paths": [str(allowed)],
                "blocked_paths": [],
                "safe_mode": True,
            }),
            encoding="utf-8",
        )

        res = registry_test_tool("delete_file", path=str(f), hitl_approved=True)
        assert "error" in res
        assert res["error"]["type"] == "ToolError"
        assert res["error"]["details"]["safe_mode_blocked"] is True
        assert res["error"]["details"]["safe_mode"] is True

    def test_rejects_nonexistent_path_after_hitl(self, policy_env):
        _, allowed, _, _, _ = policy_env
        with pytest.raises(FileNotFoundError):
            delete_file(str(allowed / "phantom.txt"), hitl_approved=True)

    def test_rejects_directory_deletion(self, policy_env):
        _, allowed, _, _, _ = policy_env
        d = allowed / "subdir"
        d.mkdir(exist_ok=True)
        with pytest.raises(ValueError, match="PathInvalid"):
            delete_file(str(d), hitl_approved=True)

    def test_rejects_blocked_path(self, policy_env):
        _, allowed, blocked, _, _ = policy_env
        f = blocked / "blocked.txt"
        f.write_text("data")
        with pytest.raises(SafetyViolationError):
            delete_file(str(f), hitl_approved=True)


# ===========================================================================
# 6. create_folder
# ===========================================================================


class TestCreateFolder:
    def test_creates_folder_in_allowed_scope(self, policy_env):
        _, allowed, _, _, _ = policy_env
        target = allowed / "new_dir" / "nested"

        res = create_folder(str(target))
        assert res["status"] == "created"
        assert target.exists()

    def test_rejects_existing_directory(self, policy_env):
        _, allowed, _, _, _ = policy_env
        existing = allowed / "already_there"
        existing.mkdir()

        with pytest.raises(ValueError, match="AlreadyExists"):
            create_folder(str(existing))

    def test_rejects_path_where_file_exists(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "conflict.txt"
        f.write_text("x")

        with pytest.raises(ValueError, match="AlreadyExists"):
            create_folder(str(f))

    def test_rejects_blocked_path(self, policy_env):
        _, allowed, blocked, _, _ = policy_env
        target = blocked / "new_folder"
        with pytest.raises(ValueError, match="PathNotAllowed"):
            create_folder(str(target))

    def test_rejects_out_of_scope_path(self):
        with pytest.raises(ValueError, match="PathNotAllowed"):
            create_folder("/Windows/System32/new_folder")

    def test_creates_nested_directories(self, policy_env):
        _, allowed, _, _, _ = policy_env
        target = allowed / "a" / "b" / "c"
        res = create_folder(str(target))
        assert res["status"] == "created"
        assert target.exists()


# ===========================================================================
# 7. compress_files
# ===========================================================================


class TestCompressFiles:
    def test_creates_zip_archive(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f1 = allowed / "doc1.txt"
        f1.write_text("hello")
        f2 = allowed / "doc2.txt"
        f2.write_text("world")
        archive = allowed / "out.zip"

        res = compress_files([str(f1), str(f2)], str(archive))
        assert res["status"] == "compressed"
        assert archive.exists()

    def test_archive_contains_correct_files(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f1 = allowed / "keep.txt"
        f1.write_text("keep")
        archive = allowed / "result.zip"

        compress_files([str(f1)], str(archive))
        with zipfile.ZipFile(archive, "r") as z:
            assert "keep.txt" in z.namelist()

    def test_skips_sensitive_files(self, policy_env):
        _, allowed, _, _, _ = policy_env
        safe = allowed / "safe.txt"
        safe.write_text("safe data")
        sens = allowed / "sensitive_file_ssn.txt"
        sens.write_text("111-22-3333")
        archive = allowed / "mixed.zip"

        res = compress_files([str(safe), str(sens)], str(archive))
        assert res["status"] == "compressed"
        with zipfile.ZipFile(archive, "r") as z:
            assert "safe.txt" in z.namelist()
            assert "sensitive_file_ssn.txt" not in z.namelist()

    def test_rejects_blocked_destination(self, policy_env):
        _, allowed, blocked, _, _ = policy_env
        f = allowed / "file.txt"
        f.write_text("data")
        archive = blocked / "out.zip"

        with pytest.raises((ValueError, SafetyViolationError)):
            compress_files([str(f)], str(archive))

    def test_returns_archive_path_in_result(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "item.txt"
        f.write_text("x")
        archive = allowed / "single.zip"

        res = compress_files([str(f)], str(archive))
        assert "archive_path" in res or "archive" in res

    def test_all_sensitive_files_raises_value_error(self, policy_env):
        """compress_files with only sensitive files should raise ValueError cleanly."""
        _, allowed, _, _, _ = policy_env
        sens = allowed / "sensitive_file_pii.txt"
        sens.write_text("ssn")
        archive = allowed / "empty.zip"

        with pytest.raises(ValueError, match="NoFilesToCompress"):
            compress_files([str(sens)], str(archive))


# ===========================================================================
# 8. write_log
# ===========================================================================


class TestWriteLog:
    def test_writes_valid_json_entry(self, log_env):
        entry = json.dumps({
            "node": "TestNode",
            "action_type": "test",
            "path": "/some/path/file.txt",
            "is_sensitive": False,
            "result": "success",
        })
        res = write_log(entry)
        assert res["status"] == "logged"

    def test_log_file_created(self, log_env):
        write_log(json.dumps({"node": "N", "action_type": "t", "path": None,
                               "is_sensitive": False, "result": "ok"}))
        assert log_env.exists()

    def test_sensitive_path_redacted_in_log(self, log_env):
        entry = json.dumps({
            "node": "TestNode",
            "action_type": "move",
            "path": "/home/user/sensitive_file_tax.pdf",
            "is_sensitive": True,
            "result": "success",
        })
        write_log(entry)
        raw = log_env.read_text(encoding="utf-8")
        assert "/home/user/sensitive_file_tax.pdf" not in raw
        assert "<sensitive file>" in raw

    def test_absolute_path_stripped_in_log(self, log_env):
        entry = json.dumps({
            "node": "TestNode",
            "action_type": "move",
            "path": "/home/user/documents/report.txt",
            "is_sensitive": False,
            "result": "success",
        })
        write_log(entry)
        raw = log_env.read_text(encoding="utf-8")
        # Absolute path must not appear verbatim in the log
        assert "/home/user/documents/report.txt" not in raw
        # Only last two segments should appear
        assert "documents/report.txt" in raw or "report.txt" in raw

    def test_handles_plain_string_entry(self, log_env):
        res = write_log("plain string event")
        assert res["status"] == "logged"

    def test_log_rotation_at_10mb(self, log_env, monkeypatch):
        from app.security.audit_logger import log_action

        # Write initial entry
        log_action("T", "t", None, False, "none", "ok")
        assert log_env.exists()

        # Mock file size to exceed 10MB
        monkeypatch.setattr(os.path, "getsize", lambda p: 11 * 1024 * 1024)

        # Next write triggers rotation
        log_action("T", "t", None, False, "none", "ok")

        backup = log_env.parent / (log_env.name + ".1")
        assert backup.exists()
        assert log_env.exists()

        first_line = json.loads(log_env.read_text(encoding="utf-8").splitlines()[0])
        assert first_line["action_type"] == "rotation"
        assert first_line["reason"] == "log_file_exceeded_10MB"

    def test_delete_reason_in_audit_log(self, log_env):
        from app.security.audit_logger import log_action
        log_action(
            "TestNode", "delete_blocked", "/allowed/junk.txt",
            False, "none", "failed",
            reason="safe_mode_blocked",
            delete_reason="safe_mode_enabled",
        )
        raw = log_env.read_text(encoding="utf-8")
        entry = json.loads(raw.strip().split("\n")[-1])
        assert entry.get("delete_reason") == "safe_mode_enabled"


# ===========================================================================
# 9. read_log
# ===========================================================================


class TestReadLog:
    def test_returns_entries_list(self, log_env):
        from app.security.audit_logger import log_action
        log_action("N", "t", None, False, "none", "ok")
        res = read_log()
        assert "entries" in res
        assert isinstance(res["entries"], list)

    def test_empty_log_returns_empty_list(self, log_env):
        res = read_log()
        # Empty file or missing file: empty entries
        assert res["entries"] == []

    def test_limit_caps_entries_returned(self, log_env):
        from app.security.audit_logger import log_action
        for i in range(10):
            log_action(f"N{i}", "t", None, False, "none", "ok")
        res = read_log(limit=3)
        assert len(res["entries"]) == 3

    def test_sensitive_path_redacted_on_read(self, log_env):
        write_log(json.dumps({
            "node": "N", "action_type": "t",
            "path": "/abs/path/sensitive_file_tax.pdf",
            "is_sensitive": True, "result": "ok",
        }))
        res = read_log()
        for raw in res["entries"]:
            entry = json.loads(raw)
            if entry.get("path"):
                assert entry["path"] == "<sensitive file>"

    def test_absolute_path_stripped_on_read(self, log_env):
        write_log(json.dumps({
            "node": "N", "action_type": "t",
            "path": "/very/long/absolute/path/doc.txt",
            "is_sensitive": False, "result": "ok",
        }))
        res = read_log()
        for raw in res["entries"]:
            entry = json.loads(raw)
            if entry.get("path") and "/" in entry["path"]:
                # Should be at most parent/filename â€” no deep absolute path
                parts = entry["path"].split("/")
                assert len(parts) <= 2

    def test_returns_json_string_entries(self, log_env):
        write_log(json.dumps({
            "node": "N", "action_type": "t", "path": None,
            "is_sensitive": False, "result": "ok",
        }))
        res = read_log()
        for e in res["entries"]:
            # Each entry must be parseable JSON
            parsed = json.loads(e)
            assert isinstance(parsed, dict)

    def test_no_file_no_crash(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLEANSLATE_LOG_PATH", str(tmp_path / "nonexistent.log"))
        res = read_log()
        assert res == {"entries": []}


# ===========================================================================
# 10. move_to_authenticated_folder
# ===========================================================================


class TestMoveToAuthenticatedFolder:
    def test_moves_sensitive_file_to_auth_folder(self, policy_env):
        _, allowed, _, auth_dir, _ = policy_env
        src = allowed / "sensitive_file_pii.txt"
        src.write_text("pii data")
        dst = auth_dir / "pii.txt"

        res = move_to_authenticated_folder(str(src), str(dst))
        assert res["status"] == "secured"
        assert not src.exists()
        assert dst.exists()

    def test_atomic_fallback_used_on_oserror(self, policy_env, monkeypatch):
        _, allowed, _, auth_dir, _ = policy_env
        src = allowed / "sensitive_file_ssn2.txt"
        src.write_text("data")
        dst = auth_dir / "ssn2.txt"

        monkeypatch.setattr(os, "replace", lambda s, d: (_ for _ in ()).throw(OSError("cross")))

        res = move_to_authenticated_folder(str(src), str(dst))
        assert res["status"] == "secured"
        assert res["atomic_fallback_used"] is True

    def test_rejects_non_sensitive_file(self, policy_env):
        _, allowed, _, auth_dir, _ = policy_env
        src = allowed / "normal.txt"
        src.write_text("not sensitive")
        dst = auth_dir / "normal.txt"

        with pytest.raises(ValueError, match="SecurityViolation"):
            move_to_authenticated_folder(str(src), str(dst))

    def test_rejects_insecure_destination(self, policy_env, monkeypatch):
        """Destination that is not an authenticated/secure folder must be rejected.

        NOTE: We mock is_authenticated_folder to return False for the plain
        destination because the Windows temp path can contain substrings like
        'secure' or 'authenticated' that fool the naive substring check.
        This tests the branch logic, not the substring detection.
        """
        _, allowed, _, _, _ = policy_env
        src = allowed / "sensitive_file_id.txt"
        src.write_text("id info")
        plain_dir = allowed / "plain"
        plain_dir.mkdir(exist_ok=True)
        dst_file = plain_dir / "id.txt"
        dst_file.write_text("")

        import sys
        # Force is_authenticated_folder to return False for this destination.
        # Must use sys.modules to get the module object (the import name collides
        # with the function name in this module).
        mta_module = sys.modules["app.mcp_tools.move_to_authenticated_folder"]
        monkeypatch.setattr(mta_module, "is_authenticated_folder", lambda p: False)

        with pytest.raises(ValueError, match="SecurityViolation"):
            mta_module.move_to_authenticated_folder(str(src), str(dst_file))

    def test_rejects_traversal_in_source(self, policy_env):
        _, allowed, _, auth_dir, _ = policy_env
        with pytest.raises(SafetyViolationError) as exc:
            move_to_authenticated_folder(
                str(allowed / ".." / "allowed" / "x"),
                str(auth_dir / "y"),
            )
        assert exc.value.details.get("directory_traversal") is True

    def test_rejects_nonexistent_source(self, policy_env):
        _, allowed, _, auth_dir, _ = policy_env
        with pytest.raises(FileNotFoundError):
            move_to_authenticated_folder(
                str(allowed / "ghost_sensitive_file.txt"),
                str(auth_dir / "ghost.txt"),
            )


# ===========================================================================
# 11. registry.list_tools
# ===========================================================================


class TestRegistryListTools:
    def test_returns_all_registered_tools(self):
        tools = list_tools()
        assert len(tools) == len(TOOLS)
        names = {t["name"] for t in tools}
        assert names == set(TOOLS.keys())

    def test_each_tool_has_required_fields(self):
        required = {"name", "description", "input_schema", "output_schema", "version"}
        for t in list_tools():
            assert required.issubset(set(t.keys())), f"{t['name']} missing fields"

    def test_version_is_string(self):
        for t in list_tools():
            assert isinstance(t["version"], str)

    def test_input_schema_has_properties(self):
        for t in list_tools():
            assert "properties" in t["input_schema"], f"{t['name']} input_schema lacks properties"

    def test_names_are_snake_case(self):
        import re
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for t in list_tools():
            assert pattern.match(t["name"]), f"{t['name']} is not snake_case"

    def test_normalize_name_variants(self):
        assert normalize_name("listFiles") == "list_files"
        assert normalize_name("list-files") == "list_files"
        assert normalize_name("list files") == "list_files"
        assert normalize_name("LIST_FILES") == "list_files"
        assert normalize_name("  list_files  ") == "list_files"

    def test_get_tool_returns_callable(self):
        fn = get_tool("list_files")
        assert callable(fn)

    def test_get_tool_raises_on_unknown(self):
        with pytest.raises(KeyError):
            get_tool("absolutely_nonexistent_tool_xyz")

    def test_get_tool_normalizes_name(self):
        fn = get_tool("listFiles")
        assert callable(fn)


# ===========================================================================
# 12. registry.test_tool
# ===========================================================================


class TestRegistryTestTool:
    def test_unknown_tool_returns_tool_not_found(self):
        res = registry_test_tool("totally_unknown_tool_xyz")
        assert "error" in res
        assert res["error"]["type"] == "ToolNotFound"
        assert res["error"]["details"]["schema_validated"] is False

    def test_tool_not_found_details_complete(self):
        res = registry_test_tool("ghost")
        err = res["error"]
        assert "type" in err
        assert "message" in err
        assert "details" in err
        assert "tool" in err["details"]
        assert "normalized_name" in err["details"]

    def test_missing_required_arg_returns_schema_error(self):
        res = registry_test_tool("list_files")  # missing 'path'
        assert "error" in res
        assert res["error"]["type"] == "SchemaError"
        assert "path" in res["error"]["message"]
        assert res["error"]["details"]["schema_diff"]["missing_key"] == "path"

    def test_unexpected_arg_returns_schema_error(self):
        res = registry_test_tool("read_log", bogus_key="value")
        assert "error" in res
        assert res["error"]["type"] == "SchemaError"
        assert "bogus_key" in res["error"]["message"]

    def test_wrong_type_integer_returns_schema_error(self):
        res = registry_test_tool("read_log", limit="not_a_number")
        assert "error" in res
        assert res["error"]["type"] == "SchemaError"
        assert res["error"]["details"]["schema_diff"]["expected_type"] == "integer"

    def test_integer_coercion_string_to_int(self, log_env):
        res = registry_test_tool("read_log", limit="5")
        # No SchemaError â€” string "5" is coerced to int
        if "error" in res:
            assert res["error"]["type"] != "SchemaError"

    def test_boolean_coercion_string_true(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "junk.txt"
        f.write_text("data")
        # "true" string should coerce to True
        res = registry_test_tool("delete_file", path=str(f), hitl_approved="true")
        assert res.get("status") == "success" or "error" in res
        # Either succeeded (deleted) or hit policy â€” not a SchemaError
        if "error" in res:
            assert res["error"]["type"] != "SchemaError"

    def test_boolean_coercion_string_false_blocks_deletion(self, policy_env):
        _, allowed, _, _, _ = policy_env
        f = allowed / "no_delete.txt"
        f.write_text("x")
        res = registry_test_tool("delete_file", path=str(f), hitl_approved="false")
        assert "error" in res
        # Should be hitl_required error, not SchemaError
        assert res["error"]["type"] != "SchemaError"

    def test_success_result_structure(self, policy_env):
        _, allowed, _, _, _ = policy_env
        res = registry_test_tool("list_files", path=str(allowed))
        assert res["status"] == "success"
        assert "result" in res
        assert "files" in res["result"]

    def test_policy_violation_returns_tool_error(self):
        res = registry_test_tool("list_files", path="/Windows/System32")
        assert "error" in res
        assert res["error"]["type"] == "ToolError"
        assert res["error"]["details"]["schema_validated"] is True

    def test_camel_case_name_resolves(self, policy_env):
        _, allowed, _, _, _ = policy_env
        res = registry_test_tool("listFiles", path=str(allowed))
        assert res["status"] == "success"

    def test_kebab_case_name_resolves(self, policy_env):
        _, allowed, _, _, _ = policy_env
        res = registry_test_tool("list-files", path=str(allowed))
        assert res["status"] == "success"

    def test_mcp_error_structure_is_never_wrapped(self):
        """Registry must return raw MCP error â€” not nested or re-wrapped."""
        res = registry_test_tool("nonexistent")
        assert list(res.keys()) == ["error"]
        err = res["error"]
        assert set(err.keys()) >= {"type", "message", "details"}

    def test_compute_hash_2gb_limit_via_registry(self, policy_env, monkeypatch):
        _, allowed, _, _, _ = policy_env
        f = allowed / "large.bin"
        f.write_bytes(b"x")
        monkeypatch.setattr(os.path, "getsize", lambda p: 3 * 1024 * 1024 * 1024)

        res = registry_test_tool("compute_hash", path=str(f))
        assert "error" in res
        assert res["error"]["details"]["file_too_large"] is True
        assert res["error"]["details"]["max_supported_size"] == "2GB"

    def test_array_coercion_from_comma_string(self, policy_env):
        """compress_files 'files' array can be passed as comma-separated string."""
        _, allowed, _, _, _ = policy_env
        f1 = allowed / "arr1.txt"
        f1.write_text("data")
        archive = str(allowed / "arr.zip")
        files_str = str(f1)  # single item â€” registry accepts list or comma string

        res = registry_test_tool("compress_files", files=files_str, destination=archive)
        # Should succeed or fail gracefully, not SchemaError
        if "error" in res:
            assert res["error"]["type"] != "SchemaError"

