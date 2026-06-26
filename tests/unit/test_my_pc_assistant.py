from unittest.mock import MagicMock, patch

import pytest

from app.nodes import (
    MyPCAssistantInput,
    MyPCAssistantOutput,
    my_pc_assistant_node,
    summary_node,
)
from app.nodes.file_discovery_node import (
    file_discovery_node,
)
from app.nodes.my_pc_assistant_node import (
    _regex_heuristics_fallback,
    _sanitize_search_query,
)
from app.nodes.summary_node import SummaryOutput

# ---------------------------------------------------------------------------
# Heuristics Fallback & Sanitization Tests
# ---------------------------------------------------------------------------


def test_regex_fallback_heuristics() -> None:
    # Cleanup detection
    res = _regex_heuristics_fallback("Please clean my PC immediately")
    assert res.intent == "cleanup"

    res = _regex_heuristics_fallback("organize my PC today")
    assert res.intent == "cleanup"

    # Search detection
    res = _regex_heuristics_fallback("find my resume")
    assert res.intent == "search"
    assert res.search_query == "my resume"

    # Explain detection
    res = _regex_heuristics_fallback("how to clean old logs?")
    assert res.intent == "explain"

    # Other / Ambiguous detection
    res = _regex_heuristics_fallback("my PC is slow and disk is full")
    assert res.intent == "other"


def test_sanitize_search_query() -> None:
    # Wildcards removed
    assert _sanitize_search_query("*.txt") == ".txt"
    # Drive letter and path separators removed
    assert _sanitize_search_query("C:\\Windows\\system32\\file.txt") == "file.txt"
    # Blocked system/sensitive keywords removed
    assert (
        _sanitize_search_query("search for ssn or password file")
        == "search for or file"
    )
    assert _sanitize_search_query("appdata folder windows path") == "folder path"


# ---------------------------------------------------------------------------
# MyPCAssistantNode Classification & Routing Tests
# ---------------------------------------------------------------------------


@patch("google.genai.Client")
def test_my_pc_assistant_cleanup_intent(mock_client_class) -> None:
    # Mock Gemini response
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Return structured json mapping to GeminiIntentResult
    mock_response.text = (
        '{"intent": "cleanup", "reasoning": "Explicit cleanup request"}'
    )
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    node_input = MyPCAssistantInput(user_query="Please declutter my desktop")
    event = my_pc_assistant_node(node_input)

    assert event.actions.route == "cleanup"
    assert event.output.intent == "cleanup"
    assert event.output.cleanup_intent_reasoning == "User explicitly requested cleanup"
    assert event.output.search_query is None
    assert event.output.explanation_request is None


@patch("google.genai.Client")
def test_my_pc_assistant_search_intent(mock_client_class) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"intent": "search", "search_query": "tax document 2025.pdf", "reasoning": "Search requested"}'
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    node_input = MyPCAssistantInput(user_query="find my tax document 2025")
    event = my_pc_assistant_node(node_input)

    assert event.actions.route == "search"
    assert event.output.intent == "search"
    assert event.output.search_query == "document 2025.pdf"


@patch("google.genai.Client")
def test_my_pc_assistant_explain_intent(mock_client_class) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"intent": "explain", "explanation_request": "How does duplicate file cleaning work?", "reasoning": "Explanation query"}'
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    node_input = MyPCAssistantInput(user_query="explain duplicate cleaning")
    event = my_pc_assistant_node(node_input)

    assert event.actions.route == "explain"
    assert event.output.intent == "explain"
    assert event.output.explanation_request == "How does duplicate file cleaning work?"


@patch("google.genai.Client")
def test_my_pc_assistant_other_intent(mock_client_class) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"intent": "other", "reasoning": "Conversational greeting"}'
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    node_input = MyPCAssistantInput(user_query="hello assistant")
    event = my_pc_assistant_node(node_input)

    assert event.actions.route is None
    assert event.output.intent == "other"
    assert "How can I help you today?" in event.output.human_readable_report


@patch("google.genai.Client")
def test_my_pc_assistant_fallback_on_exception(mock_client_class) -> None:
    # Trigger exception to test regex fallback
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")
    mock_client_class.return_value = mock_client

    node_input = MyPCAssistantInput(user_query="clean old duplicate files")
    event = my_pc_assistant_node(node_input)

    # Fallback to regex cleanup
    assert event.actions.route == "cleanup"
    assert event.output.intent == "cleanup"


# ---------------------------------------------------------------------------
# FileDiscoveryNode Integration & Validation Tests
# ---------------------------------------------------------------------------


def test_file_discovery_node_accepts_assistant_search() -> None:
    assistant_output = MyPCAssistantOutput(
        intent="search",
        search_query="project_plan.docx",
    )
    # Executing file_discovery_node with MyPCAssistantOutput constructs discovery input
    output = file_discovery_node(assistant_output)
    # Check that search query was propagated to output
    assert "project_plan.docx" in output.reasoning


def test_file_discovery_node_rejects_non_search() -> None:
    assistant_output = MyPCAssistantOutput(
        intent="cleanup",
    )
    with pytest.raises(
        ValueError, match="only accepts MyPCAssistantOutput when intent is 'search'"
    ):
        file_discovery_node(assistant_output)


def test_file_discovery_node_validation() -> None:
    # Empty query rejection
    empty_output = MyPCAssistantOutput(intent="search", search_query="")
    with pytest.raises(ValueError, match="search_query must not be empty"):
        file_discovery_node(empty_output)

    # Sensitive/System keyword rejection
    system_output = MyPCAssistantOutput(
        intent="search", search_query="search for system32 files"
    )
    with pytest.raises(ValueError, match="contains blocked system/sensitive keywords"):
        file_discovery_node(system_output)

    # Length limit rejection
    long_output = MyPCAssistantOutput(intent="search", search_query="a" * 201)
    with pytest.raises(ValueError, match="exceeds maximum length"):
        file_discovery_node(long_output)


# ---------------------------------------------------------------------------
# SummaryNode Conversational Explanation Mode
# ---------------------------------------------------------------------------


@patch("google.genai.Client")
def test_summary_node_handles_explanation(mock_client_class) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a detailed markdown explanation of duplicate files."
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    assistant_output = MyPCAssistantOutput(
        intent="explain",
        explanation_request="Explain duplicate file cleanup",
    )

    output = summary_node(assistant_output)
    assert isinstance(output, SummaryOutput)
    assert (
        output.human_readable_report
        == "This is a detailed markdown explanation of duplicate files."
    )
    assert output.total_actions == 0
    assert output.successful_actions == 0
