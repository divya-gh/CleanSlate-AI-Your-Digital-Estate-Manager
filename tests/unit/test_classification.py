from unittest.mock import MagicMock, patch

from google.adk.events.event import Event

from app.nodes.classification_node import (
    ClassificationOutput,
    FileCategory,
    _post_process_classification,
    _safe_preview,
    classification_node,
)
from app.nodes.file_discovery_node import (
    FileDiscoveryOutput,
    FileMetadata,
    FolderScopePolicy,
)


def test_safe_preview_binary_and_size_rules(tmp_path) -> None:
    # 1. Size constraint
    large_file = tmp_path / "large.txt"
    large_file.write_text("a" * (10 * 1024 * 1024 + 1))
    meta_large = FileMetadata(
        path=str(large_file),
        size=large_file.stat().st_size,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path=str(large_file),
    )
    assert _safe_preview(meta_large) is None

    # 2. Plain text safe extension
    unsupported = tmp_path / "image.png"
    unsupported.write_text("binary content")
    meta_unsupported = FileMetadata(
        path=str(unsupported),
        size=unsupported.stat().st_size,
        extension=".png",
        last_modified=1.0,
        last_accessed=1.0,
        real_path=str(unsupported),
    )
    assert _safe_preview(meta_unsupported) is None

    # 3. Binary detection heuristic (>20% bytes > 127)
    binary_file = tmp_path / "fake_text.txt"
    # Write binary bytes containing non-ASCII values (>127)
    binary_file.write_bytes(bytes([128, 129, 130, 131, 132, 65, 66, 67, 68, 69]))
    meta_binary = FileMetadata(
        path=str(binary_file),
        size=binary_file.stat().st_size,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path=str(binary_file),
    )
    # 5 out of 10 bytes are > 127 (50%), so it should be skipped
    assert _safe_preview(meta_binary) is None

    # 4. Valid plain text file
    valid_file = tmp_path / "valid.txt"
    valid_file.write_text("Hello World! This is plain text.")
    meta_valid = FileMetadata(
        path=str(valid_file),
        size=valid_file.stat().st_size,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path=str(valid_file),
    )
    assert _safe_preview(meta_valid) == "Hello World! This is plain text."


def test_post_process_classification_safety_caps() -> None:
    # 1. Sensitive Category (tax/medical) requires 2 independent signals
    meta = FileMetadata(
        path="C:/Allowed/tax_return.txt",
        size=100,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path="C:/Allowed/tax_return.txt",
    )
    # Category = tax, filename has 'tax', but no preview/extension match. Only 1 signal.
    # Should fallback to misc and cap confidence at 0.40
    cat, conf, reason = _post_process_classification(
        file=meta,
        category=FileCategory.TAX,
        confidence=0.85,
        reasoning="Filename contains tax",
        has_preview=False,
        preview_text=None,
    )
    assert cat == FileCategory.MISC
    assert conf <= 0.40
    assert "reverted to misc" in reason

    # 2. Category = tax, filename has 'tax' and preview contains 'tax' -> 2 signals
    cat, conf, reason = _post_process_classification(
        file=meta,
        category=FileCategory.TAX,
        confidence=0.85,
        reasoning="Filename and preview contain tax",
        has_preview=True,
        preview_text="Here is my tax summary",
    )
    # Both are non-strong evidence signals overall, so confidence is capped at 0.40 but category is kept
    assert cat == FileCategory.TAX
    assert conf <= 0.40

    # 3. Masked filename cannot use filename keyword
    masked_meta = FileMetadata(
        path="C:/Allowed/sensitive_file_abc123.txt",
        size=100,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path="C:/Allowed/sensitive_file_abc123.txt",
    )
    # Try to classify as medical. Only extension signal or preview signal can be used, filename keyword is blocked.
    cat, conf, reason = _post_process_classification(
        file=masked_meta,
        category=FileCategory.MEDICAL,
        confidence=0.90,
        reasoning="Gemini reasoning",
        has_preview=True,
        preview_text="Some symptoms diagnostic report",
    )
    # Only 1 signal (preview keyword), filename is masked and extension is .txt. Reverts to misc.
    assert cat == FileCategory.MISC
    assert conf <= 0.40


def test_classification_mode_constraints(tmp_path) -> None:
    txt_file = tmp_path / "doc.txt"
    txt_file.write_text("Sample resume content.")

    meta = FileMetadata(
        path=str(txt_file),
        size=txt_file.stat().st_size,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path=str(txt_file),
    )

    policy = FolderScopePolicy(allowed_paths=[str(tmp_path)], allow_previews=True)

    # Mock Gemini Client and API response
    mock_response = MagicMock()
    mock_response.text = '{"category": "resume", "confidence": 0.85, "reasoning": "Mentions resume in text"}'

    with patch("google.genai.Client") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.models.generate_content.return_value = mock_response

        # 1. Safe Mode = True (Previews restricted)
        disc_output_safe = FileDiscoveryOutput(
            file_inventory=[meta],
            folder_scope_policy=policy,
            search_mode=False,
            safe_mode=True,
            reasoning="Safe mode scan",
        )
        event = classification_node(disc_output_safe)
        assert isinstance(event, Event)
        out = event.output
        assert isinstance(out, ClassificationOutput)
        assert out.safe_mode is True
        assert out.classified_files[0].classification_method == "metadata_only"

        # 2. Search Mode = True (Previews restricted)
        disc_output_search = FileDiscoveryOutput(
            file_inventory=[meta],
            folder_scope_policy=policy,
            search_mode=True,
            safe_mode=False,
            reasoning="Search mode scan",
        )
        event = classification_node(disc_output_search)
        out = event.output
        assert out.search_mode is True
        assert out.classified_files[0].classification_method == "metadata_only"

        # 3. Interactive Mode (Previews allowed and performed)
        disc_output_interactive = FileDiscoveryOutput(
            file_inventory=[meta],
            folder_scope_policy=policy,
            search_mode=False,
            safe_mode=False,
            reasoning="Interactive scan",
        )
        event = classification_node(disc_output_interactive)
        out = event.output
        assert out.safe_mode is False
        assert out.search_mode is False
        assert out.classified_files[0].classification_method == "metadata_plus_preview"
        assert event.actions.route == "dedupe"
