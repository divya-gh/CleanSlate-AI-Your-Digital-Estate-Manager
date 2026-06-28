"""WeeklyOrganizerNode — ADK 2.0 Graph Workflow Node.

Automated weekly cleanup node triggered via Pub/Sub. Checks if weekly automation
is enabled, sets safe-mode guards, and conditionally routes to FileDiscoveryNode.
"""

from __future__ import annotations

from datetime import datetime

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from pydantic import BaseModel, Field

from app.nodes.file_discovery_node import FileDiscoveryInput, FolderScopePolicy
from app.security.audit_logger import log_action

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class WeeklyOrganizerInput(BaseModel):
    """Input payload consumed by WeeklyOrganizerNode."""

    pubsub_event: dict = Field(
        default_factory=dict, description="The Pub/Sub event payload."
    )
    weekly_automation_enabled: bool = Field(
        default=True, description="Whether weekly automation is enabled."
    )
    folder_scope_policy: FolderScopePolicy = Field(
        description="The pre-approved folder scope policy."
    )
    dry_run: bool = Field(
        default=False, description="Whether to simulate actions in dry-run mode."
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the weekly event."
    )


class WeeklySummary(BaseModel):
    """Output payload emitted by WeeklyOrganizerNode when automation is disabled or finished."""

    automation_ran: bool = Field(description="Whether weekly automation ran.")
    actions_attempted: int = Field(description="Number of actions attempted.")
    actions_completed: int = Field(description="Number of actions completed.")
    skipped: int = Field(description="Number of skipped actions.")
    dry_run: bool = Field(description="Whether dry-run mode was active.")
    human_readable_report: str = Field(description="The human-readable weekly report.")
    sensitive_files_moved: int = Field(
        default=0, description="Number of sensitive files moved."
    )
    duplicates_moved: int = Field(
        default=0, description="Number of duplicate files moved."
    )
    errors: list[str] = Field(
        default_factory=list, description="List of errors encountered."
    )


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def weekly_organizer_node(node_input: WeeklyOrganizerInput) -> Event:
    """WeeklyOrganizerNode — conditionally runs weekly organization in safe mode."""
    try:
        if not node_input.weekly_automation_enabled:
            log_action(
                node="WeeklyOrganizerNode",
                action_type="plan",
                path=None,
                is_sensitive=False,
                hitl_status="not_required",
                result="skipped",
                reason="Weekly automation is disabled.",
            )
            summary = WeeklySummary(
                automation_ran=False,
                actions_attempted=0,
                actions_completed=0,
                skipped=0,
                dry_run=node_input.dry_run,
                human_readable_report="Weekly automation disabled. No actions performed.",
                sensitive_files_moved=0,
                duplicates_moved=0,
                errors=[],
            )
            return Event(output=summary, actions=EventActions(route="disabled"))

        # Configure the pre-approved policy to safe mode
        policy = node_input.folder_scope_policy.model_copy(deep=True)
        policy.safe_mode = True
        policy.dry_run = node_input.dry_run
        policy.allow_deletes = False
        policy.allow_compress = False
        policy.allow_archives = True
        policy.allow_moves = True

        log_action(
            node="WeeklyOrganizerNode",
            action_type="plan",
            path=None,
            is_sensitive=False,
            hitl_status="not_required",
            result="success",
            reason="Weekly organizer triggered. Safe mode active: deletes and compressions are disabled.",
        )

        discovery_input = FileDiscoveryInput(
            folder_scope_policy=policy,
            search_query=None,
        )

        return Event(output=discovery_input, actions=EventActions(route="run"))

    except Exception as e:
        log_action(
            node="WeeklyOrganizerNode",
            action_type="plan",
            path=None,
            is_sensitive=False,
            hitl_status="not_required",
            result="failure",
            reason=f"Weekly automation error: {e}",
        )
        summary = WeeklySummary(
            automation_ran=False,
            actions_attempted=0,
            actions_completed=0,
            skipped=0,
            dry_run=node_input.dry_run,
            human_readable_report=f"Weekly automation error: {e}",
            sensitive_files_moved=0,
            duplicates_moved=0,
            errors=[str(e)],
        )
        return Event(output=summary, actions=EventActions(route="error"))
