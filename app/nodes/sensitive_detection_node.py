"""SensitiveDetectionNode — ADK 2.0 Graph Workflow Node.

Identifies sensitive files (containing SSNs, banking, tax, legal, medical,
password, identity documents, or API keys) strictly using metadata elements (no content previews).
Uses Gemini model classification on metadata and enforces strict safety-biased boundaries.
"""

from __future__ import annotations

import os
from pathlib import Path

from google import genai
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from app.nodes.classification_node import ClassifiedFile, FileCategory
from app.nodes.duplicate_detection_node import DuplicateDetectionOutput, DuplicateGroup
from app.nodes.file_discovery_node import (
    FileMetadata,
    FolderScopePolicy,
)
from app.utils.headings import get_heading_from_filename

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class SensitiveFileEntry(BaseModel):
    """Result details for a single checked file."""

    path: str = Field(description="Absolute path to the file.")
    sensitive: bool = Field(
        default=False,
        description="Whether the file was determined to contain sensitive data.",
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
    non_sensitive_files: list[str] = Field(
        default_factory=list,
        description="List of non-sensitive file paths.",
    )
    classified_files: list[ClassifiedFile] = Field(
        default_factory=list,
        description="List of classification results for every file (propagated downstream).",
    )
    duplicate_groups: list[DuplicateGroup] = Field(
        default_factory=list,
        description="List of duplicate groups identified (propagated downstream).",
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
        description="Whether safe mode was active during sensitive file detection.",
    )
    search_mode: bool = Field(
        default=False,
        description="Whether search mode was active during sensitive file detection.",
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
    signals_detected: list[str] | None = Field(
        default=None,
        description="Optional list of signals detected during analysis.",
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


# ---------------------------------------------------------------------------
# Signal Detection & Safety-biased filters
# ---------------------------------------------------------------------------

_SENSITIVE_KEYWORDS = [
    "ssn",
    "passport",
    "bank",
    "medical",
    "tax",
    "password",
    "social_security",
    "api_key",
    "secret",
    "resume",
    "driver",
    "license",
    "card",
]
_SENSITIVE_EXTENSIONS = {".tax", ".w2", ".1040", ".med", ".medical", ".key", ".pem"}


def _has_high_risk_keyword(name: str) -> bool:
    name_lower = name.lower()
    # Check safe substrings
    if any(kw in name_lower for kw in _SENSITIVE_KEYWORDS):
        return True
    # Standalone matches for short abbreviations
    import re
    if re.search(r'\b(id|dl)\b', name_lower):
        return True
    return False


def _detect_signals(
    file: FileMetadata,
    cf_category: str | None,
) -> list[str]:
    """Identifies sensitive indicators across metadata elements only."""
    signals = []
    basename = Path(file.path).name.lower()
    ext = file.extension.lower()

    # 1. Filename keyword (only if NOT masked)
    is_masked = "sensitive_file_" in basename
    if not is_masked:
        if any(kw in basename for kw in _SENSITIVE_KEYWORDS):
            signals.append("filename_keyword")

    # 2. Extension hint
    if ext in _SENSITIVE_EXTENSIONS:
        signals.append("sensitive_extension")

    # 3. Predecessor classification category
    if cf_category in (FileCategory.TAX, FileCategory.MEDICAL, FileCategory.RESUME):
        signals.append("classification_category")

    # 4. Folder keyword (parent directory name contains keywords)
    parent_dir = Path(file.path).parent.name.lower()
    if any(kw in parent_dir for kw in _SENSITIVE_KEYWORDS):
        signals.append("folder_keyword")

    return signals


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


def sensitive_detection_node(
    node_input: DuplicateDetectionOutput,
) -> Event:
    """SensitiveDetectionNode — classifies sensitivity using strictly metadata and Gemini."""
    inventory = node_input.file_inventory
    policy = node_input.folder_scope_policy
    safe_mode = node_input.safe_mode
    search_mode = node_input.search_mode
    classified_lookup = {cf.path: cf for cf in node_input.classified_files}

    # Initialize Gemini client
    client = genai.Client()


    checked: list[SensitiveFileEntry] = []
    non_sensitive_paths: list[str] = []
    skipped_count = 0

    for file in inventory:
        # Respect policy strictly — never scan or preview blocked paths
        if not _is_path_allowed(file.path, policy):
            skipped_count += 1
            checked.append(
                SensitiveFileEntry(
                    path=file.path,
                    sensitive=False,
                    sensitivity_type="none",
                    confidence=1.0,
                    reasoning="File skipped because it resides under a blocked or unallowed path.",
                )
            )
            non_sensitive_paths.append(file.path)
            continue

        # Fetch predecessor category
        cf = classified_lookup.get(file.path)
        category = cf.category if cf else None

        # Detect safety signals (metadata only)
        signals = _detect_signals(file, category)

        # Check if the filename contains high-risk keywords to bypass optimization limits
        basename_lower = Path(file.path).name.lower()
        has_high_risk_keyword = _has_high_risk_keyword(basename_lower)

        # Optimization: Zero signals or single signal skips Gemini (exempt high-risk keywords)
        if len(signals) < 2 and not has_high_risk_keyword:
            checked.append(
                SensitiveFileEntry(
                    path=file.path,
                    sensitive=False,
                    sensitivity_type="none",
                    confidence=1.0,
                    reasoning=(
                        f"Skipped Gemini: Requires at least 2 independent signals "
                        f"for sensitivity. Found only {len(signals)} signal(s)."
                    ),
                )
            )
            non_sensitive_paths.append(file.path)
            continue


        # Build prompt for safety biased Gemini using metadata only
        basename = Path(file.path).name
        parent_folder = Path(file.path).parent.name
        heading = get_heading_from_filename(file.path)
        is_masked = "sensitive_file_" in basename.lower()
        masked_note = (
            "The filename is masked to protect user privacy. Treat it as a zero-signal for filename. "
            "Do NOT attempt to guess or infer sensitive categories from the name. Rely only on extension and category."
            if is_masked
            else ""
        )

        prompt_parts = [
            "Analyze the following file for sensitive personal, financial, or access data.",
            f"Filename: {basename}",
            f"Derived Heading: {heading}",
            f"Extension: {file.extension}",
            f"Folder Name: {parent_folder}",
            f"Size: {file.size} bytes",
            f"Predicted Category: {category}",
            masked_note,
            "",
            "Safety Bias Instructions:",
            "1. If uncertain or there is lack of clear sensitive keywords/patterns, "
            "classify as 'none' with low confidence.",
            "2. Never guess sensitive categories (SSN, banking, medical, tax, legal, identity) "
            "unless metadata strongly demonstrates it.",
        ]

        prompt = "\n".join(prompt_parts)

        try:
            response = _generate_with_retry(
                client=client,
                model="gemini-2.5-flash",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiSensitivityResult,
                    temperature=0.1,
                ),
            )
            result = GeminiSensitivityResult.model_validate_json(response.text)

            file_is_sensitive = result.sensitive
            sens_type = result.sensitivity_type
            conf = result.confidence
            reason = result.reasoning

            # Force sensitivity if filename contains high-risk keywords
            if has_high_risk_keyword:
                file_is_sensitive = True
                conf = max(conf, 0.95)
                if sens_type == "none" or not sens_type:
                    sens_type = "identity"
                    import re as _re
                    for kw, st in [
                        ("ssn", "SSN"),
                        ("passport", "identity"),
                        ("bank", "banking"),
                        ("medical", "medical"),
                        ("tax", "tax"),
                        ("password", "password"),
                        ("social_security", "SSN"),
                        ("api_key", "api_key"),
                        ("secret", "api_key"),
                        ("resume", "identity"),
                        ("driver", "identity"),
                        ("license", "identity"),
                        ("card", "identity"),
                        ("id", "identity"),
                        ("dl", "identity"),
                    ]:
                        if kw in basename_lower or (kw in ("id", "dl") and _re.search(rf'\b{kw}\b', basename_lower)):
                            sens_type = st
                            break
                reason = f"Enforced sensitive classification based on high-risk filename keyword. Original: {reason}"

            # Extra check: double-signal rule enforce (exempt high-risk keywords)
            if file_is_sensitive and len(signals) < 2 and not has_high_risk_keyword:
                file_is_sensitive = False
                sens_type = "none"
                conf = min(conf, 0.40)
                reason = (
                    f"Sensitive flag overridden to none. Two independent signals required "
                    f"but only {len(signals)} were detected."
                )

            # Cap confidence at 0.40 if two signals are not present (exempt high-risk keywords)
            if len(signals) < 2 and not has_high_risk_keyword and conf > 0.40:
                conf = 0.40

            if file_is_sensitive:
                checked.append(
                    SensitiveFileEntry(
                        path=file.path,
                        sensitive=file_is_sensitive,
                        sensitivity_type=sens_type,
                        confidence=conf,
                        reasoning=reason,
                    )
                )
            else:
                checked.append(
                    SensitiveFileEntry(
                        path=file.path,
                        sensitive=False,
                        sensitivity_type="none",
                        confidence=conf,
                        reasoning=reason,
                    )
                )
                non_sensitive_paths.append(file.path)

        except Exception as e:
            if has_high_risk_keyword:
                # Determine sensitive category based on keywords
                basename_lower = Path(file.path).name.lower()
                sens_type = "none"
                for kw, st in [
                    ("ssn", "SSN"),
                    ("passport", "identity"),
                    ("bank", "banking"),
                    ("medical", "medical"),
                    ("tax", "tax"),
                    ("password", "password"),
                    ("social_security", "SSN"),
                    ("api_key", "api_key"),
                    ("secret", "api_key"),
                    ("resume", "identity"),
                    ("driver", "identity"),
                    ("license", "identity"),
                    ("card", "identity"),
                    ("id", "identity"),
                ]:
                    if kw in basename_lower:
                        sens_type = st
                        break
                
                checked.append(
                    SensitiveFileEntry(
                        path=file.path,
                        sensitive=True,
                        sensitivity_type=sens_type,
                        confidence=0.90,
                        reasoning=f"Local fallback: Detected high-risk keyword in file name. (Gemini error: {e})",
                    )
                )
            else:
                checked.append(
                    SensitiveFileEntry(
                        path=file.path,
                        sensitive=False,
                        sensitivity_type="none",
                        confidence=0.5,
                        reasoning=f"Failed to analyze sensitivity using Gemini: {e}",
                    )
                )
                non_sensitive_paths.append(file.path)

    sensitive_count = sum(1 for entry in checked if entry.sensitive)
    reasoning = (
        f"Analyzed {len(inventory) - skipped_count} allowed file(s). "
        f"Skipped {skipped_count} blocked/unallowed file(s). "
        f"Identified {sensitive_count} sensitive file(s). "
        f"Never read or uploaded file contents."
    )

    output = SensitiveDetectionOutput(
        sensitive_files=checked,
        non_sensitive_files=non_sensitive_paths,
        classified_files=node_input.classified_files,
        duplicate_groups=node_input.duplicate_groups,
        file_inventory=inventory,
        folder_scope_policy=policy,
        safe_mode=safe_mode,
        search_mode=search_mode,
        reasoning=reasoning,
    )

    return Event(output=output, actions=EventActions(route="plan"))
