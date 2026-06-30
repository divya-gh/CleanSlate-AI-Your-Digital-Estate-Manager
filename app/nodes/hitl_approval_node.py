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
from app.security.audit_logger import log_action

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
        import json as _json
        import os as _os

        columns = ["Action", "Category", "File Path", "Space Saved", "Confidence"]
        rows = []
        for action in plan.actions:
            # Derive Category
            reason_lower = action.reasoning.lower()
            if "exact duplicate" in reason_lower or "duplicate" in reason_lower:
                category = "duplicate"
            elif any(k in reason_lower for k in ["sensitive", "ssn", "tax", "banking", "identity"]):
                category = "sensitive"
            else:
                ext = _os.path.splitext(action.path)[1].lower()
                if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]:
                    category = "image"
                elif ext in [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"]:
                    category = "document"
                elif ext in [".zip", ".tar", ".gz", ".rar", ".7z"]:
                    category = "archive"
                else:
                    category = "other"

            # Derive Action display
            if category == "sensitive":
                action_display = "SENSITIVE"
            elif "near duplicate" in reason_lower:
                action_display = "NEAR_DUPLICATE"
            elif category == "duplicate":
                action_display = "DELETE"
            else:
                action_display = action.action_type.upper()

            rows.append([
                action_display,
                category,
                action.path.replace("\\", "/"),
                str(action.estimated_space_recovered),
                f"{action.confidence:.2f}",
            ])

        table_json = _json.dumps({
            "__TABLE__": {
                "columns": columns,
                "rows": rows
            }
        })

        toggle_json = _json.dumps({
            "question": "Would you like me to execute these actions?",
            "options": [
                {"label": "Confirm Cleanup", "value": "yes"},
                {"label": "Cancel", "value": "no"}
            ]
        })

        # Combine both widgets into the message using their respective prefixes
        msg = f"__TABLE__\n{table_json}\n__TOGGLE_SELECT__\n{toggle_json}"

        yield RequestInput(
            interrupt_id="hitl_approved",
            message=msg,
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

    # Audit logging for HITL
    approved_cnt = len(approved)
    rejected_cnt = len(plan.actions) - approved_cnt
    log_action(
        node="HITLApprovalNode",
        action_type="plan",
        path=None,
        is_sensitive=False,
        hitl_status="approved" if is_approved else "rejected",
        result="success" if is_approved else "skipped",
        reason="User confirmation response processed."
        if is_approved
        else "User rejected optimization plan.",
        approved_actions_count=approved_cnt,
        rejected_actions_count=rejected_cnt,
        hitl_required=True,
    )

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
