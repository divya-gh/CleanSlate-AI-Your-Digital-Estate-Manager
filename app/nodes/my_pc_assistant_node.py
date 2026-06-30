"""MyPCAssistantNode — ADK 2.0 Graph Workflow Node.

Main entry point and classification layer for all interactive user sessions.
Uses a safety-biased Gemini model call to categorize user queries into cleanup,
search, explain, or other, with a conservative regex heuristics fallback.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Literal

from google import genai
from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.events.request_input import RequestInput
from google.genai import types as genai_types
from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class MyPCAssistantInput(BaseModel):
    """Input payload consumed by MyPCAssistantNode."""

    user_query: str = Field(description="The natural language query from the user.")
    session_id: str | None = Field(
        default=None, description="Optional session identifier."
    )
    timestamp: datetime | None = Field(
        default_factory=datetime.utcnow, description="Timestamp of the query."
    )

    @model_validator(mode="before")
    @classmethod
    def _validate_content(cls, data: Any) -> Any:
        """Handle incoming format variants from the runner."""
        if isinstance(data, dict):
            # If parts exists (Vertex API agent format)
            if "parts" in data:
                parts = data["parts"]
                text = ""
                if isinstance(parts, list):
                    for part in parts:
                        if isinstance(part, dict) and "text" in part:
                            text += part["text"]
                        elif hasattr(part, "text") and part.text:
                            text += part.text
                return {
                    "user_query": text,
                    "session_id": data.get("session_id"),
                    "timestamp": data.get("timestamp"),
                }

            # Map standard request_text to user_query if provided
            if "request_text" in data:
                return {
                    "user_query": data["request_text"],
                    "session_id": data.get("session_id"),
                    "timestamp": data.get("timestamp"),
                }

            if "user_query" in data:
                return data

        if hasattr(data, "parts") and data.parts:
            text = ""
            for part in data.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text
            return {"user_query": text}

        if isinstance(data, str):
            return {"user_query": data}

        return data


class MyPCAssistantOutput(BaseModel):
    """Output payload emitted by MyPCAssistantNode."""

    intent: Literal["cleanup", "search", "explain", "other"] = Field(
        description="The detected user intent: 'cleanup', 'search', 'explain', 'other'."
    )
    search_query: str | None = Field(
        default=None, description="The extracted keyword/pattern if intent is 'search'."
    )
    explanation_request: str | None = Field(
        default=None, description="The clean user question if intent is 'explain'."
    )
    cleanup_intent_reasoning: str | None = Field(
        default=None, description="Explanation of why cleanup was triggered."
    )
    conversational_response: str | None = Field(
        default=None, description="Conversational response if intent is 'other'."
    )
    # Pass through the user's raw query so downstream nodes (e.g. FolderScopeNode)
    # can read it as node_input.user_query for HITL answer injection.
    user_query: str | None = Field(
        default=None, description="Raw user query passed through to downstream nodes."
    )

    # SummaryOutput compatibility fields (so the UI can render conversational fallback)
    total_actions: int = Field(default=0, description="Summary compatibility.")
    successful_actions: int = Field(default=0, description="Summary compatibility.")
    failed_actions: int = Field(default=0, description="Summary compatibility.")
    skipped_actions: int = Field(default=0, description="Summary compatibility.")
    estimated_recovery: int = Field(default=0, description="Summary compatibility.")
    dry_run: bool = Field(default=False, description="Summary compatibility.")
    sensitive_files_protected: int = Field(
        default=0, description="Summary compatibility."
    )
    rollback_supported_actions: int = Field(
        default=0, description="Summary compatibility."
    )
    rollback_unsupported_actions: int = Field(
        default=0, description="Summary compatibility."
    )
    human_readable_report: str = Field(default="", description="Summary compatibility.")
    errors: list[str] | None = Field(default=None, description="Summary compatibility.")


class GeminiIntentResult(BaseModel):
    """Schema for structured Gemini output."""

    intent: Literal["cleanup", "search", "explain", "other"]
    search_query: str | None = None
    explanation_request: str | None = None
    reasoning: str


# ---------------------------------------------------------------------------
# UI Copy
# ---------------------------------------------------------------------------

UI_WELCOME_MESSAGE = (
    "Hello! I'm CleanSlate AI \u2014 My PC Assistant.\n\n"
    "I'm here to help you manage, organize, and optimize your computer safely.\n"
    "I can:\n"
    "  \U0001f4c2  Search your files\n"
    "  \U0001f9f9  Declutter folders and remove duplicates\n"
    "  \U0001f512  Detect and protect sensitive documents\n"
    "  \U0001f4c5  Run your Weekly Organizer automatically\n\n"
    "You can say: \"Organize my computer\" to get started.\n"
    + "\u2500" * 60  # explicit + so * 60 applies only to the separator, not the whole message
)


# ---------------------------------------------------------------------------
# Welcome Node — fires on session load, shows greeting, captures first query
# ---------------------------------------------------------------------------


class WelcomeInput(BaseModel):
    """Accepts any dict/object as input (START sends raw user message)."""

    model_config = __import__("pydantic").ConfigDict(from_attributes=True, extra="allow")


class WelcomeOutput(MyPCAssistantInput):
    """Pass-through: WelcomeNode re-emits the user query as MyPCAssistantInput."""


async def welcome_node(ctx: Context, node_input: WelcomeInput):
    """Welcome Node — displays the greeting and captures the user's first query.

    This is the first node in the workflow (wired START → welcome_node →
    my_pc_assistant_node).  On the very first turn it yields a RequestInput
    that causes the ADK playground to show the welcome banner immediately.
    The user's response is forwarded as the query for intent classification.
    """
    ri = ctx.resume_inputs or {}

    if "first_query" not in ri:
        yield RequestInput(
            interrupt_id="first_query",
            message=UI_WELCOME_MESSAGE,
        )
        return

    first_query = str(ri["first_query"]).strip()
    output = WelcomeOutput(user_query=first_query or "hello")
    yield Event(output=output, actions=EventActions(route=None))



# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """Analyze the following user query to determine the user's intent:
Query: "{query}"

Categorize the intent into exactly one of:
1. "cleanup": The user is explicitly asking to start a cleanup, decluttering, optimization, or organization process on their PC.
   - Explicit cleanup verbs: "clean", "cleanup", "organize my PC", "organize my computer", "organize", "declutter", "optimize storage", "delete duplicates", "tidy up", "sort my files".
   - Safety rule: Do NOT classify as "cleanup" for ambiguous queries like "my PC is slow", "my disk is full", or "I want to find files". Those must be classified as "other".
2. "search": The user is asking to find or search for specific files, patterns, or extensions.
   - Examples: "find my resume", "search for pdfs", "where is my tax document?".
   - Extract the search keyword or pattern in `search_query` (do not include absolute paths or system paths).
3. "explain": The user is asking a general question about how the PC assistant works or asking for an explanation of a concept.
   - Examples: "how do you clean files?", "what is a duplicate file?".
   - Extract the clean question in `explanation_request`.
4. "other": Any other conversational messages, greetings, vague complaints (e.g. "my pc is slow"), or ambiguous requests.

Safety Guidelines:
- If the query is ambiguous, contains multiple mixed intents, or is partially cleanup-related, always default to "other".
- Only explicit cleanup verbs can map to "cleanup".
- Never reveal sensitive file paths or system paths.
- Never output any filesystem metadata.
"""


# ---------------------------------------------------------------------------
# Regex Conservative Fallback
# ---------------------------------------------------------------------------


def _regex_heuristics_fallback(query: str) -> GeminiIntentResult:
    """Fallback rule-based classification when Gemini is unavailable."""
    q_clean = query.strip().lower()

    # Conservative explain check
    explain_keywords = [r"\bhow to\b", r"\bexplain\b", r"\bwhat is\b", r"\bwhy does\b"]
    if any(re.search(pat, q_clean) for pat in explain_keywords):
        return GeminiIntentResult(
            intent="explain",
            explanation_request=query,
            reasoning="Fallback Regex Heuristic: Explanation pattern detected.",
        )

    # Conservative cleanup check — broad enough to catch common phrasings
    cleanup_keywords = [
        r"\bclean\b",
        r"\bcleanup\b",
        r"\borganize\b",      # matches "organize my computer", "organize my PC", etc.
        r"\bdeclutter\b",
        r"\boptimize storage\b",
        r"\bdelete duplicates\b",
        r"\btidy up\b",
        r"\bsort my files\b",
    ]
    if any(re.search(pat, q_clean) for pat in cleanup_keywords):
        return GeminiIntentResult(
            intent="cleanup",
            reasoning="Fallback Regex Heuristic: Explicit cleanup keyword detected.",
        )

    # Conservative search check
    search_keywords = [r"\bfind\b", r"\bsearch\b", r"\blocate\b", r"\bwhere is\b"]
    if any(re.search(pat, q_clean) for pat in search_keywords):
        # Basic search query extraction
        extracted = None
        for keyword in ["find", "search for", "search", "locate", "where is"]:
            if keyword in q_clean:
                parts = q_clean.split(keyword, 1)
                if len(parts) > 1 and parts[1].strip():
                    extracted = parts[1].strip()
                    break
        return GeminiIntentResult(
            intent="search",
            search_query=extracted,
            reasoning="Fallback Regex Heuristic: Search keyword detected.",
        )

    return GeminiIntentResult(
        intent="other",
        reasoning="Fallback Regex Heuristic: Query is conversational or ambiguous.",
    )


# ---------------------------------------------------------------------------
# Sanitization Helper
# ---------------------------------------------------------------------------


def _sanitize_search_query(q: str | None) -> str | None:
    """Sanitizes search query to prevent wildcards, absolute path injection, or system directories."""
    if not q:
        return None

    # Replace windows backslashes with forward slashes for cross-platform basename extraction
    s = q.replace("\\", "/")

    # Strip wildcards
    s = re.sub(r"[\*\?]", "", s)

    # Extract basename to remove directories
    s = os.path.basename(s)

    # Filter out common sensitive / system keywords
    blocked_keywords = {
        "system",
        "windows",
        "system32",
        "programdata",
        "appdata",
        "ssn",
        "password",
        "tax",
        "banking",
    }
    words = s.split()
    cleaned_words = [w for w in words if w.lower() not in blocked_keywords]

    cleaned = " ".join(cleaned_words).strip()
    return cleaned if cleaned else None


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------

# Keys that indicate we are in the middle of an organize flow
_ORGANIZE_RESUME_KEYS = {"allowed_paths", "blocked_paths", "cleanup_pin",
                          "security_question_answer", "weekly_organizer_enabled"}

async def my_pc_assistant_node(ctx: Context, node_input: MyPCAssistantInput):
    """MyPCAssistantNode — entry point node for intent classification.

    Implemented as an async generator so ADK properly injects ``ctx`` and
    ``ctx.resume_inputs``.  With rerun_on_resume=True, ADK replays this node
    on every resume turn.  If resume_inputs contain organize-flow keys we
    bypass Gemini and route directly to cleanup so FolderScopeNode can
    continue the multi-turn conversation.
    """
    # ── Organize-flow resume detection via persistent session state ──────────
    # With rerun_on_resume=True, ADK always replays from THIS entry node.
    # ctx.resume_inputs here contains the user's latest HITL answer.
    # We must capture it and persist it to session state, then route to
    # cleanup so folder_scope_node can read all accumulated answers.
    try:
        _session_state = ctx.session.state
    except AttributeError:
        _session_state = {}

    _ri = dict(getattr(ctx, "resume_inputs", None) or {})
    _STEP_KEYS = {"parent_folder", "subfolder_selections", "user_pin",
                  "security_question", "security_answer", "weekly_organizer"}
    _new_answers = {k: v for k, v in _ri.items() if k in _STEP_KEYS}

    if _session_state.get("organize_flow_active", False):
        output = MyPCAssistantOutput(
            intent="cleanup",
            cleanup_intent_reasoning="Resuming organize flow (session state flag)",
            # Pass through the user's raw query so folder_scope_node can read
            # it as node_input.user_query to use as the HITL step answer.
            user_query=node_input.user_query,
        )
        # Also persist the new answers so folder_scope_node can read them
        _state_delta = {"organize_flow_active": True, **_new_answers}
        yield Event(output=output, actions=EventActions(
            route="cleanup",
            state_delta=_state_delta,
        ))
        return

    query = node_input.user_query

    # Call Gemini model
    client = genai.Client()
    try:
        response = client.models.generate_content(  # nosemgrep
            model="gemini-2.5-flash",
            contents=PROMPT_TEMPLATE.format(query=query),
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiIntentResult,
                temperature=0.0,
            ),
        )
        result = GeminiIntentResult.model_validate_json(response.text)
    except Exception:
        # Fallback to conservative regex heuristics
        result = _regex_heuristics_fallback(query)

    # Route and output construction
    if result.intent == "cleanup":
        output = MyPCAssistantOutput(
            intent="cleanup",
            cleanup_intent_reasoning="User explicitly requested cleanup",
        )
        # Set the session flag so mid-organize resumes short-circuit here
        yield Event(
            output=output,
            actions=EventActions(
                route="cleanup",
                state_delta={"organize_flow_active": True},
            ),
        )

    elif result.intent == "search":
        sanitized = _sanitize_search_query(result.search_query)
        output = MyPCAssistantOutput(
            intent="search",
            search_query=sanitized,
        )
        yield Event(output=output, actions=EventActions(route="search"))

    elif result.intent == "explain":
        output = MyPCAssistantOutput(
            intent="explain",
            explanation_request=result.explanation_request,
        )
        yield Event(output=output, actions=EventActions(route="explain"))

    else:
        # Intent is other — detect greetings and show the welcome message
        _greeting_patterns = [
            r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgreet\b",
            r"\bwho are you\b", r"\bwhat can you do\b", r"\bhelp\b",
        ]
        is_greeting = any(
            re.search(pat, query.lower()) for pat in _greeting_patterns
        )
        reply = UI_WELCOME_MESSAGE if is_greeting else (
            "I didn't quite catch that. "
            "Try: \"Organize my computer\", \"Find my resume\", or \"What is a duplicate file?\"\n\n"
            + UI_WELCOME_MESSAGE
        )
        output = MyPCAssistantOutput(
            intent="other",
            conversational_response=reply,
            human_readable_report=reply,
        )
        # route="other" → no matching edge → workflow terminates (does NOT loop)
        yield Event(output=output, actions=EventActions(route="other"))

