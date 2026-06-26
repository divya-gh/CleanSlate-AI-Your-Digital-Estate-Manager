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

# Set Google Cloud environment variables
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


class UserRequest(BaseModel):
    request_text: str


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
def folder_scope_node(node_input: str) -> FileDiscoveryInput:
    """Placeholder FolderScopeNode — returns a default scope policy.

    This node will be replaced with the full implementation when the
    FolderScopeNode SPEC is provided.  For now it emits a safe default
    so that FileDiscoveryNode can be tested in isolation.
    """
    return FileDiscoveryInput(
        folder_scope_policy=FolderScopePolicy(
            allowed_paths=[],
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
        # — Core request pipeline —
        (START, process_request),
        (process_request, verify_request),
        (verify_request, finalize_request),
        # — File discovery → Classification pipeline (no downstream yet) —
        (finalize_request, folder_scope_node),
        (folder_scope_node, file_discovery_node),
        (file_discovery_node, classification_node),
        (classification_node, duplicate_detection_node),
    ],
    input_schema=UserRequest,
    rerun_on_resume=True,
)

# App wrapping the workflow agent with ResumabilityConfig enabled
app = App(
    root_agent=root_agent,
    name="app",
    resumability_config=ResumabilityConfig(is_resumable=True),
)
