# ADK playground entry point for CleanSlate AI - My PC Assistant.
# This thin wrapper re-exports root_agent from the app package so that
# `adk web agents/` discovers this directory as "cleanslate_ai_my_pc_assistant".
from app.agent import root_agent  # noqa: F401

__all__ = ["root_agent"]
