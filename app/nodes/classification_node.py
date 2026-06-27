"""ClassificationNode — ADK 2.0 Graph Workflow Node.

Uses Gemini reasoning to classify each file from file_inventory into
semantic categories based on metadata and optional safe content previews.
Enforces strict safe/search mode restrictions, binary checks, and safety-biased
confidence boundaries.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from google import genai
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from app.nodes.file_discovery_node import (
    FileDiscoveryOutput,
    FileMetadata,
    FolderScopePolicy,
    resolve_real_path,
)

# ---------------------------------------------------------------------------
# Category enum
# ---------------------------------------------------------------------------


class FileCategory(StrEnum):
    """Supported classification categories per SDD Master Spec §6.3."""

    RESUME = "resume"
    TAX = "tax"
    MEDICAL = "medical"
    SCREENSHOT = "screenshot"
    INVOICE = "invoice"
    SCHOOL = "school"
    SOURCE_CODE = "source_code"
    MEDIA = "media"
    MISC = "misc"


# ---------------------------------------------------------------------------
# Extension → category heuristic map
# ---------------------------------------------------------------------------

_EXTENSION_HINTS: dict[str, FileCategory] = {
    # Source code
    ".py": FileCategory.SOURCE_CODE,
    ".js": FileCategory.SOURCE_CODE,
    ".ts": FileCategory.SOURCE_CODE,
    ".jsx": FileCategory.SOURCE_CODE,
    ".tsx": FileCategory.SOURCE_CODE,
    ".java": FileCategory.SOURCE_CODE,
    ".c": FileCategory.SOURCE_CODE,
    ".cpp": FileCategory.SOURCE_CODE,
    ".h": FileCategory.SOURCE_CODE,
    ".cs": FileCategory.SOURCE_CODE,
    ".go": FileCategory.SOURCE_CODE,
    ".rs": FileCategory.SOURCE_CODE,
    ".rb": FileCategory.SOURCE_CODE,
    ".php": FileCategory.SOURCE_CODE,
    ".swift": FileCategory.SOURCE_CODE,
    ".kt": FileCategory.SOURCE_CODE,
    ".sh": FileCategory.SOURCE_CODE,
    ".bat": FileCategory.SOURCE_CODE,
    ".ps1": FileCategory.SOURCE_CODE,
    ".sql": FileCategory.SOURCE_CODE,
    ".html": FileCategory.SOURCE_CODE,
    ".css": FileCategory.SOURCE_CODE,
    ".json": FileCategory.SOURCE_CODE,
    ".xml": FileCategory.SOURCE_CODE,
    ".yaml": FileCategory.SOURCE_CODE,
    ".yml": FileCategory.SOURCE_CODE,
    ".toml": FileCategory.SOURCE_CODE,
    ".ipynb": FileCategory.SOURCE_CODE,
    # Media
    ".mp4": FileCategory.MEDIA,
    ".mov": FileCategory.MEDIA,
    ".avi": FileCategory.MEDIA,
    ".mkv": FileCategory.MEDIA,
    ".mp3": FileCategory.MEDIA,
    ".wav": FileCategory.MEDIA,
    ".flac": FileCategory.MEDIA,
    ".jpg": FileCategory.MEDIA,
    ".jpeg": FileCategory.MEDIA,
    ".png": FileCategory.MEDIA,
    ".gif": FileCategory.MEDIA,
    ".bmp": FileCategory.MEDIA,
    ".svg": FileCategory.MEDIA,
    ".webp": FileCategory.MEDIA,
    ".heic": FileCategory.MEDIA,
    ".tiff": FileCategory.MEDIA,
}

# Filename patterns that strongly suggest a category
_FILENAME_KEYWORDS: dict[str, FileCategory] = {
    "resume": FileCategory.RESUME,
    "cv": FileCategory.RESUME,
    "curriculum": FileCategory.RESUME,
    "tax": FileCategory.TAX,
    "w2": FileCategory.TAX,
    "1099": FileCategory.TAX,
    "w-2": FileCategory.TAX,
    "1040": FileCategory.TAX,
    "medical": FileCategory.MEDICAL,
    "health": FileCategory.MEDICAL,
    "prescription": FileCategory.MEDICAL,
    "diagnosis": FileCategory.MEDICAL,
    "lab_result": FileCategory.MEDICAL,
    "invoice": FileCategory.INVOICE,
    "receipt": FileCategory.INVOICE,
    "bill": FileCategory.INVOICE,
    "payment": FileCategory.INVOICE,
    "screenshot": FileCategory.SCREENSHOT,
    "screen shot": FileCategory.SCREENSHOT,
    "snip": FileCategory.SCREENSHOT,
    "capture": FileCategory.SCREENSHOT,
    "school": FileCategory.SCHOOL,
    "homework": FileCategory.SCHOOL,
    "assignment": FileCategory.SCHOOL,
}


# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class ClassifiedFile(BaseModel):
    """Classification result for a single file."""

    path: str = Field(description="Absolute path to the file.")
    category: FileCategory = Field(description="Assigned category.")
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0.",
        ge=0.0,
        le=1.0,
    )
    reasoning: str = Field(
        description="Explanation of why this category was chosen.",
    )
    classification_method: Literal["metadata_only", "metadata_plus_preview"] = Field(
        default="metadata_only",
        description="Method used to classify this file.",
    )


class ClassificationOutput(BaseModel):
    """Output payload emitted by ClassificationNode."""

    classified_files: list[ClassifiedFile] = Field(
        default_factory=list,
        description="List of classification results for every file in the inventory.",
    )
    file_inventory: list[FileMetadata] = Field(
        default_factory=list,
        description="List of metadata objects for every discovered file (propagated downstream).",
    )
    folder_scope_policy: FolderScopePolicy = Field(
        description="The folder scope policy used for discovery, propagated downstream.",
    )
    safe_mode: bool = Field(
        default=False,
        description="Whether safe mode was active during classification.",
    )
    search_mode: bool = Field(
        default=False,
        description="Whether search mode was active during classification.",
    )
    reasoning: str = Field(
        description="High-level summary of the classification run.",
    )


class GeminiClassificationResult(BaseModel):
    """Internal model for Gemini structured responses."""

    category: str = Field(
        description="File category: resume, tax, medical, screenshot, invoice, school, source_code, media, misc."
    )
    confidence: float = Field(description="Confidence rating between 0.0 and 1.0.")
    reasoning: str = Field(description="Detailed reason for selection.")


# ---------------------------------------------------------------------------
# Safe content preview helper
# ---------------------------------------------------------------------------

_SAFE_PREVIEW_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".log",
    ".ini",
    ".cfg",
    ".conf",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
}


def _safe_preview(file: FileMetadata) -> str | None:
    """Return a short text preview if the file is safe to preview.

    Safety rules enforced:
    - File size must be less than 10 MB.
    - Extension must be in plain-text safe list.
    - Quick binary heuristic check (>20% of bytes > 127 is binary).
    - Read with open(file, "rb"), checked, truncated to 512 bytes, and decoded with errors="ignore".
    """
    if file.size >= 10 * 1024 * 1024 or file.size <= 0:
        return None

    ext = file.extension.lower()
    if ext not in _SAFE_PREVIEW_EXTENSIONS:
        return None

    try:
        path_to_open = resolve_real_path(file.path)
        with open(path_to_open, "rb") as f:
            raw_bytes = f.read(1024)

        if not raw_bytes:
            return None

        # Binary check: count bytes above 127
        high_bytes = sum(1 for b in raw_bytes if b > 127)
        if (high_bytes / len(raw_bytes)) > 0.20:
            return None

        truncated = raw_bytes[:512]
        return truncated.decode("utf-8", errors="ignore")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Post-processing confidence and safety filters
# ---------------------------------------------------------------------------


def _post_process_classification(
    file: FileMetadata,
    category: FileCategory,
    confidence: float,
    reasoning: str,
    has_preview: bool,
    preview_text: str | None,
) -> tuple[FileCategory, float, str]:
    """Applies strict safety limits and caps classification confidence."""
    basename = Path(file.path).name.lower()
    ext = file.extension.lower()
    is_masked = "sensitive_file_" in basename

    # Require two independent signals for sensitive categories
    if category in (FileCategory.TAX, FileCategory.MEDICAL):
        signals = 0

        # Signal 1: extension hints
        if category == FileCategory.TAX and ext in (".tax", ".w2", ".1099", ".1040"):
            signals += 1
        elif category == FileCategory.MEDICAL and ext in (".med", ".medical"):
            signals += 1

        # Signal 2: filename keyword (only if NOT masked)
        if not is_masked:
            keywords = (
                ["tax", "w2", "1099", "1040"]
                if category == FileCategory.TAX
                else ["medical", "health", "prescription", "diagnosis"]
            )
            if any(kw in basename for kw in keywords):
                signals += 1

        # Signal 3: preview keyword
        if has_preview and preview_text:
            preview_lower = preview_text.lower()
            keywords = (
                ["tax", "w2", "1099", "1040"]
                if category == FileCategory.TAX
                else ["medical", "health", "prescription", "doctor", "patient"]
            )
            if any(kw in preview_lower for kw in keywords):
                signals += 1

        if signals < 2:
            # Fall back to misc
            category = FileCategory.MISC
            confidence = min(confidence, 0.40)
            reasoning = (
                f"Classification reverted to misc. Sensitive category '{category}' "
                f"requires 2 independent signals, but only {signals} were found. "
                f"Original reasoning: {reasoning}"
            )

    # General confidence cap at 0.40 unless strong evidence exists
    has_strong_evidence = False

    if (
        category == FileCategory.SOURCE_CODE
        and ext in _EXTENSION_HINTS
        and _EXTENSION_HINTS[ext] == FileCategory.SOURCE_CODE
    ):
        has_strong_evidence = True
    elif (
        category == FileCategory.MEDIA
        and ext in _EXTENSION_HINTS
        and _EXTENSION_HINTS[ext] == FileCategory.MEDIA
    ):
        has_strong_evidence = True
    elif category == FileCategory.SCREENSHOT and "screenshot" in basename:
        has_strong_evidence = True

    if not has_strong_evidence and confidence > 0.40:
        confidence = 0.40
        reasoning += " (Confidence capped at 0.40 due to lack of strong evidence)"

    return category, confidence, reasoning


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def classification_node(node_input: FileDiscoveryOutput) -> Event:
    """ClassificationNode — classifies each file in the inventory using safety-biased Gemini."""
    safe_mode = node_input.safe_mode
    search_mode = node_input.search_mode
    policy = node_input.folder_scope_policy

    # Initialize Gemini client
    client = genai.Client()

    classified: list[ClassifiedFile] = []
    metadata_count = 0
    preview_count = 0

    for file in node_input.file_inventory:
        basename = Path(file.path).name
        ext = file.extension.lower()

        # Check preview eligibility
        allow_previews = getattr(policy, "allow_previews", True)
        can_preview = (
            not safe_mode
            and not search_mode
            and allow_previews
            and file.size < 10 * 1024 * 1024
        )

        preview = None
        method: Literal["metadata_only", "metadata_plus_preview"] = "metadata_only"

        if can_preview:
            preview = _safe_preview(file)
            if preview:
                method = "metadata_plus_preview"
                preview_count += 1
            else:
                metadata_count += 1
        else:
            metadata_count += 1

        # Build prompt for safety biased Gemini classification
        is_masked = "sensitive_file_" in basename.lower()
        masked_note = (
            "The filename is masked to protect user privacy. Do NOT attempt to guess "
            "or infer sensitive categories from the name. Rely only on extension, size, and timestamps."
            if is_masked
            else ""
        )

        prompt_parts = [
            "Classify the following file into exactly one of these categories: "
            "resume, tax, medical, screenshot, invoice, school, source_code, media, misc.",
            "",
            f"Filename: {basename}",
            f"Extension: {ext}",
            f"Size: {file.size} bytes",
            f"Last Modified: {file.last_modified}",
            masked_note,
        ]

        if preview:
            prompt_parts.append(f"\nFile Content Preview:\n{preview}")

        prompt_parts.extend(
            [
                "",
                "Safety Bias Instructions:",
                "1. If there is any ambiguity, uncertainty, or lack of strong evidence, "
                "you MUST classify as 'misc' with low confidence.",
                "2. Never guess sensitive categories (medical, tax) unless metadata or preview "
                "strongly demonstrates the classification.",
            ]
        )

        prompt = "\n".join(prompt_parts)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiClassificationResult,
                    temperature=0.1,
                ),
            )
            gemini_result = GeminiClassificationResult.model_validate_json(
                response.text
            )

            # Map raw string to FileCategory enum safely
            try:
                raw_cat = FileCategory(gemini_result.category.lower().strip())
            except ValueError:
                raw_cat = FileCategory.MISC

            cat, conf, reason = _post_process_classification(
                file=file,
                category=raw_cat,
                confidence=gemini_result.confidence,
                reasoning=gemini_result.reasoning,
                has_preview=(preview is not None),
                preview_text=preview,
            )

        except Exception as e:
            # Safe local fallback on API failure
            cat = FileCategory.MISC
            conf = 0.30
            reason = f"Gemini API failure, fell back to misc. Error: {e}"

        classified.append(
            ClassifiedFile(
                path=file.path,
                category=cat,
                confidence=conf,
                reasoning=reason,
                classification_method=method,
            )
        )

    # Compile high-level run summary
    reasoning = (
        f"Completed classification of {len(classified)} files. "
        f"Used metadata-only for {metadata_count} files, "
        f"and metadata-plus-preview for {preview_count} files. "
        f"No contents were uploaded."
    )

    output = ClassificationOutput(
        classified_files=classified,
        file_inventory=node_input.file_inventory,
        folder_scope_policy=policy,
        safe_mode=safe_mode,
        search_mode=search_mode,
        reasoning=reasoning,
    )

    return Event(output=output, actions=EventActions(route="dedupe"))
