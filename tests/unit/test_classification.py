from unittest.mock import MagicMock, patch

from google.adk.events.event import Event

from app.nodes.classification_node import (
    ClassificationOutput,
    FileCategory,
    _post_process_classification,
    classification_node,
)
from app.nodes.file_discovery_node import (
    FileDiscoveryOutput,
    FileMetadata,
    FolderScopePolicy,
)


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
    # Category = tax, filename has 'tax', but no extension or parent folder match. Only 1 signal.
    # Should fallback to misc and cap confidence at 0.40
    cat, conf, reason = _post_process_classification(
        file=meta,
        category=FileCategory.TAX,
        confidence=0.85,
        reasoning="Filename contains tax",
    )
    assert cat == FileCategory.MISC
    assert conf <= 0.40
    assert "reverted to misc" in reason

    # 2. Category = tax, filename has 'tax' and parent folder has 'tax' -> 2 signals
    meta_two_signals = FileMetadata(
        path="C:/Allowed/tax_files/tax_return.txt",
        size=100,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path="C:/Allowed/tax_files/tax_return.txt",
    )
    cat, conf, reason = _post_process_classification(
        file=meta_two_signals,
        category=FileCategory.TAX,
        confidence=0.85,
        reasoning="Filename and parent folder contain tax",
    )
    # Both are non-strong evidence signals overall, so confidence is capped at 0.40 but category is kept
    assert cat == FileCategory.TAX
    assert conf <= 0.40

    # 3. Masked filename cannot use filename keyword
    masked_meta = FileMetadata(
        path="C:/Allowed/tax_files/sensitive_file_abc123.txt",
        size=100,
        extension=".txt",
        last_modified=1.0,
        last_accessed=1.0,
        real_path="C:/Allowed/tax_files/sensitive_file_abc123.txt",
    )
    # Try to classify as medical. Filename is masked, extension is txt. Parent folder is 'tax_files'.
    # 0 signals for medical. Reverts to misc.
    cat, conf, reason = _post_process_classification(
        file=masked_meta,
        category=FileCategory.MEDICAL,
        confidence=0.90,
        reasoning="Gemini reasoning",
    )
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

        # 1. Safe Mode = True
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

        # 2. Search Mode = True
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

        # 3. Interactive Mode (Metadata-only is still enforced now)
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
        assert out.classified_files[0].classification_method == "metadata_only"
        assert event.actions.route == "dedupe"
