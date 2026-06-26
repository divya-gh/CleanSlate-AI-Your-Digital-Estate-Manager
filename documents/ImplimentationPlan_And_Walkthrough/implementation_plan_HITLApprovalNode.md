# HITLApprovalNode Implementation Plan

We will create the `HITLApprovalNode` in the ADK 2.0 graph workflow.

## Proposed Changes

### Nodes Module

#### [NEW] [hitl_approval_node.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/nodes/hitl_approval_node.py)
We will create a new ADK 2.0 node with:
- **Input schema**: Accepts `OptimizationPlannerOutput` (predecessor's output) containing `action_plan` and `reasoning`.
- **Output schema (`HITLApprovalOutput`)**: Emits `approved_actions[]` where each has `path`, `action_type`, `reasoning`, `estimated_space_recovered`, `safe_to_delete`, and `confidence`.
- **Interrupt / Behavior**:
  - The node is an `async generator` function.
  - If `ctx.resume_inputs` does not contain `"hitl_approved"`, it yields a `RequestInput` with a human-readable list of all proposed actions, reasoning, and estimated storage recovery, asking the user to reply with "yes" or "no".
  - When resumed, if the user replied `"yes"`, it filters the proposed actions to include only safe actions (e.g., if an action is a `delete`, it must have `safe_to_delete=True`, and it must never target blocked paths or sensitive files) and emits them in `approved_actions`. If the user replies `"no"`, `approved_actions` is empty.

#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Import and wire `hitl_approval_node` after `optimization_planner_node`.

## Verification Plan

### Automated Tests
- Create unit tests verifying:
  - The node yields a `RequestInput` when running for the first time.
  - The node returns the list of approved safe actions when resumed with `"yes"`.
  - The node returns an empty list when resumed with `"no"`.
  - The node correctly filters out any unsafe actions even if the user approved them (double-safety guard).
  - Run linting and type checks.
