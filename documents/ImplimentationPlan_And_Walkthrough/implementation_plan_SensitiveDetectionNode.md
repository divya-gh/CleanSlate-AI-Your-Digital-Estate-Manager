# SensitiveDetectionNode Implementation Plan

We will create the `SensitiveDetectionNode` in the ADK 2.0 graph workflow.

## Proposed Changes

### Nodes Module

#### [NEW] [sensitive_detection_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/sensitive_detection_node.py)
We will create a new ADK 2.0 node with:
- **Input schema**: Accepts `DuplicateDetectionOutput` (predecessor's output) containing `file_inventory`, `folder_scope_policy`, and `classified_files`.
- **Output schema (`SensitiveDetectionOutput`)**: Emits `sensitive_files[]` where each has:
  - `path`
  - `sensitivity_type`
  - `confidence`
  - `reasoning`
- **Heuristics / Safety**:
  - Checks each file against the `folder_scope_policy`.
  - For allowed files, reads safe previews (up to 512 bytes) or inspects metadata.
  - Calls Gemini API (`gemini-2.5-flash`) using structured output to determine:
    - If a file contains sensitive data (SSN, banking, tax, legal, medical, password, api_key, identity).
    - Returns `sensitivity_type`, `confidence`, and `reasoning`.

#### [MODIFY] [duplicate_detection_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/duplicate_detection_node.py)
- Propagate `classified_files`, `file_inventory`, and `folder_scope_policy` through `DuplicateDetectionOutput` so they are accessible by downstream nodes.

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Import and wire `sensitive_detection_node` after `duplicate_detection_node`.

## Verification Plan

### Automated Tests
- Create unit tests to verify that:
  - Sensitive files (containing mock SSNs, passwords, or named "tax_return.pdf") are correctly identified as sensitive.
  - Non-sensitive files are classified as not sensitive.
  - Scope policy is respected (hashing/scanning skipped for blocked paths).
  - Run linting and type checks.
