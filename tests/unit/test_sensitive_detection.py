import json
from unittest.mock import MagicMock, patch

from app.nodes.classification_node import ClassifiedFile, FileCategory
from app.nodes.duplicate_detection_node import DuplicateDetectionOutput
from app.nodes.file_discovery_node import FileMetadata, FolderScopePolicy
from app.nodes.sensitive_detection_node import (
    sensitive_detection_node,
)


@patch("google.genai.Client")
def test_sensitive_detection(mock_client_class, tmp_path) -> None:
    # 1. Setup paths
    allowed_dir = tmp_path / "allowed"
    blocked_dir = tmp_path / "blocked"
    allowed_dir.mkdir()
    blocked_dir.mkdir()

    # Create dummy files
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
        reasoning="",
    )

    # Mock Gemini behavior:
    # It will generate content. We want to check the prompts or mock responses.
    # For file_sensitive (tax_return.txt), return sensitive=True, type=tax
    # For file_safe (public_info.txt), return sensitive=False, type=none
    # file_blocked should NEVER trigger generate_content because it is blocked.
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
    output = sensitive_detection_node(node_input)

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
    assert "SSN" in sensitive_entry.reasoning

    # Safe check
    safe_entry = lookup[str(file_safe)]
    assert safe_entry.sensitive is False
    assert safe_entry.sensitivity_type == "none"

    # Make sure generate_content was called exactly 2 times (never for the blocked path)
    assert mock_client.models.generate_content.call_count == 2
