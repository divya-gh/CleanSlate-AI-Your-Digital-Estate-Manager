"""ClassificationNode — ADK 2.0 Graph Workflow Node.

Uses Gemini reasoning to classify each file from file_inventory into
semantic categories based on metadata and optional safe content previews.
Never reads full file contents; never uploads file data.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

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
    # Screenshots (common naming convention — extension alone isn't enough)
    # Screenshots are detected by filename pattern in _classify_by_metadata.
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
    "syllabus": FileCategory.SCHOOL,
    "transcript": FileCategory.SCHOOL,
    "lecture": FileCategory.SCHOOL,
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
    reasoning: str = Field(
        description="High-level summary of the classification run.",
    )


# ---------------------------------------------------------------------------
# Metadata-based classification (deterministic, no LLM needed)
# ---------------------------------------------------------------------------


def _classify_by_metadata(file: FileMetadata) -> ClassifiedFile:
    """Classify a file using only its metadata (path, extension, name).

    This provides a fast, deterministic baseline.  A future LLM-enhanced
    pass can refine these results.
    """
    basename = Path(file.path).stem.lower()
    ext = file.extension.lower()

    # 1. Check filename keyword matches (highest signal)
    for keyword, category in _FILENAME_KEYWORDS.items():
        if keyword in basename:
            return ClassifiedFile(
                path=file.path,
                category=category,
                confidence=0.85,
                reasoning=(
                    f"Filename '{Path(file.path).name}' contains keyword "
                    f"'{keyword}' → classified as {category.value}."
                ),
            )

    # 2. Check extension-based hints
    if ext in _EXTENSION_HINTS:
        category = _EXTENSION_HINTS[ext]
        return ClassifiedFile(
            path=file.path,
            category=category,
            confidence=0.80,
            reasoning=(
                f"Extension '{ext}' is a known indicator of {category.value} files."
            ),
        )

    # 3. Fallback to misc
    return ClassifiedFile(
        path=file.path,
        category=FileCategory.MISC,
        confidence=0.50,
        reasoning=(
            f"No strong metadata signal for '{Path(file.path).name}' "
            f"(ext='{ext}'). Classified as misc with low confidence."
        ),
    )


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
}

_MAX_PREVIEW_BYTES = 512  # Read at most 512 bytes — never full contents


def _safe_preview(file: FileMetadata) -> str | None:
    """Return a short text preview if the file extension is safe.

    Safety rules enforced:
    - Only reads files with known safe text extensions.
    - Never reads binary or sensitive file types.
    - Reads at most _MAX_PREVIEW_BYTES bytes.
    - Never uploads file contents anywhere.
    """
    ext = file.extension.lower()
    if ext not in _SAFE_PREVIEW_EXTENSIONS:
        return None

    try:
        with open(resolve_real_path(file.path), encoding="utf-8", errors="ignore") as f:
            return f.read(_MAX_PREVIEW_BYTES)
    except OSError:
        return None


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def classification_node(node_input: FileDiscoveryOutput) -> ClassificationOutput:
    """ClassificationNode — classifies each file in the inventory.

    This function node follows the ADK 2.0 Workflow convention:
    - Accepts a typed Pydantic input (FileDiscoveryOutput from predecessor).
    - Returns a typed Pydantic output (ClassificationOutput) for downstream.

    Classification strategy:
    1. Metadata-based heuristics (filename keywords, extension mapping).
    2. Optional safe content preview for ambiguous text files.
    3. Gemini LLM reasoning is reserved for a future enhancement pass.

    Safety guarantees:
    - Never reads file contents unless extension is in the safe-preview list.
    - Never uploads file contents.
    - Only uses metadata or safe previews (≤512 bytes of plain text).
    """
    classified: list[ClassifiedFile] = []
    refined_count = 0

    for file in node_input.file_inventory:
        result = _classify_by_metadata(file)

        # If confidence is low and a safe preview is available, try to refine
        if result.confidence < 0.70:
            preview = _safe_preview(file)
            if preview:
                # Use preview content keywords to attempt reclassification
                preview_lower = preview.lower()
                for keyword, category in _FILENAME_KEYWORDS.items():
                    if keyword in preview_lower:
                        result = ClassifiedFile(
                            path=file.path,
                            category=category,
                            confidence=0.75,
                            reasoning=(
                                f"Content preview contains keyword '{keyword}' "
                                f"→ reclassified as {category.value}."
                            ),
                        )
                        refined_count += 1
                        break

        classified.append(result)

    # Build high-level reasoning summary
    category_counts: dict[str, int] = {}
    for cf in classified:
        category_counts[cf.category.value] = (
            category_counts.get(cf.category.value, 0) + 1
        )

    distribution = ", ".join(
        f"{cat}: {count}" for cat, count in sorted(category_counts.items())
    )

    reasoning = (
        f"Classified {len(classified)} file(s) from the inventory. "
        f"Distribution: [{distribution}]. "
        f"{refined_count} file(s) were refined using safe content preview. "
        f"No file contents were uploaded."
    )

    return ClassificationOutput(
        classified_files=classified,
        file_inventory=node_input.file_inventory,
        folder_scope_policy=node_input.folder_scope_policy,
        reasoning=reasoning,
    )
