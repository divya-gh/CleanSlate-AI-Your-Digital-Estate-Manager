# 📘 Agent CLI Spec — CleanSlate PC Assistant

This document defines the CLI command-line interface for the CleanSlate PC Assistant.

## 1. Syntax Overview
All commands follow the pattern:
```bash
cleanslate <command> [options]
```

---

## 2. Commands List

### 2.1 cleanslate run
- **Description**: Starts `MyPCAssistantNode` in interactive conversational mode.
- **Workflow**: Prompts the user for query input in a terminal loop, processes outputs via the ADK Runner, and handles intermediate Human-in-the-loop (HITL) requests or interrupts.

### 2.2 cleanslate search "<query>" [--json] [--path <folder>]
- **Description**: Triggers search intent using `FileDiscoveryNode` under the hood.
- **Rules**: Respects the configured folder scope policy. Prints search inventory matching the case-insensitive glob query. If `--json` is specified, outputs JSON format.

### 2.3 cleanslate cleanup [--dry-run]
- **Description**: Triggers the interactive cleanup workflow.
- **Workflow**: Loads the pre-configured folder scope policy (or prompts the user for it if missing using `FolderScopeNode`). Runs the planning pipeline, requires interactive HITL confirmation, runs `ExecutionNode` and `SummaryNode`.

### 2.4 cleanslate weekly-run
- **Description**: Runs automated weekly cleanup in safe mode.
- **Verification**:
  - Checks if `weekly_automation_enabled` is set to `true` in `~/.cleanslate/config.json`.
  - If `false`, prints: `"Weekly automation disabled. Enable it with: cleanslate weekly enable"` and exits.
  - If `true`, runs `WeeklyOrganizerNode` and executes allowed safe moves/archives, presenting a final `SummaryNode` report.

### 2.5 cleanslate logs [--limit N] [--json]
- **Description**: Reads from `CLEANSLATE_LOG_PATH` (defaults to `logs/audit.log`).
- **Rules**: Outputs log entries. Redacts absolute paths to parent directory + filename or `<sensitive file>`. Supports limiting logs to the last `N` entries or outputting as JSON.

### 2.6 cleanslate rollback
- **Description**: Triggers `RollbackNode` using execution history saved from the most recent run in `~/.cleanslate/last_execution.json`.

### 2.7 cleanslate scope reset
- **Description**: Clears the stored folder scope policy (`~/.cleanslate/policy.json`).

---

## 3. Weekly Automation Control Commands

### 3.1 cleanslate weekly enable
- **Action**: Loads the configuration, sets `weekly_automation_enabled = true`, saves the configuration, and prints `"Weekly automation enabled."`

### 3.2 cleanslate weekly disable
- **Action**: Loads the configuration, sets `weekly_automation_enabled = false`, saves the configuration, and prints `"Weekly automation disabled."`
