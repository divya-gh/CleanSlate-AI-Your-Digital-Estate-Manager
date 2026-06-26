# DuplicateDetectionNode Implementation Plan

We will create the `DuplicateDetectionNode` in the ADK 2.0 graph workflow.

## Proposed Changes

### Nodes Module

#### [NEW] [duplicate_detection_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/duplicate_detection_node.py)
We will create a new ADK 2.0 node with:
- **Input schema (`DuplicateDetectionInput`)**: Extends or inherits from the predecessor `ClassificationOutput` to receive `file_inventory` and `folder_scope_policy`.
- **Output schema (`DuplicateDetectionOutput`)**: Emits `duplicate_groups[]` where each group has `group_id`, `files[]` (path, size, hash, similarity_score), and `reasoning`.
- **Heuristics/Behavior**:
  - Hash computation: Uses SHA-256 for exact duplicates.
  - Folder Scope Policy: Before hashing, checks each file path against `folder_scope_policy` (must be explicitly allowed and never blocked).
  - Near duplicates heuristics: Groups files by same extension, similar sizes (e.g. within 5% or 10%), same parent folder, and similar filenames (e.g. using string similarity like SequenceMatcher or Levenshtein distance).
  - Reasoning: Included for each duplicate group.

#### [MODIFY] [classification_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/classification_node.py)
- Propagate `file_inventory` and `folder_scope_policy` through `ClassificationOutput` so they are accessible by downstream nodes.

#### [MODIFY] [file_discovery_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/file_discovery_node.py)
- Propagate `folder_scope_policy` in `FileDiscoveryOutput`.

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Import and wire `duplicate_detection_node` after `classification_node`.

## Verification Plan

### Automated Tests
- Create unit/integration tests to verify that:
  - Exact duplicates are detected correctly.
  - Near duplicates are detected using heuristics (filenames, size, parent dir, extension).
  - `folder_scope_policy` is respected.
  - Run `agents-cli lint` to ensure no errors.
