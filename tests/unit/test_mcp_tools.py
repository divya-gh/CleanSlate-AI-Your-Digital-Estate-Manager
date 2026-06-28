import json
import os

import pytest

from app.mcp_tools.compress_files import compress_files
from app.mcp_tools.compute_hash import compute_hash
from app.mcp_tools.create_folder import create_folder
from app.mcp_tools.delete_file import delete_file
from app.mcp_tools.list_files import list_files
from app.mcp_tools.move_file import move_file
from app.mcp_tools.read_file_metadata import read_file_metadata
from app.mcp_tools.read_log import read_log
from app.mcp_tools.utils import (
    is_path_allowed_by_policy,
    is_sensitive,
)
from app.mcp_tools.write_log import write_log


@pytest.fixture
def mock_config_paths(tmp_path, monkeypatch):
    """Isolates policy and config to a temp path for testing."""
    mock_dir = tmp_path / ".cleanslate"
    mock_dir.mkdir()

    mock_config = mock_dir / "config.json"
    mock_policy = mock_dir / "policy.json"

    monkeypatch.setattr("app.config.CONFIG_DIR", mock_dir)
    monkeypatch.setattr("app.config.CONFIG_FILE", mock_config)
    monkeypatch.setattr("app.config.POLICY_FILE", mock_policy)

    # Write a default policy
    policy_data = {
        "allowed_paths": [str(tmp_path / "allowed")],
        "blocked_paths": [str(tmp_path / "allowed" / "blocked")],
        "safe_mode": False,
    }

    # Ensure folders exist
    (tmp_path / "allowed").mkdir(exist_ok=True)
    (tmp_path / "allowed" / "blocked").mkdir(exist_ok=True)

    with open(mock_policy, "w", encoding="utf-8") as f:
        json.dump(policy_data, f)

    yield tmp_path, mock_policy


def test_allowed_vs_blocked_paths(mock_config_paths):
    """Verify is_path_allowed_by_policy blocks/allows correct paths."""
    tmp_path, _ = mock_config_paths

    allowed = tmp_path / "allowed" / "file.txt"
    blocked = tmp_path / "allowed" / "blocked" / "file.txt"
    system_path = "/Windows/System32/somefile.dll"

    assert is_path_allowed_by_policy(allowed) is True
    assert is_path_allowed_by_policy(blocked) is False
    assert is_path_allowed_by_policy(system_path) is False


def test_sensitive_vs_non_sensitive():
    """Verify is_sensitive correctly matches extensions, keywords, and markings."""
    assert is_sensitive("normal_report.txt") is False
    assert is_sensitive("sensitive_file_draft.doc") is True
    assert is_sensitive("tax_document.pdf") is True
    assert is_sensitive("my_keys.pem") is True
    assert is_sensitive("bank/report.xlsx") is True


def test_list_files(mock_config_paths):
    """Assert list_files retrieves entries for allowed directories."""
    tmp_path, _ = mock_config_paths
    allowed_dir = tmp_path / "allowed"

    # Write dummy files
    f1 = allowed_dir / "test1.txt"
    f1.write_text("hello")
    f2 = allowed_dir / "blocked" / "test2.txt"
    f2.write_text("world")

    res = list_files(str(allowed_dir))
    files = res["files"]

    # Only test1 should be visible, blocked directory/files skipped
    assert len(files) == 1
    assert files[0]["name"] == "test1.txt"


def test_read_file_metadata(mock_config_paths):
    """Assert read_file_metadata returns core stats without opening the file."""
    tmp_path, _ = mock_config_paths
    allowed_file = tmp_path / "allowed" / "test.txt"
    allowed_file.write_text("hello world")

    metadata = read_file_metadata(str(allowed_file))
    assert metadata["size"] == 11
    assert metadata["extension"] == ".txt"
    assert "text/" in metadata["mime_type"]


def test_compute_hash_streaming(mock_config_paths):
    """Assert compute_hash works on large files in chunks and throws on sensitive files."""
    tmp_path, _ = mock_config_paths

    # Test sensitive file error
    sens_file = tmp_path / "allowed" / "sensitive_file_tax.txt"
    sens_file.write_text("top secret")
    with pytest.raises(ValueError, match="SensitiveFileError"):
        compute_hash(str(sens_file))

    # Test successful hash on standard file
    std_file = tmp_path / "allowed" / "standard.txt"
    # Write enough text to verify chunking
    std_file.write_text("A" * 20000)

    res = compute_hash(str(std_file))
    assert "sha256" in res
    assert len(res["sha256"]) == 64


def test_move_file(mock_config_paths):
    """Assert move_file requires authenticated folder for sensitive source."""
    tmp_path, _ = mock_config_paths

    src = tmp_path / "allowed" / "sensitive_file_secret.txt"
    src.write_text("confidential")

    unauth_dest = tmp_path / "allowed" / "regular_folder" / "secret.txt"
    auth_dest = tmp_path / "allowed" / "authenticated_folder" / "secret.txt"

    # 1. Unauthenticated dest fails
    with pytest.raises(ValueError, match="SecurityViolation"):
        move_file(str(src), str(unauth_dest))

    # 2. Authenticated dest succeeds
    res = move_file(str(src), str(auth_dest))
    assert res["status"] == "success"
    assert not src.exists()
    assert auth_dest.exists()


def test_delete_file_hitl(mock_config_paths):
    """Assert delete_file checks HITL approval, safe mode, and sensitivity."""
    tmp_path, mock_policy = mock_config_paths

    std_file = tmp_path / "allowed" / "junk.txt"
    std_file.write_text("delete me")

    # 1. Rejects without HITL
    with pytest.raises(ValueError, match="HITLApprovalRequired"):
        delete_file(str(std_file), hitl_approved=False)

    # 2. Rejects sensitive deletion even with HITL
    sens_file = tmp_path / "allowed" / "sensitive_file_check.txt"
    sens_file.write_text("tax card")
    with pytest.raises(ValueError, match="SecurityViolation"):
        delete_file(str(sens_file), hitl_approved=True)

    # 3. Respects safe_mode
    with open(mock_policy, "w", encoding="utf-8") as f:
        json.dump(
            {
                "allowed_paths": [str(tmp_path / "allowed")],
                "blocked_paths": [],
                "safe_mode": True,
            },
            f,
        )

    with pytest.raises(ValueError, match="SafeModeActive"):
        delete_file(str(std_file), hitl_approved=True)

    # Restore safe_mode=False and verify deletion
    with open(mock_policy, "w", encoding="utf-8") as f:
        json.dump(
            {
                "allowed_paths": [str(tmp_path / "allowed")],
                "blocked_paths": [],
                "safe_mode": False,
            },
            f,
        )

    res = delete_file(str(std_file), hitl_approved=True)
    assert res["status"] == "deleted"
    assert not std_file.exists()


def test_create_folder(mock_config_paths):
    """Assert create_folder creates directories in allowed paths."""
    tmp_path, _ = mock_config_paths
    target = tmp_path / "allowed" / "new_folder" / "nested"

    res = create_folder(str(target))
    assert res["status"] == "created"
    assert target.exists()


def test_compress_files(mock_config_paths):
    """Assert compress_files skips sensitive items."""
    tmp_path, _ = mock_config_paths

    f1 = tmp_path / "allowed" / "doc1.txt"
    f1.write_text("regular data")
    f2 = tmp_path / "allowed" / "sensitive_file_doc2.txt"
    f2.write_text("restricted ssn data")

    archive = tmp_path / "allowed" / "output.zip"

    res = compress_files([str(f1), str(f2)], str(archive))
    assert res["status"] == "compressed"
    assert archive.exists()

    # Confirm ZIP contains only non-sensitive items
    import zipfile

    with zipfile.ZipFile(archive, "r") as z:
        names = z.namelist()
        assert "doc1.txt" in names
        assert "sensitive_file_doc2.txt" not in names


def test_log_redaction_and_read(tmp_path, monkeypatch):
    """Assert write_log and read_log redact absolute paths correctly."""
    mock_log = tmp_path / "audit.log"
    monkeypatch.setenv("CLEANSLATE_LOG_PATH", str(mock_log))

    # 1. Log with sensitive indicator
    log_entry_sens = json.dumps(
        {
            "node": "TestNode",
            "action_type": "read",
            "path": "/absolute/path/to/sensitive_file_tax.pdf",
            "is_sensitive": True,
            "result": "success",
            "reason": "reading doc",
        }
    )
    write_log(log_entry_sens)

    # 2. Log regular entry (absolute path should be relative in audit)
    log_entry_std = json.dumps(
        {
            "node": "TestNode",
            "action_type": "move",
            "path": "/absolute/path/to/regular_file.txt",
            "is_sensitive": False,
            "result": "success",
            "reason": "moving doc",
        }
    )
    write_log(log_entry_std)

    res = read_log(limit=2)
    entries = [json.loads(x) for x in res["entries"]]

    # Assert path redaction
    assert entries[0]["path"] == "<sensitive file>"
    assert entries[1]["path"] == "to/regular_file.txt"


def test_registry_list_and_get():
    """Assert registry registers, gets, and lists tools correctly."""
    from app.mcp_tools.registry import get_tool, list_tools, normalize_name

    # 1. Normalization tests
    assert normalize_name("ListFiles") == "list_files"
    assert normalize_name("list-files") == "list_files"
    assert normalize_name("LIST_FILES") == "list_files"
    assert normalize_name("listFiles") == "list_files"
    assert normalize_name("  list-files  ") == "list_files"
    assert normalize_name("list files") == "list_files"

    tools = list_tools()
    assert len(tools) == 10
    assert any(x["name"] == "list_files" for x in tools)
    assert "input_schema" in tools[0]
    assert "output_schema" in tools[0]
    assert tools[0].get("version") == "1.0"

    func = get_tool("list files")
    assert callable(func)

    with pytest.raises(KeyError):
        get_tool("nonexistent_tool")


def test_registry_test_tool(mock_config_paths):
    """Assert registry test_tool validates arguments and checks policy."""
    tmp_path, _ = mock_config_paths
    from app.mcp_tools.registry import test_tool

    # 1. Unknown tool
    res = test_tool("nonexistent")
    assert "error" in res
    assert res["error"]["type"] == "ToolNotFound"
    assert res["error"]["details"]["tool"] == "nonexistent"
    assert res["error"]["details"]["schema_validated"] is False

    # 2. Missing argument
    res = test_tool("list_files")
    assert "error" in res
    assert res["error"]["type"] == "SchemaError"
    assert "Missing required argument" in res["error"]["message"]
    assert res["error"]["details"]["schema_validated"] is False
    assert "missing_key" in res["error"]["details"]["schema_diff"]

    # 3. Coercion tests ("10" -> 10)
    res = test_tool("read_log", limit="10")
    assert "status" in res or "error" in res
    # Even if it errors due to empty log, the type coercion should succeed (it won't raise SchemaError for type mismatch)
    if "error" in res:
        assert res["error"]["type"] != "SchemaError"

    # Invalid integer type error format
    res = test_tool("read_log", limit="not_an_int")
    assert "error" in res
    assert res["error"]["type"] == "SchemaError"
    assert "must be an integer" in res["error"]["message"]
    assert res["error"]["details"]["schema_diff"]["expected_type"] == "integer"

    # 4. Unknown key
    res = test_tool("list_files", path=str(tmp_path), unexpected="extra")
    assert "error" in res
    assert res["error"]["type"] == "SchemaError"
    assert "Unexpected argument" in res["error"]["message"]

    # 5. Success run
    allowed_dir = tmp_path / "allowed"
    res = test_tool("list files", path=str(allowed_dir))
    assert res["status"] == "success"
    assert "files" in res["result"]

    # 6. Policy check is handled inside tool, but test_tool bubbles it up as ToolError
    res = test_tool("list_files", path="/Windows/System32")
    assert "error" in res
    assert res["error"]["type"] == "ToolError"
    assert res["error"]["details"]["schema_validated"] is True
    assert res["error"]["details"]["normalized_name"] == "list_files"


def test_safety_symlink_and_traversal(mock_config_paths):
    """Assert symlinks and traversal paths are blocked."""
    tmp_path, _ = mock_config_paths
    from app.mcp_tools.registry import test_tool

    allowed_dir = tmp_path / "allowed"

    # 1. Directory Traversal
    traversal_path = str(allowed_dir / ".." / "allowed" / "test.txt")
    res = test_tool("list_files", path=traversal_path)
    assert "error" in res
    assert res["error"]["details"].get("directory_traversal") is True

    # 2. Symlinks
    link_path = allowed_dir / "my_link"
    target_file = allowed_dir / "target.txt"
    target_file.write_text("hello")

    # Create symlink if supported by OS
    try:
        os.symlink(str(target_file), str(link_path))
        res = test_tool("read_file_metadata", path=str(link_path))
        assert "error" in res
        assert res["error"]["details"].get("symlink_blocked") is True
    except OSError:
        # Skip if symlink creation is not permitted by OS security policy
        pass


def test_compute_hash_large_file(mock_config_paths, monkeypatch):
    """Assert compute_hash rejects files >2GB with details."""
    tmp_path, _ = mock_config_paths
    from app.mcp_tools.registry import test_tool

    std_file = tmp_path / "allowed" / "large_file.bin"
    std_file.write_text("dummy content")

    # Mock os.path.getsize to simulate a 3GB file
    monkeypatch.setattr(os.path, "getsize", lambda x: 3 * 1024 * 1024 * 1024)

    res = test_tool("compute_hash", path=str(std_file))
    assert "error" in res
    assert res["error"]["details"].get("file_too_large") is True
    assert res["error"]["details"].get("max_supported_size") == "2GB"


def test_log_rotation_guard(tmp_path, monkeypatch):
    """Assert logs are rotated automatically when exceeding 10MB."""
    mock_log = tmp_path / "audit.log"
    monkeypatch.setenv("CLEANSLATE_LOG_PATH", str(mock_log))

    from app.security.audit_logger import log_action

    # 1. Write an entry to create the file
    log_action("TestNode", "test", None, False, "none", "success")
    assert mock_log.exists()

    # 2. Mock os.path.getsize to simulate file > 10MB
    monkeypatch.setattr(os.path, "getsize", lambda x: 11 * 1024 * 1024)

    # 3. Next log should trigger rotation
    log_action("TestNode", "test", None, False, "none", "success")

    backup_log = tmp_path / "audit.log.1"
    assert backup_log.exists()
    assert mock_log.exists()

    # The rotated file should have a rotation success entry as the first line
    with open(mock_log, encoding="utf-8") as f:
        first_line = json.loads(f.readline())
        assert first_line["action_type"] == "rotation"
        assert first_line["reason"] == "log_file_exceeded_10MB"


def test_atomic_move_fallback(mock_config_paths, monkeypatch):
    """Assert move_file tries os.replace first and falls back to shutil.move."""
    tmp_path, _ = mock_config_paths
    from app.mcp_tools.registry import test_tool

    src = tmp_path / "allowed" / "src.txt"
    src.write_text("data")
    dest = tmp_path / "allowed" / "dest.txt"

    # Mock os.replace to raise OSError (to trigger fallback)
    def mock_replace(s, d):
        raise OSError("Cross-device link")

    monkeypatch.setattr(os, "replace", mock_replace)

    res = test_tool("move_file", source=str(src), destination=str(dest))
    assert res["status"] == "success"
    assert res["result"].get("atomic_fallback_used") is True
    assert dest.exists()


def test_delete_file_safety_details(mock_config_paths, monkeypatch):
    """Assert delete_file error details are populated correctly on policy block."""
    tmp_path, mock_policy_file = mock_config_paths
    from app.mcp_tools.registry import test_tool

    # Write policy with safe_mode=True
    with open(mock_policy_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "allowed_paths": [str(tmp_path / "allowed")],
                "blocked_paths": [],
                "safe_mode": True,
            },
            f,
        )

    target = tmp_path / "allowed" / "junk.txt"
    target.write_text("delete me")

    res = test_tool("delete_file", path=str(target), hitl_approved=True)
    assert "error" in res
    assert res["error"]["details"].get("safe_mode_blocked") is True
    assert res["error"]["details"].get("safe_mode") is True


def test_junction_blocking_mock(mock_config_paths, monkeypatch):
    """Assert Windows junction is detected and blocked."""
    tmp_path, _ = mock_config_paths
    from app.mcp_tools.registry import test_tool

    target = tmp_path / "allowed" / "junction_dir"
    target.mkdir(exist_ok=True)

    # Mock os.lstat to return a st_reparse_tag == 0xA0000003
    class MockStat:
        st_reparse_tag = 0xA0000003
        st_size = 0
        st_mtime = 1000
        st_ctime = 1000
        st_mode = 16877  # directory S_IFDIR

    monkeypatch.setattr(os, "lstat", lambda x: MockStat())

    res = test_tool("list_files", path=str(target))
    assert "error" in res
    assert res["error"]["details"].get("junction_blocked") is True


def test_realpath_symlink_escaping_scope(mock_config_paths, monkeypatch):
    """Assert that a symlink escaping allowed scope is blocked and flagged as symlink_blocked."""
    tmp_path, _ = mock_config_paths
    from app.mcp_tools.registry import test_tool

    target = tmp_path / "allowed" / "escaped_link.txt"

    # Mock realpath to return a path outside allowed scope (e.g. /Windows/System32)
    monkeypatch.setattr(os.path, "realpath", lambda x: "/Windows/System32/file.txt")

    res = test_tool("read_file_metadata", path=str(target))
    assert "error" in res
    assert res["error"]["details"].get("symlink_blocked") is True
    assert res["error"]["details"].get("directory_traversal") is True
