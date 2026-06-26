# OptimizationPlannerNode Implementation Plan

We will create the `OptimizationPlannerNode` in the ADK 2.0 graph workflow.

## Proposed Changes

### Nodes Module

#### [NEW] [optimization_planner_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/optimization_planner_node.py)
We will create a new ADK 2.0 node with:
- **Input schema**: Accepts `SensitiveDetectionOutput` (predecessor's output) containing `sensitive_files`, `classified_files`, `file_inventory`, and `folder_scope_policy`.
- **Output schema (`OptimizationPlannerOutput`)**: Emits `action_plan` containing:
  - `actions`: List of actions where each contains `path`, `action_type` (move, archive, compress, delete), `reasoning`, and `estimated_space_recovered`.
  - `reasoning`: List of strings summarizing high-level plan details.
  - `estimated_recovery`: Total estimated storage recovery in bytes.
- **Safety / Behavior**:
  - Excludes any file marked as sensitive (`sensitive: True` in `sensitive_files`).
  - Excludes blocked paths and paths outside allowed paths using `folder_scope_policy`.
  - Identifies duplicate files (from `duplicate_groups`) and suggests deleting duplicates (leaving only one copy).
  - Suggests compression or archiving for less-accessed files (e.g. older than 30 days based on metadata or categories like media/source_code).
  - Computes total estimated storage recovery.

#### [MODIFY] [sensitive_detection_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/sensitive_detection_node.py)
- Propagate `classified_files`, `duplicate_groups`, `file_inventory`, and `folder_scope_policy` through `SensitiveDetectionOutput` so they are accessible by downstream nodes.

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Import and wire `optimization_planner_node` after `sensitive_detection_node`.

## Verification Plan

### Automated Tests
- Create unit tests verifying:
  - Deletion suggestions are never made for sensitive files.
  - Deletion suggestions are made for non-sensitive duplicates.
  - Compression/archiving suggestions are generated for other non-sensitive eligible files.
  - Blocked paths are completely excluded.
  - Run linting and type checks.
