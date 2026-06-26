"""HITLApprovalNode — ADK 2.0 Graph Workflow Node.

Presents the generated action plan to the user, showing estimated space
recovery, reasoning, and individual actions. Interrupts the graph execution
to wait for explicit user approval (HITL).
"""

from __future__ import annotations

from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.events.request_input import RequestInput
from pydantic import BaseModel, Field

from app.nodes.classification_node import ClassifiedFile
from app.nodes.duplicate_detection_node import DuplicateGroup
from app.nodes.file_discovery_node import FileMetadata, FolderScopePolicy
from app.nodes.optimization_planner_node import CleanupAction, OptimizationPlannerOutput
from app.nodes.sensitive_detection_node import SensitiveFileEntry

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class HITLApprovalOutput(BaseModel):
    """Output payload emitted by HITLApprovalNode."""

    approved_actions: list[CleanupAction] = Field(
        default_factory=list,
        description="List of actions that the user explicitly approved and are safe to run.",
    )
    classified_files: list[ClassifiedFile] = Field(
        default_factory=list,
        description="List of classification results (propagated downstream).",
    )
    duplicate_groups: list[DuplicateGroup] = Field(
        default_factory=list,
        description="List of duplicate groups (propagated downstream).",
    )
    file_inventory: list[FileMetadata] = Field(
        default_factory=list,
        description="List of metadata objects for every discovered file (propagated downstream).",
    )
    folder_scope_policy: FolderScopePolicy = Field(
        description="The folder scope policy used for discovery, propagated downstream.",
    )
    sensitive_files: list[SensitiveFileEntry] = Field(
        default_factory=list,
        description="List of sensitive file entries (propagated downstream).",
    )
    dry_run: bool = Field(
        default=True,
        description="Dry run status propagated from the planner.",
    )
    rollback_enabled: bool = Field(
        default=True,
        description="Whether rollback is enabled, propagated downstream.",
    )
    reasoning: str = Field(
        description="High-level reasoning comments summarizing the HITL outcome."
    )


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node (HITL / Resumable Async Generator)
# ---------------------------------------------------------------------------


async def hitl_approval_node(
    ctx: Context,
    node_input: OptimizationPlannerOutput,
):
    """HITLApprovalNode — interrupts flow to get user confirmation for the plan.

    Presents the proposed action plan in a clean, human-readable format.
    Filters out any unsafe or sensitive actions from approved_actions even
    if the user approvals them.
    """
    plan = node_input.action_plan

    # Step 1: Interrupt if we don't have the user's input yet
    if not ctx.resume_inputs or "hitl_approved" not in ctx.resume_inputs:
        msg_parts = [
            "=== CleanSlate AI PC Assistant Optimization Action Plan ===",
            f"Total Estimated Storage Space Recovered: {plan.estimated_recovery} bytes",
            "Suggested Actions:",
        ]

        for i, action in enumerate(plan.actions):
            msg_parts.append(
                f"  [{i + 1}] {action.action_type.upper()}: {action.path}\n"
                f"      Reasoning: {action.reasoning}\n"
                f"      Safe to delete: {action.safe_to_delete} | Confidence: {action.confidence} | Space: {action.estimated_space_recovered} bytes"
            )

        msg_parts.append(
            "\nDo you approve executing this plan? Reply with 'yes' to proceed, or 'no' to cancel:"
        )

        message = "\n".join(msg_parts)

        yield RequestInput(
            interrupt_id="hitl_approved",
            message=message,
        )
        return

    # Step 2: Handle resumed state when input is available
    user_reply = ctx.resume_inputs["hitl_approved"]
    is_approved = str(user_reply).lower().strip() in {
        "yes",
        "y",
        "approve",
        "true",
    }

    approved: list[CleanupAction] = []
    if is_approved:
        # Enforce safety rules: filter out any unsafe actions or blocked targets
        for action in plan.actions:
            if action.action_type == "delete" and not action.safe_to_delete:
                # Extra guard: never delete unsafe/sensitive/blocked paths
                continue
            approved.append(action)

    route = "approved" if approved else "rejected"

    yield Event(
        output=HITLApprovalOutput(
            approved_actions=approved,
            classified_files=node_input.classified_files,
            duplicate_groups=node_input.duplicate_groups,
            file_inventory=node_input.file_inventory,
            folder_scope_policy=node_input.folder_scope_policy,
            sensitive_files=node_input.sensitive_files,
            dry_run=plan.dry_run,
            rollback_enabled=True,
            reasoning=(
                f"User approved the plan: {is_approved}. "
                f"Selected {len(approved)} safe action(s) for execution."
            ),
        ),
        actions=EventActions(route=route),
    )
