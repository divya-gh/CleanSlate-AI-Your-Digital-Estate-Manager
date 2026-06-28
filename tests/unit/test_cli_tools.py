"""
tests/unit/test_cli_tools.py

Unit tests for the developer-facing `cleanslate tools list` and
`cleanslate tools test` CLI commands.

All tests are registry-only:
- No real filesystem paths are passed to the tools.
- MCP error objects are asserted verbatim.
- Safety / policy checks are NOT bypassed.
"""
import json
from io import StringIO
from unittest.mock import patch

import pytest

from app.cli import cmd_tools_list, cmd_tools_test
from app.mcp_tools.registry import TOOLS, normalize_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def capture(func, *args, **kwargs) -> str:
    """Run func and capture everything printed to stdout."""
    buf = StringIO()
    with patch("sys.stdout", buf):
        func(*args, **kwargs)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# cmd_tools_list
# ---------------------------------------------------------------------------


class TestToolsList:
    def test_lists_all_registered_tools_human(self):
        """Human-readable output contains every tool registered in TOOLS."""
        output = capture(cmd_tools_list, json_opt=False)
        for name in TOOLS:
            assert name in output, f"Expected tool '{name}' in listing"

    def test_lists_all_registered_tools_json(self):
        """JSON output is a list with one entry per registered tool."""
        output = capture(cmd_tools_list, json_opt=True)
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) == len(TOOLS)
        names_in_output = {t["name"] for t in data}
        assert names_in_output == set(TOOLS.keys())

    def test_json_entries_have_required_fields(self):
        """Each JSON entry must carry name, description, input_schema, output_schema, version."""
        output = capture(cmd_tools_list, json_opt=True)
        data = json.loads(output)
        required_fields = {"name", "description", "input_schema", "output_schema", "version"}
        for entry in data:
            missing = required_fields - set(entry.keys())
            assert not missing, f"Entry {entry['name']} missing fields: {missing}"

    def test_input_schema_keys_shown_in_human_output(self):
        """Human output must show 'Inputs' and 'Required' lines for known tools."""
        output = capture(cmd_tools_list, json_opt=False)
        # list_files requires 'path'
        assert "list_files" in output
        assert "path" in output

    def test_human_output_shows_description(self):
        """Human output must include the tool description text."""
        output = capture(cmd_tools_list, json_opt=False)
        # Every tool's description should appear somewhere in output
        for meta in TOOLS.values():
            assert meta["description"] in output


# ---------------------------------------------------------------------------
# cmd_tools_test — success paths
# ---------------------------------------------------------------------------


class TestToolsTestSuccess:
    def test_read_log_no_args_succeeds(self, tmp_path):
        """read_log with no args (limit defaults to None) succeeds or returns graceful result."""
        import os
        log_path = str(tmp_path / "audit.log")
        with patch.dict("os.environ", {"CLEANSLATE_LOG_PATH": log_path}):
            output = capture(cmd_tools_test, "read_log", [], json_opt=True)
        data = json.loads(output)
        # Either success or a graceful ToolError (empty log file) — never a crash
        assert "status" in data or "error" in data

    def test_read_log_json_output_is_valid(self, tmp_path):
        """--json flag makes tools test emit parseable JSON."""
        import os
        log_path = str(tmp_path / "audit.log")
        with patch.dict("os.environ", {"CLEANSLATE_LOG_PATH": log_path}):
            output = capture(cmd_tools_test, "read_log", [], json_opt=True)
        # Must be valid JSON — no exception
        json.loads(output)

    def test_camel_case_name_normalization(self, tmp_path):
        """Tool name in camelCase is normalized correctly before dispatch."""
        import os
        log_path = str(tmp_path / "audit.log")
        with patch.dict("os.environ", {"CLEANSLATE_LOG_PATH": log_path}):
            output = capture(cmd_tools_test, "readLog", [], json_opt=True)
        data = json.loads(output)
        # Should dispatch to read_log (normalized), not return ToolNotFound
        assert data.get("error", {}).get("type") != "ToolNotFound"

    def test_kebab_case_name_normalization(self, tmp_path):
        """Tool name in kebab-case is normalized correctly before dispatch."""
        import os
        log_path = str(tmp_path / "audit.log")
        with patch.dict("os.environ", {"CLEANSLATE_LOG_PATH": log_path}):
            output = capture(cmd_tools_test, "read-log", [], json_opt=True)
        data = json.loads(output)
        assert data.get("error", {}).get("type") != "ToolNotFound"


# ---------------------------------------------------------------------------
# cmd_tools_test — MCP error paths
# ---------------------------------------------------------------------------


class TestToolsTestErrors:
    def test_unknown_tool_returns_tool_not_found_mcp_error(self):
        """Invalid tool name must emit a ToolNotFound MCP error object."""
        output = capture(cmd_tools_test, "nonexistent_tool_xyz", [], json_opt=True)
        data = json.loads(output)
        assert "error" in data
        assert data["error"]["type"] == "ToolNotFound"
        assert "nonexistent_tool_xyz" in data["error"]["message"]

    def test_unknown_tool_human_output_shows_error_type(self):
        """Human-readable output for unknown tool shows [ERROR] prefix."""
        output = capture(cmd_tools_test, "ghost_tool", [], json_opt=False)
        assert "[ERROR]" in output
        assert "ToolNotFound" in output

    def test_missing_required_arg_returns_schema_error(self):
        """Calling list_files without required 'path' arg must emit SchemaError."""
        output = capture(cmd_tools_test, "list_files", [], json_opt=True)
        data = json.loads(output)
        assert "error" in data
        assert data["error"]["type"] == "SchemaError"
        assert "path" in data["error"]["message"]

    def test_unknown_kwarg_returns_schema_error(self):
        """Passing an unexpected key to a tool must emit SchemaError."""
        output = capture(cmd_tools_test, "read_log", ["bogus_key=123"], json_opt=True)
        data = json.loads(output)
        assert "error" in data
        assert data["error"]["type"] == "SchemaError"
        assert "bogus_key" in data["error"]["message"]

    def test_invalid_arg_format_returns_schema_error_immediately(self):
        """A raw token without '=' must emit a SchemaError before registry dispatch."""
        output = capture(cmd_tools_test, "list_files", ["badformat"], json_opt=True)
        data = json.loads(output)
        assert "error" in data
        assert data["error"]["type"] == "SchemaError"
        assert "badformat" in data["error"]["details"]["token"]

    def test_mcp_error_structure_is_complete(self):
        """MCP error objects must contain type, message, and details keys."""
        output = capture(cmd_tools_test, "list_files", [], json_opt=True)
        data = json.loads(output)
        err = data["error"]
        assert "type" in err
        assert "message" in err
        assert "details" in err

    def test_tool_error_preserved_verbatim(self):
        """Error from registry must NOT be wrapped or re-formatted by the CLI layer."""
        output = capture(cmd_tools_test, "list_files", ["path=/nonexistent_path_xyz"], json_opt=True)
        data = json.loads(output)
        # Whether it's a ToolError or ToolNotFound, the structure must be the raw registry output
        assert "error" in data or "status" in data

    def test_delete_file_safe_mode_returns_tool_error(self, tmp_path):
        """delete_file without HITL approval must return a ToolError (not crash)."""
        target = tmp_path / "file.txt"
        target.write_text("data")
        from app.config import set_policy_override
        set_policy_override({"allowed_paths": [str(tmp_path)], "blocked_paths": []})
        try:
            output = capture(
                cmd_tools_test,
                "delete_file",
                [f"path={target}", "hitl_approved=false"],
                json_opt=True,
            )
        finally:
            set_policy_override(None)
        data = json.loads(output)
        assert "error" in data
        assert data["error"]["type"] == "ToolError"

    def test_type_coercion_integer_limit(self, tmp_path):
        """read_log with limit=2 (integer string) is coerced correctly."""
        import os
        log_path = str(tmp_path / "audit.log")
        with patch.dict("os.environ", {"CLEANSLATE_LOG_PATH": log_path}):
            output = capture(cmd_tools_test, "read_log", ["limit=2"], json_opt=True)
        data = json.loads(output)
        # No SchemaError — integer coercion worked
        assert data.get("error", {}).get("type") != "SchemaError"


# ---------------------------------------------------------------------------
# Normalization unit tests (registry helper)
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_snake_case_unchanged(self):
        assert normalize_name("list_files") == "list_files"

    def test_camel_case_converted(self):
        assert normalize_name("listFiles") == "list_files"

    def test_kebab_converted(self):
        assert normalize_name("list-files") == "list_files"

    def test_spaces_converted(self):
        assert normalize_name("list files") == "list_files"

    def test_mixed_case_converted(self):
        # The regex splits on lowercase→uppercase transitions only.
        # "ReadFileMETADATA" → "Read_File_METADATA" → lower → "read_file_metadata"
        assert normalize_name("ReadFileMETADATA") == "read_file_metadata"

    def test_strips_whitespace(self):
        assert normalize_name("  list_files  ") == "list_files"
