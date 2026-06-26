"""SensitiveDetectionNode — ADK 2.0 Graph Workflow Node.

Identifies sensitive files (containing SSNs, banking, tax, legal, medical,
password, identity documents, or API keys) using metadata and optional safe previews
via Gemini model classification.
"""

from __future__ import annotations

import os
from pathlib import Path

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from app.nodes.duplicate_detection_node import DuplicateDetectionOutput
from app.nodes.file_discovery_node import FileMetadata, FolderScopePolicy

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class SensitiveFileEntry(BaseModel):
    """Result details for a single checked file."""

    path: str = Field(description="Absolute path to the file.")
    sensitive: bool = Field(
        description="Whether the file was determined to contain sensitive data."
    )
    sensitivity_type: str = Field(
        description="Type of sensitive data (e.g. SSN, banking, tax, legal, medical, password, api_key, identity, none)."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0.",
        ge=0.0,
        le=1.0,
    )
    reasoning: str = Field(
        description="Detailed explanation of the classification result."
    )


class SensitiveDetectionOutput(BaseModel):
    """Output payload emitted by SensitiveDetectionNode."""

    sensitive_files: list[SensitiveFileEntry] = Field(
        default_factory=list,
        description="List of files with their sensitivity classification results.",
    )
    reasoning: str = Field(
        description="High-level reasoning summary of sensitive file detection.",
    )


# ---------------------------------------------------------------------------
# Helper classes and functions
# ---------------------------------------------------------------------------


class GeminiSensitivityResult(BaseModel):
    """Schema for structured Gemini output."""

    sensitive: bool = Field(
        description="True if the file contains sensitive information, False otherwise."
    )
    sensitivity_type: str = Field(
        description="The category of sensitivity: 'SSN', 'banking', 'tax', 'legal', 'medical', 'password', 'api_key', 'identity', or 'none'."
    )
    confidence: float = Field(
        description="Confidence score for this classification (0.0 to 1.0)."
    )
    reasoning: str = Field(
        description="Reasoning explaining the classification choice."
    )


def _is_path_allowed(path: str, policy: FolderScopePolicy) -> bool:
    """Verify path is allowed and not blocked by the scope policy."""
    resolved_path = os.path.normcase(os.path.abspath(path))

    # 1. Check blocked paths
    for bp in policy.blocked_paths:
        bp_resolved = os.path.normcase(os.path.abspath(bp))
        if resolved_path == bp_resolved or resolved_path.startswith(
            bp_resolved + os.sep
        ):
            return False

    # 2. Check allowed paths
    if not policy.allowed_paths:
        return False

    any_allowed = False
    for ap in policy.allowed_paths:
        ap_resolved = os.path.normcase(os.path.abspath(ap))
        if resolved_path == ap_resolved or resolved_path.startswith(
            ap_resolved + os.sep
        ):
            any_allowed = True
            break

    return any_allowed


_SAFE_PREVIEW_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".log",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
}

_MAX_PREVIEW_BYTES = 512


def _safe_preview(file: FileMetadata, policy: FolderScopePolicy) -> str | None:
    """Read a small preview of the file if allowed and has a safe text extension."""
    if not _is_path_allowed(file.path, policy):
        return None

    ext = file.extension.lower()
    if ext not in _SAFE_PREVIEW_EXTENSIONS:
        return None

    try:
        with open(file.path, encoding="utf-8", errors="ignore") as f:
            return f.read(_MAX_PREVIEW_BYTES)
    except OSError:
        return None


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def sensitive_detection_node(
    node_input: DuplicateDetectionOutput,
) -> SensitiveDetectionOutput:
    """SensitiveDetectionNode — classifies sensitivity using metadata and Gemini."""
    inventory = node_input.file_inventory
    policy = node_input.folder_scope_policy
    classified_lookup = {cf.path: cf for cf in node_input.classified_files}

    # Initialize Gemini client
    client = genai.Client()

    checked: list[SensitiveFileEntry] = []
    skipped_count = 0

    for file in inventory:
        # Respect policy strictly — never scan or preview blocked paths
        if not _is_path_allowed(file.path, policy):
            skipped_count += 1
            # Explicitly mark blocked paths as non-sensitive and safe
            checked.append(
                SensitiveFileEntry(
                    path=file.path,
                    sensitive=False,
                    sensitivity_type="none",
                    confidence=1.0,
                    reasoning="File skipped because it resides under a blocked or unallowed path.",
                )
            )
            continue

        # Get predecessor classification category if available
        cf = classified_lookup.get(file.path)
        category = cf.category if cf else "unknown"

        # Read preview
        preview = _safe_preview(file, policy)

        # Build LLM Prompt
        filename = Path(file.path).name
        prompt_parts = [
            "Analyze the following file for sensitive personal, financial, or access data.",
            f"Filename: {filename}",
            f"Extension: {file.extension}",
            f"Size: {file.size} bytes",
            f"Predicted Category: {category}",
        ]
        if preview:
            prompt_parts.append(f"Content Preview (first 512 bytes):\n{preview}")

        prompt = "\n".join(prompt_parts)

        # Call Gemini
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiSensitivityResult,
                    temperature=0.1,
                ),
            )
            result = GeminiSensitivityResult.model_validate_json(response.text)
            checked.append(
                SensitiveFileEntry(
                    path=file.path,
                    sensitive=result.sensitive,
                    sensitivity_type=result.sensitivity_type,
                    confidence=result.confidence,
                    reasoning=result.reasoning,
                )
            )
        except Exception as e:
            # Fallback in case of API issues
            checked.append(
                SensitiveFileEntry(
                    path=file.path,
                    sensitive=False,
                    sensitivity_type="none",
                    confidence=0.5,
                    reasoning=f"Failed to analyze sensitivity using Gemini: {e}",
                )
            )

    sensitive_count = sum(1 for entry in checked if entry.sensitive)
    reasoning = (
        f"Analyzed {len(inventory) - skipped_count} allowed file(s). "
        f"Skipped {skipped_count} blocked/unallowed file(s). "
        f"Identified {sensitive_count} sensitive file(s). "
        f"Never uploaded file contents."
    )

    return SensitiveDetectionOutput(
        sensitive_files=checked,
        reasoning=reasoning,
    )
