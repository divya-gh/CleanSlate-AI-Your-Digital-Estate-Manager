# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import google.auth
from pydantic import BaseModel
from google.adk.workflow import Workflow, START
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig

from app.nodes.file_discovery_node import (
    FileDiscoveryInput,
    FileDiscoveryOutput,
    FolderScopePolicy,
    file_discovery_node,
)
from app.nodes.classification_node import classification_node
from app.nodes.duplicate_detection_node import duplicate_detection_node
from app.nodes.sensitive_detection_node import sensitive_detection_node
from app.nodes.optimization_planner_node import optimization_planner_node
from app.nodes.hitl_approval_node import hitl_approval_node
from app.nodes.execution_node import execution_node
from app.nodes.summary_node import summary_node
from app.nodes.rollback_node import rollback_node
from app.nodes.weekly_organizer_node import (
    weekly_organizer_node,
    WeeklyOrganizerInput,
    WeeklySummary,
)
from app.nodes.my_pc_assistant_node import (
    MyPCAssistantInput,
    my_pc_assistant_node,
)

# Set Google Cloud environment variables
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


from pydantic import BaseModel, model_validator
from typing import Any


class UserRequest(BaseModel):
    request_text: str

    @model_validator(mode="before")
    @classmethod
    def _validate_content(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "parts" in data:
                parts = data["parts"]
                text = ""
                if isinstance(parts, list):
                    for part in parts:
                        if isinstance(part, dict) and "text" in part:
                            text += part["text"]
                        elif hasattr(part, "text") and part.text:
                            text += part.text
                return {"request_text": text}
            if "request_text" in data:
                return data
        if hasattr(data, "parts") and data.parts:
            text = ""
            for part in data.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text
            return {"request_text": text}
        if isinstance(data, str):
            return {"request_text": data}
        return data


def process_request(node_input: UserRequest) -> str:
    """Pre-processes the user request to prepare it for validation."""
    return f"Clean Slate Action Request: {node_input.request_text}"


async def verify_request(ctx: Context, node_input: str):
    """Asks the user for approval before executing the request."""
    # Check if we have the user response for this interrupt
    if not ctx.resume_inputs or "approved" not in ctx.resume_inputs:
        yield RequestInput(
            interrupt_id="approved",
            message=f"Do you approve this action? Reply with 'yes' to proceed: '{node_input}'",
        )
        return

    # Process user response
    user_reply = ctx.resume_inputs["approved"]
    is_approved = str(user_reply).lower().strip() == "yes"

    yield Event(
        output={"approved": is_approved, "request": node_input},
        actions=EventActions(state_delta={"is_approved": is_approved}),
    )


def finalize_request(node_input: dict) -> str:
    """Finalizes the request status and returns the final outcome."""
    approved = node_input.get("approved", False)
    request = node_input.get("request", "")
    if approved:
        return f"Outcome: SUCCESS. Executed action: '{request}'"
    else:
        return f"Outcome: REJECTED. Canceled action: '{request}'"


# ---------------------------------------------------------------------------
# FolderScopeNode — placeholder (to be implemented per ADK Agent Graph SPEC)
# Outputs a FileDiscoveryInput that feeds into FileDiscoveryNode.
# ---------------------------------------------------------------------------
def folder_scope_node(node_input: Any) -> FileDiscoveryInput:
    """Placeholder FolderScopeNode — returns a default scope policy.

    This node will be replaced with the full implementation when the
    FolderScopeNode SPEC is provided.  For now it emits a safe default
    so that FileDiscoveryNode can be tested in isolation.
    """
    return FileDiscoveryInput(
        folder_scope_policy=FolderScopePolicy(
            allowed_paths=[os.getcwd()],
            blocked_paths=[],
        ),
        search_query=None,
    )


# ---------------------------------------------------------------------------
# Define the workflow graph
# ---------------------------------------------------------------------------
root_agent = Workflow(
    name="cleanslate_pc_workflow",
    edges=[
        # — Interactive Assistant Entry Point & Routing —
        (START, my_pc_assistant_node),
        (my_pc_assistant_node, {"cleanup": folder_scope_node}),
        (my_pc_assistant_node, {"search": file_discovery_node}),
        (my_pc_assistant_node, {"explain": summary_node}),
        # — File discovery → Classification pipeline —
        (folder_scope_node, file_discovery_node),
        (file_discovery_node, classification_node),
        (classification_node, duplicate_detection_node),
        (duplicate_detection_node, sensitive_detection_node),
        (sensitive_detection_node, optimization_planner_node),
        (optimization_planner_node, hitl_approval_node),
        (hitl_approval_node, {"approved": execution_node}),
        # — Execution & Conditional Rollback Routing —
        (execution_node, summary_node),
        (execution_node, {"rollback": rollback_node}),
        (rollback_node, summary_node),
        # In safe mode, optimization_planner_node skips HITL and executes directly
        (optimization_planner_node, {"safe_execute": execution_node}),
    ],
    input_schema=MyPCAssistantInput,
    rerun_on_resume=True,
)

# — Weekly Organizer Workflow (Isolated from the main cleanup pipeline) —
weekly_organizer_agent = Workflow(
    name="weekly_organizer_workflow",
    edges=[
        (START, weekly_organizer_node),
        (weekly_organizer_node, {"run": file_discovery_node}),
        (file_discovery_node, classification_node),
        (classification_node, duplicate_detection_node),
        (duplicate_detection_node, sensitive_detection_node),
        (sensitive_detection_node, optimization_planner_node),
        (optimization_planner_node, {"safe_execute": execution_node}),
        (execution_node, summary_node),
    ],
    input_schema=WeeklyOrganizerInput,
    rerun_on_resume=True,
)

# App wrapping the workflow agent with ResumabilityConfig enabled
app = App(
    root_agent=root_agent,
    name="app",
    resumability_config=ResumabilityConfig(is_resumable=True),
)
