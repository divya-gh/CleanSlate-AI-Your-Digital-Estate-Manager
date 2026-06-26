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
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
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
# Prompt template
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """Analyze the following user query to determine the user's intent:
Query: "{query}"

Categorize the intent into exactly one of:
1. "cleanup": The user is explicitly asking to start a cleanup, decluttering, optimization, or organization process on their PC.
   - Explicit cleanup verbs: "clean", "organize my PC", "declutter", "optimize storage", "delete duplicates".
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

    # Conservative cleanup check
    cleanup_keywords = [
        r"\bclean\b",
        r"\bcleanup\b",
        r"\borganize my pc\b",
        r"\bdeclutter\b",
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


def my_pc_assistant_node(node_input: MyPCAssistantInput) -> Event:
    """MyPCAssistantNode — entry point node for intent classification."""
    query = node_input.user_query

    # Call Gemini model
    client = genai.Client()
    try:
        response = client.models.generate_content(
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
        return Event(output=output, actions=EventActions(route="cleanup"))

    elif result.intent == "search":
        sanitized = _sanitize_search_query(result.search_query)
        output = MyPCAssistantOutput(
            intent="search",
            search_query=sanitized,
        )
        return Event(output=output, actions=EventActions(route="search"))

    elif result.intent == "explain":
        output = MyPCAssistantOutput(
            intent="explain",
            explanation_request=result.explanation_request,
        )
        return Event(output=output, actions=EventActions(route="explain"))

    else:
        # Intent is other — respond conversationally
        reply = (
            "Hello! I detected that you are looking for assistance, but I did not "
            "recognize an explicit instruction to clean up, search, or explain a PC assistant feature. "
            "How can I help you today?"
        )
        output = MyPCAssistantOutput(
            intent="other",
            conversational_response=reply,
            human_readable_report=reply,
        )
        # Terminates the workflow
        return Event(
            output=output,
            content=genai_types.Content(
                role="model", parts=[genai_types.Part.from_text(text=reply)]
            ),
            actions=EventActions(route=None),
        )
