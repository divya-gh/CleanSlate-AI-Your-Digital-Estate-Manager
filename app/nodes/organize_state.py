"""organize_state.py — Shared in-process store for the organize flow.

Replaces ADK ``state_delta`` events for folder_scope_node step answers.

With ``rerun_on_resume=True`` on the workflow, every ``state_delta`` event
causes ADK to replay the entire workflow from the beginning within the SAME
SSE response.  Replays accumulate: after N turns each with state_delta, there
are O(2^N) replays, each appending the RequestInput message to the SSE buffer.
The result is 60+ copies of "Security Setup" in a single response.

This module stores step answers in a plain Python dict.  Because the ADK
server is a single-process uvicorn instance, module-level state persists
across HTTP requests without any ADK event needed.  No state_delta → no
replays → no cascade.

Usage
-----
    from app.nodes.organize_state import OrganizerSessionStore

    store = OrganizerSessionStore.for_session(session_id)
    store.is_active()         # bool
    store.set_active()        # mark flow started
    store.get(step)           # read a step answer (or None)
    store.set(step, value)    # save a step answer
    store.pop(step)           # remove a step answer (for re-prompt)
    store.clear()             # wipe all state for this session
    store.as_dict()           # snapshot of all stored keys
"""

from __future__ import annotations

# Module-level storage: session_id (str) → {step_key: value}
_STORE: dict[str, dict] = {}

_ACTIVE_KEY = "organize_flow_active"


class OrganizerSessionStore:
    """Thin wrapper around _STORE for one session."""

    def __init__(self, session_id: str) -> None:
        self._sid = session_id
        if session_id not in _STORE:
            _STORE[session_id] = {}

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def for_session(cls, session_id: str) -> "OrganizerSessionStore":
        """Return (or create) the store for *session_id*."""
        return cls(session_id)

    # ------------------------------------------------------------------
    # Active-flag helpers
    # ------------------------------------------------------------------

    def is_active(self) -> bool:
        return bool(_STORE[self._sid].get(_ACTIVE_KEY))

    def set_active(self) -> None:
        _STORE[self._sid][_ACTIVE_KEY] = True

    def deactivate(self) -> None:
        _STORE[self._sid].pop(_ACTIVE_KEY, None)

    # ------------------------------------------------------------------
    # Step-answer helpers
    # ------------------------------------------------------------------

    def get(self, step: str, default=None):
        return _STORE[self._sid].get(step, default)

    def set(self, step: str, value) -> None:
        _STORE[self._sid][step] = value

    def pop(self, step: str) -> None:
        _STORE[self._sid].pop(step, None)

    def has(self, step: str) -> bool:
        return step in _STORE[self._sid]

    # ------------------------------------------------------------------
    # Bulk helpers
    # ------------------------------------------------------------------

    def as_dict(self) -> dict:
        """Return a snapshot of all stored keys for this session."""
        return dict(_STORE[self._sid])

    def clear(self) -> None:
        """Wipe all state for this session (used on flow reset / new session)."""
        _STORE[self._sid].clear()

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __contains__(self, step: str) -> bool:
        return self.has(step)

    def __repr__(self) -> str:
        return f"OrganizerSessionStore(sid={self._sid!r}, data={_STORE[self._sid]!r})"
