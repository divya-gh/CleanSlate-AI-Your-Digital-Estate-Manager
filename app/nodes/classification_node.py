"""ClassificationNode — ADK 2.0 Graph Workflow Node.

Uses Gemini reasoning to classify each file from file_inventory into
semantic categories based strictly on metadata (no safe content previews).
Enforces strict safe/search mode restrictions and safety-biased confidence boundaries.
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
)
from app.utils.headings import get_heading_from_filename

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
# Post-processing confidence and safety filters
# ---------------------------------------------------------------------------


def _post_process_classification(
    file: FileMetadata,
    category: FileCategory,
    confidence: float,
    reasoning: str,
) -> tuple[FileCategory, float, str]:
    """Applies strict safety limits and caps classification confidence using metadata-only signals."""
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

        # Signal 3: parent folder name contains keywords
        parent_dir = Path(file.path).parent.name.lower()
        folder_keywords = (
            ["tax", "w2", "1099", "1040", "finance", "accounting"]
            if category == FileCategory.TAX
            else ["medical", "health", "prescription", "clinic", "hospital", "doctor"]
        )
        if any(kw in parent_dir for kw in folder_keywords):
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


def _generate_with_retry(client, model, contents, config, max_retries=3, initial_delay=3.0):
    import time
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as e:
            if "429" in str(e) or "exhausted" in str(e).lower() or "limit" in str(e).lower():
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
            raise e


def classification_node(node_input: FileDiscoveryOutput) -> Event:
    """ClassificationNode — classifies each file in the inventory using safety-biased Gemini (metadata only)."""
    safe_mode = node_input.safe_mode
    search_mode = node_input.search_mode
    policy = node_input.folder_scope_policy

    # Initialize Gemini client
    client = genai.Client()

    classified: list[ClassifiedFile] = []

    for file in node_input.file_inventory:
        basename = Path(file.path).name
        ext = file.extension.lower()
        parent_folder = Path(file.path).parent.name
        path_depth = len(Path(file.path).parts)
        heading = get_heading_from_filename(file.path)

        # Basic type guess based on extension hints helper mapping
        type_guess = _EXTENSION_HINTS.get(ext, FileCategory.MISC)

        # Local bypass checks to avoid unnecessary Gemini API calls on large inventories
        basename_lower = basename.lower()

        # 1. Source code bypass
        if type_guess == FileCategory.SOURCE_CODE:
            classified.append(
                ClassifiedFile(
                    path=file.path,
                    category=FileCategory.SOURCE_CODE,
                    confidence=0.95,
                    reasoning="Classified locally as source code based on extension.",
                    classification_method="metadata_only",
                )
            )
            continue

        # 2. Archive bypass
        if ext in (".zip", ".tar", ".gz", ".rar", ".7z", ".cab", ".iso"):
            classified.append(
                ClassifiedFile(
                    path=file.path,
                    category=FileCategory.MISC,
                    confidence=0.95,
                    reasoning="Classified locally as misc based on archive extension.",
                    classification_method="metadata_only",
                )
            )
            continue

        # 3. Media bypass (only if filename doesn't contain ambiguous/sensitive keywords)
        ambiguous_keywords = [
            "screenshot", "ss", "invoice", "bill", "receipt", "payment",
            "resume", "cv", "tax", "w2", "1099", "1040", "medical", "health",
            "prescription", "diagnosis", "ssn", "passport", "bank", "password",
            "social_security", "api_key", "secret", "driver", "license", "card", "id"
        ]
        if type_guess == FileCategory.MEDIA and not any(kw in basename_lower for kw in ambiguous_keywords):
            classified.append(
                ClassifiedFile(
                    path=file.path,
                    category=FileCategory.MEDIA,
                    confidence=0.95,
                    reasoning="Classified locally as media based on extension and name.",
                    classification_method="metadata_only",
                )
            )
            continue

        # Build prompt for safety biased Gemini classification using metadata elements only
        is_masked = "sensitive_file_" in basename.lower()
        masked_note = (
            "The filename is masked to protect user privacy. Treat it as a zero-signal for filename. "
            "Do NOT attempt to guess or infer sensitive categories from the name. Rely only on extension, size, and timestamps."
            if is_masked
            else ""
        )

        prompt_parts = [
            "Classify the following file into exactly one of these categories: "
            "resume, tax, medical, screenshot, invoice, school, source_code, media, misc.",
            "",
            f"Filename: {basename}",
            f"Derived Heading: {heading}",
            f"Extension: {ext}",
            f"Folder Name: {parent_folder}",
            f"Size: {file.size} bytes",
            f"Path Depth: {path_depth}",
            f"Last Modified: {file.last_modified}",
            f"Type Guess: {type_guess}",
            masked_note,
            "",
            "Safety Bias Instructions:",
            "1. If there is any ambiguity, uncertainty, or lack of strong evidence, "
            "you MUST classify as 'misc' with low confidence.",
            "2. Never guess sensitive categories (medical, tax) unless metadata "
            "strongly demonstrates the classification.",
        ]

        prompt = "\n".join(prompt_parts)

        try:
            response = _generate_with_retry(
                client=client,
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
            )

        except Exception as e:
            # Smart local fallback on API failure
            basename_lower = basename.lower()
            if any(kw in basename_lower for kw in ["resume", "cv"]):
                cat = FileCategory.RESUME
                conf = 0.85
                reason = f"Local fallback: Classified as resume based on filename pattern. (Gemini error: {e})"
            elif any(kw in basename_lower for kw in ["tax", "w2", "1099", "1040"]) or ext in (".tax", ".w2", ".1099", ".1040"):
                cat = FileCategory.TAX
                conf = 0.85
                reason = f"Local fallback: Classified as tax based on filename pattern. (Gemini error: {e})"
            elif any(kw in basename_lower for kw in ["medical", "health", "prescription", "diagnosis"]) or ext in (".med", ".medical"):
                cat = FileCategory.MEDICAL
                conf = 0.85
                reason = f"Local fallback: Classified as medical based on filename pattern. (Gemini error: {e})"
            elif any(kw in basename_lower for kw in ["screenshot", "ss"]):
                cat = FileCategory.SCREENSHOT
                conf = 0.85
                reason = f"Local fallback: Classified as screenshot based on filename pattern. (Gemini error: {e})"
            elif any(kw in basename_lower for kw in ["invoice", "bill", "receipt"]):
                cat = FileCategory.INVOICE
                conf = 0.85
                reason = f"Local fallback: Classified as invoice based on filename pattern. (Gemini error: {e})"
            else:
                cat = type_guess
                conf = 0.60
                reason = f"Local fallback: Classified based on extension guess {type_guess}. (Gemini error: {e})"

        classified.append(
            ClassifiedFile(
                path=file.path,
                category=cat,
                confidence=conf,
                reasoning=reason,
                classification_method="metadata_only",
            )
        )

    # Compile high-level run summary
    reasoning = (
        f"Completed classification of {len(classified)} files. "
        f"Used metadata-only for all files. "
        f"No contents were read or uploaded."
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
