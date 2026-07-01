import os
import json as _json
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
from app.nodes.organize_state import OrganizerSessionStore


@pytest.fixture(autouse=True)
def clean_session_store() -> None:
    # Clear the session store before/after each test to prevent cross-test leakage
    from app.nodes.organize_state import _STORE
    _STORE.clear()


@pytest.mark.anyio
async def test_folder_scope_cleanup_intent_false() -> None:
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.id = "test_session"
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
async def test_folder_scope_prompts_for_parent_folder() -> None:
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.id = "test_session"
    ctx.resume_inputs = {}
    node_input = FolderScopeInput(cleanup_intent=True)

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, RequestInput)
    assert event.interrupt_id == "parent_folder"
    assert "Suggested safe folders" in event.message


@pytest.mark.anyio
async def test_folder_scope_prompts_for_subfolder_selections() -> None:
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.id = "test_session"
    node_input = FolderScopeInput(cleanup_intent=True)

    store = OrganizerSessionStore.for_session("test_session")
    store.set_active()
    # Mock that the user entered a valid parent folder path
    cwd = os.getcwd().replace("\\", "/")
    store.set("parent_folder", cwd)

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, RequestInput)
    assert event.interrupt_id == "subfolder_selections"


@pytest.mark.anyio
async def test_folder_scope_prompts_for_user_pin() -> None:
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.id = "test_session"
    node_input = FolderScopeInput(cleanup_intent=True)

    parent_folder = "C:/Users/User/Documents" if os.name == "nt" else "/home/user/documents"
    store = OrganizerSessionStore.for_session("test_session")
    store.set_active()
    store.set("parent_folder", parent_folder)
    store.set("subfolder_selections", _json.dumps({"organized": [parent_folder + "/SubFolder"], "never_touch": []}))

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, RequestInput)
    assert event.interrupt_id == "user_pin"
    assert "create a 4-digit PIN" in event.message


@pytest.mark.anyio
async def test_folder_scope_prompts_for_security_question() -> None:
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.id = "test_session"
    node_input = FolderScopeInput(cleanup_intent=True)

    parent_folder = "C:/Users/User/Documents" if os.name == "nt" else "/home/user/documents"
    store = OrganizerSessionStore.for_session("test_session")
    store.set_active()
    store.set("parent_folder", parent_folder)
    store.set("subfolder_selections", _json.dumps({"organized": [parent_folder + "/SubFolder"], "never_touch": []}))
    store.set("user_pin", "1234")

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, RequestInput)
    assert event.interrupt_id == "security_question"
    assert "Choose a security question" in event.message


@pytest.mark.anyio
async def test_folder_scope_prompts_for_security_answer() -> None:
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.id = "test_session"
    node_input = FolderScopeInput(cleanup_intent=True)

    parent_folder = "C:/Users/User/Documents" if os.name == "nt" else "/home/user/documents"
    store = OrganizerSessionStore.for_session("test_session")
    store.set_active()
    store.set("parent_folder", parent_folder)
    store.set("subfolder_selections", _json.dumps({"organized": [parent_folder + "/SubFolder"], "never_touch": []}))
    store.set("user_pin", "1234")
    store.set("security_question", "1")  # First question

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, RequestInput)
    assert event.interrupt_id == "security_answer"
    assert "first pet?" in event.message


@pytest.mark.anyio
async def test_folder_scope_prompts_for_weekly_organizer() -> None:
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.id = "test_session"
    node_input = FolderScopeInput(cleanup_intent=True)

    parent_folder = "C:/Users/User/Documents" if os.name == "nt" else "/home/user/documents"
    store = OrganizerSessionStore.for_session("test_session")
    store.set_active()
    store.set("parent_folder", parent_folder)
    store.set("subfolder_selections", _json.dumps({"organized": [parent_folder + "/SubFolder"], "never_touch": []}))
    store.set("user_pin", "1234")
    store.set("security_question", "1")
    store.set("security_answer", "Buddy")

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, RequestInput)
    assert event.interrupt_id == "weekly_organizer"
    assert "__TOGGLE_SELECT__" in event.message


@pytest.mark.anyio
async def test_folder_scope_success_policy_construction() -> None:
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.id = "test_session"
    node_input = FolderScopeInput(cleanup_intent=True)

    parent_folder = "C:/Users/User/Documents" if os.name == "nt" else "/home/user/documents"
    store = OrganizerSessionStore.for_session("test_session")
    store.set_active()
    store.set("parent_folder", parent_folder)
    store.set("subfolder_selections", _json.dumps({"organized": [parent_folder + "/Work"], "never_touch": [parent_folder + "/Private"]}))
    store.set("user_pin", "1234")
    store.set("security_question", "1")
    store.set("security_answer", "Buddy")
    store.set("weekly_organizer", "enable")

    events = []
    async for event in folder_scope_node(ctx, node_input):
        events.append(event)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    assert event.actions.route == "scope_ok"
    policy = event.output.folder_scope_policy
    assert policy is not None
    assert (parent_folder + "/Work").lower() in policy.allowed_paths
    assert (parent_folder + "/Private").lower() in policy.blocked_paths


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

    res = file_discovery_node(scope_output)
    discovery_output = res.output if hasattr(res, "output") else res
    assert discovery_output.folder_scope_policy.allowed_paths == [allowed_path]
    assert len(discovery_output.file_inventory) >= 0
