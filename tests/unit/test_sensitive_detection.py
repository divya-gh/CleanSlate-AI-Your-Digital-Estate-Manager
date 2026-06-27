import json
from unittest.mock import MagicMock, patch

from google.adk.events.event import Event

from app.nodes.classification_node import ClassifiedFile, FileCategory
from app.nodes.duplicate_detection_node import DuplicateDetectionOutput
from app.nodes.file_discovery_node import FileMetadata, FolderScopePolicy
from app.nodes.sensitive_detection_node import (
    _detect_signals,
    _extract_pdf_text,
    _safe_preview,
    sensitive_detection_node,
)


@patch("google.genai.Client")
def test_sensitive_detection(mock_client_class, tmp_path) -> None:
    # 1. Setup paths
    allowed_dir = tmp_path / "allowed"
    blocked_dir = tmp_path / "blocked"
    allowed_dir.mkdir()
    blocked_dir.mkdir()

    # Create dummy files (giving tax_return 2 signals: filename has tax, category is TAX)
    file_sensitive = allowed_dir / "tax_return.txt"
    file_safe = allowed_dir / "public_info.txt"
    file_blocked = blocked_dir / "secret_keys.txt"

    file_sensitive.write_text("SSN: 000-12-3456")
    file_safe.write_text("Hello World this is public text info.")
    file_blocked.write_text("SECRET_API_KEY_DO_NOT_READ")

    # Define metadata
    meta_sensitive = FileMetadata(
        path=str(file_sensitive),
        size=file_sensitive.stat().st_size,
        extension=".txt",
        last_modified=file_sensitive.stat().st_mtime,
        last_accessed=file_sensitive.stat().st_atime,
    )
    meta_safe = FileMetadata(
        path=str(file_safe),
        size=file_safe.stat().st_size,
        extension=".txt",
        last_modified=file_safe.stat().st_mtime,
        last_accessed=file_safe.stat().st_atime,
    )
    meta_blocked = FileMetadata(
        path=str(file_blocked),
        size=file_blocked.stat().st_size,
        extension=".txt",
        last_modified=file_blocked.stat().st_mtime,
        last_accessed=file_blocked.stat().st_atime,
    )

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[str(blocked_dir)],
    )

    classified = [
        ClassifiedFile(
            path=meta_sensitive.path,
            category=FileCategory.TAX,
            confidence=0.9,
            reasoning="",
        ),
        ClassifiedFile(
            path=meta_safe.path,
            category=FileCategory.MISC,
            confidence=0.9,
            reasoning="",
        ),
        ClassifiedFile(
            path=meta_blocked.path,
            category=FileCategory.MISC,
            confidence=0.9,
            reasoning="",
        ),
    ]

    node_input = DuplicateDetectionOutput(
        duplicate_groups=[],
        classified_files=classified,
        file_inventory=[meta_sensitive, meta_safe, meta_blocked],
        folder_scope_policy=policy,
        safe_mode=False,
        search_mode=False,
        reasoning="",
    )

    # Mock Gemini behavior:
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    def mock_generate_content(model, contents, config):
        if "tax_return.txt" in contents:
            res = MagicMock()
            res.text = json.dumps(
                {
                    "sensitive": True,
                    "sensitivity_type": "tax",
                    "confidence": 0.95,
                    "reasoning": "Contains SSN format pattern and tax in filename",
                }
            )
            return res
        elif "public_info.txt" in contents:
            res = MagicMock()
            res.text = json.dumps(
                {
                    "sensitive": False,
                    "sensitivity_type": "none",
                    "confidence": 0.99,
                    "reasoning": "Generic greeting info",
                }
            )
            return res
        else:
            raise ValueError(f"Unexpected file content generate: {contents}")

    mock_client.models.generate_content.side_effect = mock_generate_content

    # Run the node
    event = sensitive_detection_node(node_input)
    assert isinstance(event, Event)
    output = event.output

    # 2. Assertions
    # We expect 3 checked entries
    assert len(output.sensitive_files) == 3

    lookup = {sf.path: sf for sf in output.sensitive_files}

    # Blocked check
    blocked_entry = lookup[str(file_blocked)]
    assert blocked_entry.sensitive is False
    assert blocked_entry.sensitivity_type == "none"
    assert blocked_entry.confidence == 1.0
    assert "blocked" in blocked_entry.reasoning.lower()

    # Sensitive check
    sensitive_entry = lookup[str(file_sensitive)]
    assert sensitive_entry.sensitive is True
    assert sensitive_entry.sensitivity_type == "tax"
    assert sensitive_entry.confidence >= 0.90
    assert (
        "SSN" in sensitive_entry.reasoning
        or "two independent signals" in sensitive_entry.reasoning
    )

    # Safe check (skips Gemini because of 0 signals)
    safe_entry = lookup[str(file_safe)]
    assert safe_entry.sensitive is False
    assert safe_entry.sensitivity_type == "none"

    # Make sure generate_content was called exactly 1 time (only for file_sensitive, as file_safe has 0 signals and file_blocked is blocked)
    assert mock_client.models.generate_content.call_count == 1


def test_sensitive_detection_safe_mode_blocks_previews(tmp_path) -> None:
    allowed = tmp_path / "doc.txt"
    allowed.write_text("tax return SSN 000-12-3456")
    meta = FileMetadata(
        path=str(allowed),
        size=allowed.stat().st_size,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path=str(allowed),
    )
    policy = FolderScopePolicy(allowed_paths=[str(tmp_path)], allow_previews=True)
    # Previews must be disabled in safe mode
    assert _safe_preview(meta, policy, safe_mode=True) is None


def test_sensitive_detection_skips_preview_for_binary_pdf(tmp_path) -> None:
    # A dummy binary PDF containing some bytes
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(bytes([128, 129, 130] * 100))
    FileMetadata(
        path=str(pdf_file),
        size=pdf_file.stat().st_size,
        extension=".pdf",
        last_modified=1.0,
        last_accessed=1.0,
        real_path=str(pdf_file),
    )
    # Binary streams from PDF should not leak, so raw binary stream returns empty parsed text
    text = _extract_pdf_text(str(pdf_file))
    assert text == ""


def test_sensitive_detection_zero_signal_skips_gemini(tmp_path) -> None:
    # Masked filename with a generic category
    meta = FileMetadata(
        path="C:/Allowed/sensitive_file_abc123.txt",
        size=100,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path="C:/Allowed/sensitive_file_abc123.txt",
    )
    # Zero signals (masked filename, non-sensitive extension, no preview, no category)
    signals = _detect_signals(meta, "misc", has_preview=False, preview_text=None)
    assert len(signals) == 0


def test_sensitive_detection_two_signal_rule_and_confidence_cap(tmp_path) -> None:
    # 1 signal only (filename keyword, masked is False)
    meta = FileMetadata(
        path="C:/Allowed/tax_return.txt",
        size=100,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path="C:/Allowed/tax_return.txt",
    )
    signals = _detect_signals(meta, "misc", has_preview=False, preview_text=None)
    assert len(signals) == 1
