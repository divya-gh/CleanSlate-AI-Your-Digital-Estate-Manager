import argparse
import asyncio
import json
import os
import sys

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent
from app.config import (
    CONFIG_DIR,
    DEFAULT_CONFIG,
    load_config,
    load_policy,
    reset_policy,
    save_config,
    save_policy,
)
from app.mcp_tools.registry import list_tools, normalize_name, test_tool
from app.nodes.classification_node import classification_node
from app.nodes.duplicate_detection_node import duplicate_detection_node
from app.nodes.execution_node import ExecutionOutput, execution_node
from app.nodes.file_discovery_node import (
    FileDiscoveryInput,
    FolderScopePolicy,
    file_discovery_node,
)
from app.nodes.folder_scope_node import FolderScopeInput, folder_scope_node
from app.nodes.hitl_approval_node import HITLApprovalOutput
from app.nodes.optimization_planner_node import optimization_planner_node
from app.nodes.rollback_node import rollback_node
from app.nodes.sensitive_detection_node import sensitive_detection_node
from app.nodes.summary_node import summary_node
from app.nodes.weekly_organizer_node import WeeklyOrganizerInput, weekly_organizer_node

LAST_EXEC_FILE = CONFIG_DIR / "last_execution.json"


def cmd_run():
    """Starts the MyPCAssistantNode in interactive mode."""
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(
        user_id="cli_user", app_name="cleanslate"
    )
    runner = Runner(
        agent=root_agent, session_service=session_service, app_name="cleanslate"
    )

    print("CleanSlate AI My PC Assistant CLI (Interactive Mode)")
    print("Type your message below. Type 'exit' or 'quit' to exit.")
    print("-" * 50)

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.strip().lower() in ("exit", "quit"):
                break
            if not user_input.strip():
                continue

            message = types.Content(
                role="user", parts=[types.Part.from_text(text=user_input)]
            )

            events = runner.run(
                new_message=message,
                user_id="cli_user",
                session_id=session.id,
            )

            for event in events:
                if hasattr(event, "interrupt_id") and event.interrupt_id:
                    print(f"\n[INTERRUPT: {event.interrupt_id}]")
                    print(event.message)
                    reply = input("Reply: ")
                    events = runner.run(
                        new_message=None,
                        user_id="cli_user",
                        session_id=session.id,
                        resume_inputs={event.interrupt_id: reply},
                    )
                    for rev in events:
                        if rev.content and rev.content.parts:
                            for part in rev.content.parts:
                                if part.text:
                                    print(part.text, end="", flush=True)
                    print()
                elif event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(part.text, end="", flush=True)
            print()

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


def cmd_search(query, path_opt=None, json_opt=False):
    """Triggers the search mode using FileDiscoveryNode under the hood."""
    policy_dict = load_policy()
    if policy_dict:
        # Convert string timestamp back to datetime if necessary or ignore for Pydantic v2
        policy = FolderScopePolicy.model_validate(policy_dict)
    else:
        # Default allowed is current directory
        policy = FolderScopePolicy(allowed_paths=[os.getcwd()])

    if path_opt:
        abs_path = os.path.abspath(path_opt)
        policy.allowed_paths = [abs_path]

    discovery_input = FileDiscoveryInput(folder_scope_policy=policy, search_query=query)
    try:
        event = file_discovery_node(discovery_input)
        output = event.output
        inventory = output.file_inventory

        if json_opt:
            res = [item.model_dump() for item in inventory]
            print(json.dumps(res, indent=2))
        else:
            if not inventory:
                print("No files found matching the search query.")
            else:
                print(f"Discovered {len(inventory)} matching files:")
                for item in inventory:
                    print(f"- {item.path} ({item.size} bytes)")
    except Exception as e:
        print(f"Error during search: {e}")


def cmd_cleanup(dry_run=False):
    """Triggers the interactive cleanup workflow."""
    policy_dict = load_policy()
    if policy_dict:
        policy = FolderScopePolicy.model_validate(policy_dict)
    else:
        print("Folder scope is not configured yet. Let's configure it now:")
        allowed_str = input(
            "Please enter the folders you allow the assistant to scan (separated by commas):\n> "
        )
        blocked_str = input(
            "Please enter any folders the assistant must never touch (separated by commas, or press Enter to skip):\n> "
        )

        async def run_scope():
            from google.adk.agents.context import Context

            ctx = Context(
                app_name="cleanslate",
                user_id="cli_user",
                session_id="cli_session",
                resume_inputs={
                    "allowed_paths": allowed_str,
                    "blocked_paths": blocked_str,
                },
            )
            node_input = FolderScopeInput(cleanup_intent=True)
            events = []
            async for ev in folder_scope_node(ctx, node_input):
                events.append(ev)
            return events

        loop = asyncio.get_event_loop()
        events = loop.run_until_complete(run_scope())

        last_event = events[-1]
        if (
            hasattr(last_event, "output")
            and last_event.output
            and last_event.output.folder_scope_policy
        ):
            policy = last_event.output.folder_scope_policy
            save_policy(policy.model_dump())
            print("Folder scope saved to policy.json.")
        else:
            print("Folder scope validation failed:")
            if hasattr(last_event, "output") and last_event.output.validation_errors:
                for err in last_event.output.validation_errors:
                    print(f" - {err}")
            sys.exit(1)

    # Run remaining workflow pipeline
    discovery_input = FileDiscoveryInput(folder_scope_policy=policy)
    disc_event = file_discovery_node(discovery_input)
    classify_event = classification_node(disc_event.output)
    dedupe_output = duplicate_detection_node(classify_event.output)
    sensitive_event = sensitive_detection_node(dedupe_output)
    planner_event = optimization_planner_node(sensitive_event.output)
    planner_output = planner_event.output

    if planner_event.actions.route == "no_actions":
        print("No actions recommended. PC is already clean!")
        exec_output = ExecutionOutput(
            execution_log=[],
            reasoning="No actions recommended",
            folder_scope_policy=planner_output.folder_scope_policy,
            sensitive_files=planner_output.sensitive_files,
            dry_run=dry_run,
        )
        summary_output = summary_node(exec_output)
        print(summary_output.human_readable_report)
        return

    print("\n--- Proposed Optimization Plan ---")
    for action in planner_output.actions:
        print(
            f"[{action.action_type.upper()}] {action.path} -> {action.reasoning} (Recovery: {action.estimated_space_recovered} bytes)"
        )
    print(
        f"Estimated space recovered: {planner_output.estimated_space_recovered} bytes"
    )

    confirm = input("\nDo you approve this cleanup plan? (yes/no): ").strip().lower()
    if confirm in ("yes", "y"):
        exec_input = HITLApprovalOutput(
            approved_actions=planner_output.actions,
            folder_scope_policy=planner_output.folder_scope_policy,
            sensitive_files=planner_output.sensitive_files,
            dry_run=dry_run,
            reasoning="User approved via CLI cleanup",
        )
        exec_event = execution_node(exec_input)
        exec_output = exec_event.output

        # Save last execution log for rollback
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(LAST_EXEC_FILE, "w", encoding="utf-8") as f:
                json.dump(exec_output.model_dump(), f, indent=2, default=str)
        except Exception:
            pass

        summary_output = summary_node(exec_output)
        print("\n--- Execution Summary ---")
        print(summary_output.human_readable_report)
    else:
        print("Cleanup aborted by user.")


def cmd_weekly_run():
    """Runs the weekly organizer automation."""
    config = load_config()
    enabled = config.get("weekly_automation_enabled", False)
    print(f"Checking weekly automation state: Enabled={enabled}")
    if not enabled:
        print("Weekly automation disabled. Enable it with: cleanslate weekly enable")
        sys.exit(0)

    policy_dict = load_policy()
    if not policy_dict:
        print(
            "Error: No pre-approved folder scope policy found. Run 'cleanslate cleanup' first to set one."
        )
        sys.exit(1)

    policy = FolderScopePolicy.model_validate(policy_dict)

    organizer_input = WeeklyOrganizerInput(
        pubsub_event={},
        weekly_automation_enabled=True,
        folder_scope_policy=policy,
        dry_run=False,
    )

    event = weekly_organizer_node(organizer_input)
    if event.actions.route == "run":
        discovery_input = event.output
        disc_event = file_discovery_node(discovery_input)
        classify_event = classification_node(disc_event.output)
        dedupe_output = duplicate_detection_node(classify_event.output)
        sensitive_event = sensitive_detection_node(dedupe_output)
        planner_event = optimization_planner_node(sensitive_event.output)
        planner_output = planner_event.output

        if planner_event.actions.route == "execute":
            exec_input = HITLApprovalOutput(
                approved_actions=planner_output.actions,
                folder_scope_policy=planner_output.folder_scope_policy,
                sensitive_files=planner_output.sensitive_files,
                dry_run=False,
                reasoning="Weekly automation run",
            )
            exec_event = execution_node(exec_input)
            exec_output = exec_event.output

            # Save last execution log for rollback
            try:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                with open(LAST_EXEC_FILE, "w", encoding="utf-8") as f:
                    json.dump(exec_output.model_dump(), f, indent=2, default=str)
            except Exception:
                pass

            summary_output = summary_node(exec_output)
            print(summary_output.human_readable_report)
        else:
            exec_output = ExecutionOutput(
                execution_log=[],
                reasoning="No actions recommended",
                folder_scope_policy=planner_output.folder_scope_policy,
                sensitive_files=planner_output.sensitive_files,
                dry_run=False,
            )
            summary_output = summary_node(exec_output)
            print(summary_output.human_readable_report)
    else:
        print(event.output.human_readable_report)


def cmd_logs(limit=None, json_opt=False):
    """Reads and outputs audit logs."""
    log_path = os.environ.get("CLEANSLATE_LOG_PATH", "logs/audit.log")
    if not os.path.exists(log_path):
        if json_opt:
            print("[]")
        else:
            print("No logs found.")
        return

    try:
        with open(
            log_path, encoding="utf-8"
        ) as f:  # nosemgrep: no-file-content-reading, file-ops-must-use-folder-scope
            lines = f.readlines()  # nosemgrep: no-file-content-reading

        entries = []
        for line in lines:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass

        if limit:
            entries = entries[-limit:]

        if json_opt:
            print(json.dumps(entries, indent=2))
        else:
            print(f"Showing last {len(entries)} log entries:")
            for entry in entries:
                path_str = f" | Path: {entry.get('path')}" if entry.get("path") else ""
                print(
                    f"[{entry.get('timestamp')}] Node: {entry.get('node')} | Action: {entry.get('action_type')} | Result: {entry.get('result')}{path_str}"
                )
    except Exception as e:
        print(f"Error reading logs: {e}")


def cmd_rollback():
    """Triggers the rollback workflow to undo the last execution."""
    if not LAST_EXEC_FILE.exists():
        print("No execution history found to roll back.")
        return

    try:
        with open(
            LAST_EXEC_FILE, encoding="utf-8"
        ) as f:  # nosemgrep: no-file-content-reading, file-ops-must-use-folder-scope
            data = json.load(f)

        rb_input = ExecutionOutput(
            execution_log=data.get("execution_log", []),
            folder_scope_policy=data.get("folder_scope_policy"),
            sensitive_files=data.get("sensitive_files", []),
            dry_run=False,
        )

        rb_event = rollback_node(rb_input)
        summary = rb_event.rollback_summary

        print("\n--- Rollback Summary ---")
        print(summary.human_readable_report)

        if LAST_EXEC_FILE.exists():
            LAST_EXEC_FILE.unlink()  # nosemgrep: no-direct-file-deletes

    except Exception as e:
        print(f"Error during rollback: {e}")


def cmd_scope_reset():
    """Resets folder scope policy."""
    reset_policy()
    print(
        "Folder scope policy reset successfully. Next cleanup will require re-configuration."
    )


def cmd_weekly_enable():
    """Enables weekly automation."""
    config = load_config()
    config["weekly_automation_enabled"] = True
    save_config(config)
    print("Weekly automation enabled.")


def cmd_weekly_disable():
    """Disables weekly automation."""
    config = load_config()
    config["weekly_automation_enabled"] = False
    save_config(config)
    print("Weekly automation disabled.")


def cmd_weekly_status():
    """Prints the weekly automation status."""
    config = load_config()
    enabled = config.get("weekly_automation_enabled", False)
    status_str = "ENABLED" if enabled else "DISABLED"
    print(f"Weekly automation status: {status_str}")


def cmd_config_show():
    """Prints the current configuration."""
    config = load_config()
    print("Current Configuration:")
    print(json.dumps(config, indent=2))


def cmd_config_reset():
    """Resets the configuration to default settings."""
    save_config(DEFAULT_CONFIG)
    print("Configuration reset to default settings.")


# ---------------------------------------------------------------------------
# Developer tool commands (registry-only, no direct filesystem access)
# ---------------------------------------------------------------------------


def _sanitize_path(raw: str) -> str:
    """Strips absolute prefix from a path string for CLI display.

    Converts absolute paths to parent_folder/filename form so that the CLI
    never exposes absolute filesystem paths in its output.
    Complies with the no-absolute-paths-in-cli-output Semgrep rule.
    """
    if not isinstance(raw, str):
        return str(raw)
    # Only sanitize strings that look like filesystem paths
    if os.sep in raw or "/" in raw or "\\" in raw:
        norm = os.path.normpath(raw)
        parts = norm.split(os.sep)
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
        return parts[-1]
    return raw


def _sanitize_result_for_display(obj) -> object:
    """Recursively sanitize paths inside a dict/list for safe human-readable display."""
    if isinstance(obj, dict):
        return {k: _sanitize_result_for_display(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_result_for_display(i) for i in obj]
    if isinstance(obj, str):
        return _sanitize_path(obj)
    return obj


def cmd_tools_list(json_opt: bool = False) -> None:
    """Lists all registered MCP tools from the registry."""
    tools = list_tools()
    if json_opt:
        print(json.dumps(tools, indent=2))
        return

    print(f"Registered MCP tools ({len(tools)}):")
    print("-" * 50)
    for tool in tools:
        required_keys = tool["input_schema"].get("required", [])
        props = list(tool["input_schema"].get("properties", {}).keys())
        print(f"  {tool['name']}")
        print(f"    Description : {tool['description']}")
        print(f"    Inputs      : {', '.join(props) if props else '(none)'}")
        print(f"    Required    : {', '.join(required_keys) if required_keys else '(none)'}")
        print(f"    Version     : {tool.get('version', '1.0')}")
        print()


def cmd_tools_test(tool_name: str, raw_args: list[str], json_opt: bool = False) -> None:
    """Executes a single MCP tool through registry.test_tool() for developer debugging.

    All safety and policy checks inside the tool are preserved — this command
    never bypasses MCP enforcement.
    """
    # Normalize the tool name using registry rules
    norm = normalize_name(tool_name)

    # Parse key=value pairs from CLI args
    parsed: dict = {}
    for token in raw_args:
        if "=" not in token:
            print(
                json.dumps(
                    {
                        "error": {
                            "type": "SchemaError",
                            "message": f"Invalid argument format '{token}'. Expected key=value.",
                            "details": {"token": token},
                        }
                    },
                    indent=2,
                )
            )
            return
        k, _, v = token.partition("=")
        parsed[k.strip()] = v.strip()

    # Dispatch through the registry — never direct filesystem calls
    result = test_tool(norm, **parsed)

    if json_opt:
        print(json.dumps(result, indent=2))
        return

    if "error" in result:
        err = result["error"]
        print(f"[ERROR] {err.get('type', 'ToolError')}: {err.get('message', '')}")
        details = err.get("details", {})
        if details:
            # Sanitize details before display to prevent absolute path leakage
            sanitized = _sanitize_result_for_display(details)
            print("Details:")
            for k, v in sanitized.items():
                print(f"  {k}: {v}")
    else:
        print(f"[SUCCESS] Tool '{norm}' executed.")
        # Sanitize result paths before display; --json mode is raw developer output
        sanitized_result = _sanitize_result_for_display(result.get("result", result))
        print(json.dumps(sanitized_result, indent=2))


def main():
    parser = argparse.ArgumentParser(description="CleanSlate AI - My PC Assistant CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run
    subparsers.add_parser("run", help="Start MyPCAssistantNode in interactive mode")

    # search
    search_parser = subparsers.add_parser(
        "search", help="Trigger MyPCAssistantNode in search mode"
    )
    search_parser.add_argument("query", type=str, help="Search query")
    search_parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )
    search_parser.add_argument(
        "--path", type=str, default=None, help="Folder path to restrict search"
    )

    # cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Trigger cleanup workflow")
    cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate actions in dry-run mode",
    )

    # weekly-run
    subparsers.add_parser("weekly-run", help="Run automated weekly organizer")

    # logs
    logs_parser = subparsers.add_parser("logs", help="Read audit logs")
    logs_parser.add_argument(
        "--limit", type=int, default=None, help="Limit output to last N logs"
    )
    logs_parser.add_argument(
        "--json", action="store_true", help="Output logs in JSON format"
    )

    # rollback
    subparsers.add_parser(
        "rollback", help="Trigger RollbackNode to undo last cleanup batch"
    )

    # scope
    scope_parser = subparsers.add_parser(
        "scope", help="Manage folder scope configuration"
    )
    scope_subparsers = scope_parser.add_subparsers(
        dest="scope_command", help="Scope subcommand"
    )
    scope_subparsers.add_parser("reset", help="Clear stored folder scope policy")

    # config
    config_parser = subparsers.add_parser(
        "config", help="Manage persistent configurations"
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Config subcommand"
    )
    config_subparsers.add_parser("show", help="Show current configuration")
    config_subparsers.add_parser("reset", help="Reset configuration to defaults")

    # weekly
    weekly_parser = subparsers.add_parser("weekly", help="Weekly automation control")
    weekly_parser.add_argument(
        "--status", "-s", action="store_true", help="Print weekly automation status"
    )
    weekly_subparsers = weekly_parser.add_subparsers(
        dest="weekly_command", help="Weekly subcommand"
    )
    weekly_subparsers.add_parser("enable", help="Enable weekly automation")
    weekly_subparsers.add_parser("disable", help="Disable weekly automation")
    weekly_subparsers.add_parser("status", help="Print weekly automation status")

    # tools (developer commands)
    tools_parser = subparsers.add_parser(
        "tools", help="Developer MCP tool registry commands"
    )
    tools_parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )
    tools_subparsers = tools_parser.add_subparsers(
        dest="tools_command", help="Tools subcommand"
    )
    # tools list
    tools_list_parser = tools_subparsers.add_parser(
        "list", help="List all registered MCP tools"
    )
    tools_list_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )
    # tools test
    tools_test_parser = tools_subparsers.add_parser(
        "test", help="Execute a single MCP tool for developer debugging"
    )
    tools_test_parser.add_argument("tool_name", type=str, help="Name of the tool to test")
    tools_test_parser.add_argument(
        "args",
        nargs="*",
        metavar="key=value",
        help="Tool arguments in key=value format",
    )
    tools_test_parser.add_argument(
        "--json", action="store_true", help="Output result in JSON format"
    )

    args = parser.parse_args()

    if args.command == "run":
        cmd_run()
    elif args.command == "search":
        cmd_search(args.query, args.path, args.json)
    elif args.command == "cleanup":
        cmd_cleanup(args.dry_run)
    elif args.command == "weekly-run":
        cmd_weekly_run()
    elif args.command == "logs":
        cmd_logs(args.limit, args.json)
    elif args.command == "rollback":
        cmd_rollback()
    elif args.command == "scope":
        if args.scope_command == "reset":
            cmd_scope_reset()
        else:
            scope_parser.print_help()
    elif args.command == "config":
        if args.config_command == "show":
            cmd_config_show()
        elif args.config_command == "reset":
            cmd_config_reset()
        else:
            config_parser.print_help()
    elif args.command == "weekly":
        if args.weekly_command == "enable":
            cmd_weekly_enable()
        elif args.weekly_command == "disable":
            cmd_weekly_disable()
        elif args.weekly_command == "status" or args.status:
            cmd_weekly_status()
        else:
            weekly_parser.print_help()
    elif args.command == "tools":
        json_flag = getattr(args, "json", False)
        if args.tools_command == "list":
            cmd_tools_list(json_opt=json_flag)
        elif args.tools_command == "test":
            cmd_tools_test(args.tool_name, args.args, json_opt=json_flag)
        else:
            tools_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
