import os
from unittest.mock import MagicMock

import pytest
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput

from app.nodes import (
    FolderScopeInput,
    FolderScopeOutput,
    file_discovery_node,
    folder_scope_node,
)
from app.nodes.file_discovery_node import FolderScopePolicy
from app.nodes.folder_scope_node import (
    _parse_paths,
    _validate_single_path,
)


@pytest.mark.anyio
async def test_folder_scope_cleanup_intent_false() -> None:
    ctx = MagicMock()
    ctx.resume_inputs = {}
    node_input = FolderScopeInput(cleanup_intent=False)

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    assert event.actions.route is None
    assert event.output.folder_scope_policy is None
    assert "Cleanup intent not detected" in event.output.message


@pytest.mark.anyio
async def test_folder_scope_prompts_for_allowed_paths() -> None:
    ctx = MagicMock()
    ctx.resume_inputs = {}
    node_input = FolderScopeInput(cleanup_intent=True)

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, RequestInput)
    assert event.interrupt_id == "allowed_paths"
    assert "allow the assistant to scan" in event.message


@pytest.mark.anyio
async def test_folder_scope_prompts_for_blocked_paths() -> None:
    ctx = MagicMock()
    ctx.resume_inputs = {"allowed_paths": "C:\\Users\\User\\Documents"}
    node_input = FolderScopeInput(cleanup_intent=True)

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, RequestInput)
    assert event.interrupt_id == "blocked_paths"
    assert "must never touch" in event.message


@pytest.mark.anyio
async def test_folder_scope_validation_error_and_field_clearing() -> None:
    # allowed_paths contains a system path, which is invalid
    ctx = MagicMock()
    ctx.resume_inputs = {
        "allowed_paths": "C:\\Windows",
        "blocked_paths": "C:\\Users\\User\\Downloads",
    }
    node_input = FolderScopeInput(cleanup_intent=True)

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    assert event.actions.route is None
    assert event.output.folder_scope_policy is None
    assert len(event.output.validation_errors) > 0
    # Checks that allowed_paths got popped, but blocked_paths remains
    assert "allowed_paths" not in ctx.resume_inputs
    assert "blocked_paths" in ctx.resume_inputs


@pytest.mark.anyio
async def test_folder_scope_success_policy_construction() -> None:
    # Valid paths
    allowed_path = (
        "C:/Users/User/Documents" if os.name == "nt" else "/home/user/documents"
    )
    blocked_path = (
        "C:/Users/User/Downloads" if os.name == "nt" else "/home/user/downloads"
    )

    ctx = MagicMock()
    ctx.resume_inputs = {"allowed_paths": allowed_path, "blocked_paths": blocked_path}
    node_input = FolderScopeInput(cleanup_intent=True)

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    assert event.actions.route == "scan"
    policy = event.output.folder_scope_policy
    assert policy is not None
    assert policy.version == "1.0"
    assert policy.source == "interactive_cleanup"
    assert policy.created_by == "FolderScopeNode"

    # Verify that the allowed path is in allowed_paths
    assert allowed_path.lower() in policy.allowed_paths

    # Verify that default system paths and the user blocked path are inside blocked_paths
    assert blocked_path.lower() in policy.blocked_paths
    # Default system paths should be populated
    if os.name == "nt":
        assert "c:/windows" in policy.blocked_paths
    else:
        assert "/system" in policy.blocked_paths or "/usr" in policy.blocked_paths


def test_validate_single_path_constraints() -> None:
    # Absolute path constraint
    with pytest.raises(ValueError, match="Paths must be absolute"):
        _validate_single_path("relative/path", is_allowed=True)

    # Env variable constraint
    with pytest.raises(ValueError, match="environment variables"):
        _validate_single_path("%APPDATA%\\folder", is_allowed=True)

    # Wildcards constraint
    with pytest.raises(ValueError, match="wildcards"):
        _validate_single_path("C:\\Users\\*\\Downloads", is_allowed=True)

    # Directory traversal constraint
    with pytest.raises(ValueError, match="directory traversal"):
        _validate_single_path("C:\\Users\\User\\..\\Documents", is_allowed=True)

    # System directory matches
    if os.name == "nt":
        with pytest.raises(ValueError, match="protected system folder"):
            _validate_single_path("C:\\Windows", is_allowed=True)
        with pytest.raises(ValueError, match="protected system folder"):
            _validate_single_path("C:\\Program Files\\app", is_allowed=True)
        with pytest.raises(ValueError, match="protected system component"):
            _validate_single_path("C:\\Users\\User\\.git", is_allowed=True)


def test_parse_paths_helper() -> None:
    assert _parse_paths("path1, path2\npath3") == ["path1", "path2", "path3"]
    assert _parse_paths(["path1", "path2"]) == ["path1", "path2"]
    assert _parse_paths("") == []


def test_file_discovery_node_integration() -> None:
    # Verify FileDiscoveryNode accepts FolderScopeOutput and executes correctly
    allowed_path = os.getcwd()
    policy = FolderScopePolicy(
        allowed_paths=[allowed_path],
        blocked_paths=[],
    )
    scope_output = FolderScopeOutput(folder_scope_policy=policy, message="Success")

    discovery_output = file_discovery_node(scope_output)
    assert discovery_output.folder_scope_policy.allowed_paths == [allowed_path]
    assert len(discovery_output.file_inventory) >= 0
