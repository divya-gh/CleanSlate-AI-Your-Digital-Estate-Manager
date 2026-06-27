# Implementation Plan — SensitiveDetectionNode Rebuild (Final, Refined)

This plan covers rebuilding the `SensitiveDetectionNode` to securely analyze file sensitivity, incorporating PDF text-only extraction, zero-signal API call bypass, and two-signal validation filters.

## User Review Required

> [!IMPORTANT]
> **Safety & Privacy Safeguards**:
> - **PDF and Binary Guard**:
>   - Previews are disabled in `safe_mode=True`.
>   - Never preview PDF binary streams directly. Extract text only (e.g. using `pypdf` or fallback text parser) and truncate to 512 chars.
>   - Disables previews for binary, media, executable, or archive files, and source code $> 50$ KB.
> - **Zero-Signal Bypass (Gemini optimization)**:
>   - If zero signals are present based on metadata (masked filename and generic extension), **skip calling Gemini entirely** and mark as `sensitive=False` with `sensitivity_type="none"`.
>   - If only one signal is present, force `sensitivity_type="none"` without calling Gemini (or override after call) to enforce the two-signal rule.
> - **Masked Filenames Safety**:
>   - Masked filenames segment (`sensitive_file_<hash>`) are treated as **zero-signal** for sensitive detection.
> - **Dedupe Integration**:
>   - Ensure `DuplicateDetectionNode` does not modify or corrupt masked filenames.
> - **Routing**:
>   - Returns `Event(output=..., actions=EventActions(route="plan"))` to route to `OptimizationPlannerNode`.

## Proposed Changes

### Duplicate Detection Component

#### [MODIFY] [duplicate_detection_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/duplicate_detection_node.py)
- Propagate `safe_mode: bool` and `search_mode: bool` on `DuplicateDetectionOutput`.
- Ensure it preserves the masked filenames as is.

### Sensitive Detection Component

#### [MODIFY] [sensitive_detection_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/sensitive_detection_node.py)
Rebuild node logic and schemas:
- **SensitiveFileEntry**: Include `sensitive: bool`.
- **SensitiveDetectionOutput**: Propagate `safe_mode: bool`, `search_mode: bool`, `sensitive_files: List[SensitiveFileEntry]`, and `non_sensitive_files: List[str]`.
- **Structured Gemini Result**: Includes `sensitivity_type`, `confidence`, `reasoning`, and optional `signals_detected`.
- **Safe Preview PDF / Binary Guards**: Check binary bytes (>20% > 127 heuristic), and for PDFs, extract text dynamically.
- **Routing**: Set `route="plan"` to connect to `OptimizationPlannerNode`.

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Wire routing:
  - `(sensitive_detection_node, {"plan": optimization_planner_node})`

---

## Verification Plan

### Automated Tests
- Update/create tests in `test_sensitive_detection.py` to cover:
  - Previews blocked in `safe_mode=True`.
  - Masked filename fallback handling (zero-signal).
  - Two-signal rule for sensitivity.
  - Confidence capping at 0.40.
  - Gracefully skipping blocked paths entirely.
  - `test_sensitive_detection_skips_preview_for_binary_pdf`
  - `test_sensitive_detection_zero_signal_skips_gemini`
