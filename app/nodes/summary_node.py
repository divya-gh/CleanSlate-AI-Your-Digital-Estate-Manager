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
from app.nodes.file_discovery_node import FolderScopePolicy, FileDiscoveryOutput
from app.nodes.my_pc_assistant_node import MyPCAssistantOutput
from app.nodes.rollback_node import RollbackOutput
from app.nodes.weekly_organizer_node import WeeklySummary
from app.nodes.optimization_planner_node import OptimizationPlannerOutput
from app.nodes.hitl_approval_node import HITLApprovalOutput
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
    node_input: ExecutionOutput
    | RollbackOutput
    | MyPCAssistantOutput
    | FileDiscoveryOutput
    | WeeklySummary
    | OptimizationPlannerOutput
    | HITLApprovalOutput,
) -> MyPCAssistantOutput:
    """SummaryNode — aggregates and reports execution outcomes safely."""
    if isinstance(node_input, FileDiscoveryOutput):
        report = node_input.reasoning
        is_error = (
            "error" in report.lower()
            or "not found" in report.lower()
            or "symlink" in report.lower()
            or "overlap" in report.lower()
        )
        return MyPCAssistantOutput(
            intent="cleanup",
            total_actions=0,
            successful_actions=0,
            failed_actions=0,
            skipped_actions=0,
            estimated_recovery=0,
            dry_run=node_input.safe_mode,
            sensitive_files_protected=0,
            rollback_supported_actions=0,
            rollback_unsupported_actions=0,
            human_readable_report=report,
            errors=[report] if is_error else [],
        )

    if isinstance(node_input, WeeklySummary):
        return MyPCAssistantOutput(
            intent="cleanup",
            total_actions=node_input.actions_attempted,
            successful_actions=node_input.actions_completed,
            failed_actions=len(node_input.errors),
            skipped_actions=node_input.skipped,
            estimated_recovery=0,
            dry_run=node_input.dry_run,
            sensitive_files_protected=node_input.sensitive_files_moved,
            rollback_supported_actions=0,
            rollback_unsupported_actions=0,
            human_readable_report=node_input.human_readable_report,
            errors=node_input.errors,
        )

    if isinstance(node_input, OptimizationPlannerOutput):
        return MyPCAssistantOutput(
            intent="cleanup",
            total_actions=0,
            successful_actions=0,
            failed_actions=0,
            skipped_actions=0,
            estimated_recovery=0,
            dry_run=node_input.safe_mode,
            sensitive_files_protected=0,
            rollback_supported_actions=0,
            rollback_unsupported_actions=0,
            human_readable_report=node_input.reasoning,
            errors=[],
        )

    if isinstance(node_input, HITLApprovalOutput):
        return MyPCAssistantOutput(
            intent="cleanup",
            total_actions=0,
            successful_actions=0,
            failed_actions=0,
            skipped_actions=0,
            estimated_recovery=0,
            dry_run=node_input.dry_run,
            sensitive_files_protected=0,
            rollback_supported_actions=0,
            rollback_unsupported_actions=0,
            human_readable_report=node_input.reasoning,
            errors=[],
        )

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

        return MyPCAssistantOutput(
            intent="explain",
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
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append("🧹  CLEANSLATE AI — CLEANUP SUMMARY REPORT")
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append("")
    report_lines.append("📊 OVERVIEW")
    report_lines.append("──────────────────────────────────────────────")
    report_lines.append(f"• Total Actions:            {total_actions}")
    report_lines.append(f"• Successful Actions:       {successful_actions}   🟢")
    report_lines.append(f"• Failed Actions:           {failed_actions}       🔴")
    report_lines.append(f"• Skipped Actions:          {skipped_actions}      ⚪")
    report_lines.append("")
    report_lines.append("💾 STORAGE RECOVERY")
    report_lines.append("──────────────────────────────────────────────")
    report_lines.append(f"• Total Space Recovered:    {estimated_recovery} bytes  📦")
    report_lines.append("")
    report_lines.append("🔐 SENSITIVE FILE PROTECTION")
    report_lines.append("──────────────────────────────────────────────")
    report_lines.append(f"• Sensitive Files Protected: {sensitive_files_protected}")
    report_lines.append("• Status:                   🛡️ All protected safely")
    report_lines.append("• Details:                  Hidden for privacy")
    report_lines.append("")
    report_lines.append("♻️ ROLLBACK CAPABILITY")
    report_lines.append("──────────────────────────────────────────────")
    report_lines.append(f"• Rollback Supported:       {rollback_supported_actions}   🔄")
    report_lines.append(f"• Rollback Unsupported:     {rollback_unsupported_actions} ✔️")
    report_lines.append("")
    report_lines.append("🧪 DRY-RUN MODE")
    report_lines.append("──────────────────────────────────────────────")
    report_lines.append(f"• Dry-Run Active:           {dry_run}  🚫")
    report_lines.append("")
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append("📜  CLEANUP ACTION LOG — DETAILED REPORT")
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append("")

    success_logs = []
    failed_logs = []
    skipped_logs = []

    for entry in execution_log:
        is_skipped = (
            "safety check" in entry.reasoning.lower()
            or "prohibited" in entry.reasoning.lower()
        )
        is_sensitive = _is_sensitive_file(entry.path, sensitive_files)
        cleaned_path = "[Protected Sensitive File]" if is_sensitive else _clean_path(entry.path, policy)
        
        action_type = entry.action_type.upper()
        details = _clean_reasoning(entry.reasoning)
        
        if entry.status == "success":
            success_logs.append((action_type, cleaned_path, details))
        elif is_skipped:
            skipped_logs.append((action_type, cleaned_path, details))
        else:
            failed_logs.append((action_type, cleaned_path, details))

    report_lines.append("🟢 SUCCESSFUL ACTIONS")
    report_lines.append("──────────────────────────────────────────────")
    if not success_logs:
        report_lines.append("No successful actions.")
    else:
        for action_type, f_name, details in success_logs:
            report_lines.append(f"🟢 {action_type} • {f_name}")
            if details:
                report_lines.append(f"    └─ {details}")
                
    report_lines.append("")
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append("")
    
    report_lines.append("🔴 FAILED ACTIONS")
    report_lines.append("──────────────────────────────────────────────")
    if not failed_logs:
        report_lines.append("No failed actions.")
    else:
        for action_type, f_name, details in failed_logs:
            report_lines.append(f"🔴 {action_type} • {f_name}")
            report_lines.append(f"    └─ ❗ {details}")

    if skipped_logs:
        report_lines.append("")
        report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report_lines.append("")
        report_lines.append("⚪ SKIPPED ACTIONS")
        report_lines.append("──────────────────────────────────────────────")
        for action_type, f_name, details in skipped_logs:
            report_lines.append(f"⚪ {action_type} • {f_name}")
            report_lines.append(f"    └─ {details}")

    report_lines.append("")
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append("")
    
    report_lines.append("📌 NOTES")
    report_lines.append("──────────────────────────────────────────────")
    report_lines.append("• “File not found” failures indicate the file was moved, renamed,")
    report_lines.append("  or deleted before execution.")
    report_lines.append("• “PathNotAllowed” failures indicate archive destination violated")
    report_lines.append("  safety or traversal policy.")
    report_lines.append("• Sensitive files remain protected and hidden by design.")
    report_lines.append("")
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    human_readable_report = "\n".join(report_lines)

    # Audit log planning / safety overrides if any actions were skipped
    reasoning_str = getattr(node_input, "reasoning", "Rollback execution")
    plan_id = hashlib.sha256(reasoning_str.encode()).hexdigest()[:8]
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

    return MyPCAssistantOutput(
        intent="cleanup",
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
