# Implementation Plan — ClassificationNode Rebuild

This plan covers rebuilding the `ClassificationNode` to consume `FileDiscoveryOutput` and refine file classification using safety-biased Gemini reasoning, conditional content previewing, and detailed metadata parsing.

## User Review Required

> [!IMPORTANT]
> **Safety & Privacy Safeguards**:
> - **Gemini Content Preview Isolation**: Gemini reasoning receives file metadata and, *only when explicitly allowed*, a short content preview (up to 512 bytes) of plain text files. **No file contents are uploaded to the cloud.**
> - **Strict Safe / Search Mode Restrictions**:
>   - In `safe_mode=True` or `search_mode=True`, content previews are completely disabled. Classification runs on metadata only.
> - **Sensitive Filename Masking Alignment**: If the filename is masked (`sensitive_file_<hash>`), ClassificationNode will classify based on this masked format and the file extension without attempting to unmask it.
> - **Safety Biased Classification**: The Gemini classification prompt is biased to output `misc` with low confidence if there is any ambiguity. It avoids guessing sensitive categories (e.g. `medical`, `tax`) without strong metadata/preview evidence.

## Open Questions

- *None. Requirements are fully specified.*

## Proposed Changes

### Classification Component

#### [MODIFY] [classification_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/classification_node.py)
Rebuild the node function to support the following:
- **Input Schema**: Expects `FileDiscoveryOutput`.
- **Output Schema**:
  - `classified_files: List[ClassifiedFile]`
    - Each `ClassifiedFile` contains: `path`, `category`, `confidence`, `reasoning`, `classification_method: Literal["metadata_only", "metadata_plus_preview"]`.
  - `file_inventory: List[FileMetadata]` (propagated)
  - `folder_scope_policy: FolderScopePolicy` (propagated)
  - `safe_mode: bool` (propagated)
  - `search_mode: bool` (propagated)
  - `reasoning: str`
- **Preview Constraints**:
  - Disable previews if `safe_mode=True` or `search_mode=True`.
  - Enable previews in interactive cleanup only if `folder_scope_policy.allow_previews` is `True` (we will check this attribute or fall back to `True`), file size is within limits (e.g. size > 0 and size < 10,000,000 bytes), and file extension is plain-text safe (`.txt`, `.md`, `.csv`, `.log`, `.ini`, `.cfg`, `.conf`, `.yaml`, `.yml`, `.json`, `.toml`).
- **Gemini Reasoning**:
  - Initialize the Gemini API client.
  - Implement a structured fallback parser that calls Gemini with the file's metadata (extension, name, path) and optional preview text.
  - Apply a system prompt instructing Gemini to categorize files into one of the 9 categories (`resume`, `tax`, `medical`, `screenshot`, `invoice`, `school`, `source_code`, `media`, `misc`).
  - Instruct the model to err on the side of `misc` (low confidence) when uncertain, and to never guess `medical` or `tax` unless metadata/preview explicitly demonstrates it.
- **Dynamic Routing**:
  - The node will return `ClassificationOutput` directly.

---

### Graph Transitions

- Ensure `ClassificationNode` connects to `DuplicateDetectionNode` in the workflow:
  `(file_discovery_node, classification_node)` and `(classification_node, duplicate_detection_node)` are configured statically in `app/agent.py`.

---

## Verification Plan

### Automated Tests
- Create/update unit tests in [test_classification.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_classification.py) to cover:
  - `test_classification_safe_mode_restricts_previews`
  - `test_classification_search_mode_restricts_previews`
  - `test_classification_interactive_previews_allowed`
  - `test_gemini_classification_heuristics`
  - `test_sensitive_masked_filename_handling`
  - `test_safe_mode_propagation`
