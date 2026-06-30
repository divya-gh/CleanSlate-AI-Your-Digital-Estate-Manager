"""SummaryNode — ADK 2.0 Graph Workflow Node.

Pure reporting node that aggregates the outcomes of all executed cleanup actions,
tracks rollback counts, and generates a secure human-readable markdown summary report.
Does not perform any file system modifications.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from google import genai
from pydantic import BaseModel, Field

from app.nodes.execution_node import ExecutionOutput
from app.nodes.file_discovery_node import FolderScopePolicy
from app.nodes.my_pc_assistant_node import MyPCAssistantOutput
from app.nodes.rollback_node import RollbackOutput
from app.nodes.sensitive_detection_node import SensitiveFileEntry
from app.mcp_tools.registry import test_tool

# ---------------------------------------------------------------------------
# Input / Output schemas
# ---------------------------------------------------------------------------


class SummaryOutput(BaseModel):
    """Output payload emitted by SummaryNode."""

    total_actions: int = Field(description="Total count of proposed actions.")
    successful_actions: int = Field(
        description="Count of successfully executed actions."
    )
    failed_actions: int = Field(description="Count of failed execution actions.")
    skipped_actions: int = Field(
        description="Count of actions skipped due to safety checks."
    )
    estimated_recovery: int = Field(description="Total estimated recovery in bytes.")
    dry_run: bool = Field(description="Whether this run was a dry run.")
    sensitive_files_protected: int = Field(
        description="Number of sensitive files protected during run."
    )
    rollback_supported_actions: int = Field(
        description="Number of actions supporting rollback."
    )
    rollback_unsupported_actions: int = Field(
        description="Number of actions where rollback is unsupported."
    )
    human_readable_report: str = Field(
        description="The sectioned human-readable summary report in markdown."
    )
    errors: list[str] | None = Field(
        default_factory=list,
        description="Execution errors or failures surfaced to the user.",
    )


# ---------------------------------------------------------------------------
# Safety Helpers
# ---------------------------------------------------------------------------


_SYSTEM_COMPONENTS = {
    "windows",
    "system32",
    "program files",
    "program files (x86)",
    "programdata",
    "appdata",
    ".git",
    ".venv",
    "node_modules",
    ".ruff_cache",
    ".pytest_cache",
}


def _is_system_folder(path: str) -> bool:
    """Helper to detect system directories."""
    parts = [part.lower() for part in Path(path).parts]
    for part in parts:
        if part in _SYSTEM_COMPONENTS:
            if part == "appdata" and "temp" in parts:
                continue
            return True
    return False


def _is_path_blocked(path: str, policy: FolderScopePolicy) -> bool:
    """Helper to check if a path resides under blocked directories."""
    resolved_path = os.path.normcase(os.path.abspath(path))
    for bp in policy.blocked_paths:
        bp_resolved = os.path.normcase(os.path.abspath(bp))
        if resolved_path == bp_resolved or resolved_path.startswith(
            bp_resolved + os.sep
        ):
            return True
    return False


def _is_sensitive_file(path: str, sensitive_files: list[SensitiveFileEntry]) -> bool:
    """Check if the file path matches any sensitive file entry."""
    norm_path = os.path.normcase(os.path.abspath(path))
    for sf in sensitive_files:
        if os.path.normcase(os.path.abspath(sf.path)) == norm_path:
            return sf.sensitive
    return False


def _clean_path(path: str, policy: FolderScopePolicy) -> str:
    """Hides absolute system/blocked paths by replacing them with generic text."""
    if _is_path_blocked(path, policy) or _is_system_folder(path):
        return "a protected file"
    return os.path.basename(path)


def _clean_reasoning(reasoning: str) -> str:
    """Sanitizes reasoning string to remove sensitive information or classification text."""
    r_lower = reasoning.lower()
    if any(
        k in r_lower
        for k in [
            "sensitive",
            "ssn",
            "banking",
            "tax",
            "legal",
            "medical",
            "password",
            "api_key",
            "identity",
        ]
    ):
        return "Runtime Safety Check: Sensitive file protection."
    if "gemini" in r_lower:
        return "Classification analysis completed."
    return reasoning


# ---------------------------------------------------------------------------
# ADK 2.0 Function Node
# ---------------------------------------------------------------------------


def summary_node(
    node_input: ExecutionOutput | RollbackOutput | MyPCAssistantOutput,
) -> SummaryOutput:
    """SummaryNode — aggregates and reports execution outcomes safely."""
    if isinstance(node_input, MyPCAssistantOutput):
        if node_input.conversational_response:
            report = node_input.conversational_response
            r_lower = report.lower()
            if "cancel" in r_lower or "abort" in r_lower:
                session_id = hashlib.sha256(report.encode()).hexdigest()[:8]
                entry_dict = {
                    "node": "SummaryNode",
                    "action_type": "plan",
                    "path": None,
                    "is_sensitive": False,
                    "hitl_status": "not_required",
                    "result": "skipped",
                    "reason": "Conversational cancel/abort request processed.",
                    "session_id": session_id,
                    "tool_name": "write_log",
                }
                test_tool("write_log", entry=json.dumps(entry_dict))
        elif node_input.explanation_request:
            # Generate a secure conversational explanation via Gemini
            client = genai.Client()
            prompt = (
                f"You are a helpful PC assistant. Securely explain the following topic to the user:\n"
                f"Topic: {node_input.explanation_request}\n\n"
                f"Guidelines:\n"
                f"- Never reveal any actual absolute file paths, backup folders, or system directories.\n"
                f"- Speak conversationally and guide the user in markdown formatting.\n"
                f"- Do not refer to any local files or system-specific metadata."
            )
            try:
                response = client.models.generate_content(  # nosemgrep
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                report = response.text
            except Exception as e:
                report = f"I am sorry, I encountered an issue generating the explanation: {e}"
        else:
            report = "No details to display."

        return SummaryOutput(
            total_actions=0,
            successful_actions=0,
            failed_actions=0,
            skipped_actions=0,
            estimated_recovery=0,
            dry_run=False,
            sensitive_files_protected=0,
            rollback_supported_actions=0,
            rollback_unsupported_actions=0,
            human_readable_report=report,
            errors=[],
        )

    execution_log = node_input.execution_log
    policy = node_input.folder_scope_policy
    sensitive_files = node_input.sensitive_files
    dry_run = node_input.dry_run

    total_actions = len(execution_log)
    successful_actions = 0
    failed_actions = 0
    skipped_actions = 0
    sensitive_files_protected = 0
    rollback_supported_actions = 0
    rollback_unsupported_actions = 0
    estimated_recovery = node_input.estimated_recovery

    errors_list: list[str] = []

    for entry in execution_log:
        # Determine status
        is_skipped = (
            "safety check" in entry.reasoning.lower()
            or "prohibited" in entry.reasoning.lower()
        )
        if entry.status == "success":
            successful_actions += 1
        elif is_skipped:
            skipped_actions += 1
        else:
            failed_actions += 1
            errors_list.append(
                f"Action on '{_clean_path(entry.path, policy)}' ({entry.action_type}) failed: {_clean_reasoning(entry.reasoning)}"
            )

        # Track sensitive protection
        if _is_sensitive_file(entry.path, sensitive_files):
            sensitive_files_protected += 1

        # Track rollback capability
        if entry.rollback_supported:
            rollback_supported_actions += 1
        else:
            rollback_unsupported_actions += 1

    rollback_summary = getattr(node_input, "rollback_summary", None)
    if rollback_summary is not None:
        failed_actions += rollback_summary.failed
        rollback_errors = getattr(node_input, "errors", [])
        for err in rollback_errors:
            errors_list.append(err)

    # Formulate sectioned markdown report
    report_lines: list[str] = []
    if dry_run:
        report_lines.append("Dry Run Mode — No changes were made.\n")

    report_lines.append("## Cleanup Summary")
    report_lines.append(f"- Total Actions: {total_actions}")
    report_lines.append(f"- Successful Actions: {successful_actions}")
    report_lines.append(f"- Failed Actions: {failed_actions}")
    report_lines.append(f"- Skipped Actions: {skipped_actions}")
    report_lines.append("")

    if rollback_summary is not None:
        report_lines.append("## Rollback Summary")
        report_lines.append(f"- Restored Files: {rollback_summary.succeeded}")
        report_lines.append(f"- Unsupported Reversals: {rollback_summary.unsupported}")
        report_lines.append(f"- Rollback Failures: {rollback_summary.failed}")
        report_lines.append(f"- Rollback Dry-Run Status: {rollback_summary.dry_run}")
        report_lines.append("")
        report_lines.append(rollback_summary.human_readable_report)
        report_lines.append("")

    report_lines.append("## Storage Recovery")
    report_lines.append(
        f"- Total Estimated Storage Recovered: {estimated_recovery} bytes"
    )
    report_lines.append("")

    report_lines.append("## Sensitive File Protection")
    if sensitive_files_protected > 0:
        report_lines.append(
            f"- Protected {sensitive_files_protected} sensitive file(s) (details hidden for privacy)"
        )
    else:
        report_lines.append("- No sensitive files were processed.")
    report_lines.append("")

    report_lines.append("## Rollback Capability")
    report_lines.append(f"- Rollback Supported Actions: {rollback_supported_actions}")
    report_lines.append(
        f"- Rollback Unsupported Actions: {rollback_unsupported_actions}"
    )
    report_lines.append("")

    report_lines.append("## Dry-Run Status")
    report_lines.append(f"- Dry-Run Active: {dry_run}")
    report_lines.append("")

    # Detail logs
    if execution_log:
        import json as _json3
        columns = ["Action", "Category", "File Path", "Status", "Details"]
        rows = []
        for entry in execution_log:
            file_is_sensitive = _is_sensitive_file(entry.path, sensitive_files)

            # Category
            reason_lower = entry.reasoning.lower()
            if file_is_sensitive:
                category = "sensitive"
            elif "exact duplicate" in reason_lower or "duplicate" in reason_lower:
                category = "duplicate"
            else:
                ext = os.path.splitext(entry.path)[1].lower()
                if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]:
                    category = "image"
                elif ext in [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"]:
                    category = "document"
                else:
                    category = "other"

            # Action Display
            if file_is_sensitive:
                action_display = "SENSITIVE"
            elif "near duplicate" in reason_lower:
                action_display = "NEAR_DUPLICATE"
            elif category == "duplicate":
                action_display = "DELETE"
            else:
                action_display = entry.action_type.upper()

            # Path
            clean_p = "[Protected Sensitive File]" if file_is_sensitive else _clean_path(entry.path, policy)
            # Details
            clean_reason = "Runtime Safety Check: Sensitive file protection." if file_is_sensitive else _clean_reasoning(entry.reasoning)

            rows.append([
                action_display,
                category,
                clean_p.replace("\\", "/"),
                entry.status.upper(),
                clean_reason
            ])

        table_json = _json3.dumps({
            "__TABLE__": {
                "columns": columns,
                "rows": rows
            }
        })

        report_lines.append("### Action Log Details")
        report_lines.append(f"__TABLE__\n{table_json}")

    human_readable_report = "\n".join(report_lines)

    # Audit log planning / safety overrides if any actions were skipped
    plan_id = hashlib.sha256(node_input.reasoning.encode()).hexdigest()[:8]
    if skipped_actions > 0:
        entry_dict = {
            "node": "SummaryNode",
            "action_type": "plan",
            "path": None,
            "is_sensitive": False,
            "hitl_status": "not_required",
            "result": "skipped",
            "reason": "Safety overrides triggered. Some planned actions were prohibited and skipped.",
            "plan_id": plan_id,
            "safety_override_reason": "Runtime safety checks blocked unsafe operations.",
            "tool_name": "write_log",
        }
        test_tool("write_log", entry=json.dumps(entry_dict))

    return SummaryOutput(
        total_actions=total_actions,
        successful_actions=successful_actions,
        failed_actions=failed_actions,
        skipped_actions=skipped_actions,
        estimated_recovery=estimated_recovery,
        dry_run=dry_run,
        sensitive_files_protected=sensitive_files_protected,
        rollback_supported_actions=rollback_supported_actions,
        rollback_unsupported_actions=rollback_unsupported_actions,
        human_readable_report=human_readable_report,
        errors=errors_list,
    )
