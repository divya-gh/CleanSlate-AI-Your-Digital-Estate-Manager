# Implementation Plan - Agent CLI & Weekly Automation (Refined)

Build the full CleanSlate CLI from scratch to expose all assistant commands, persistent configuration, graph orchestration, and weekly automation toggles.

## Missing Features
1. **Interactive Resume Prompting in standard Python shell**: Standard console input loops lack full back-and-forth multi-turn capability when resume input requirements are complex (e.g. nested lists).
   - **Backlog**: Switch to Textual UI for multi-turn resume flows.
2. **Global scope lock-down database**: The system relies on simple local JSON policy structures without multi-user role partitioning or OS permission validation.
   - **Future**: OS-level ACL validation for folder scope.

## Suggested Enhancements
1. **Config Encryption**: Secure the stored `config.json` and `policy.json` to prevent local tamper access by other unprivileged apps.
   - **Details**: Use Fernet or OS keyring for encryption. Encrypt only sensitive keys (not all config).
2. **Interactive CLI Menu**: Implement a rich terminal visual interface for a premium user experience.
   - **Details**: Use textual for cross-platform TUI. Add folder picker + policy editor.
3. **Audit Log Watcher**: Add a `cleanslate logs --watch` command to stream live audit logs to the terminal as actions execute.
   - **Details**: Use file tailing with watchdog or manual polling. Add `--follow` alias like `tail -f`.

## Proposed Changes

### Configuration Persistence
#### [MODIFY] [config.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/config.py)
- Establish configuration directory at `~/.cleanslate`.
- Implement `ensure_config_dir()`, `ensure_default_config()`, and `ensure_default_policy()`.
- Add schema validation and auto-repair in `load_config()`.
- Implement atomic writing (`_save_file_atomic`) by writing to a temporary file first and atomically replacing the target configuration files.

### Pure Graph Design
#### [MODIFY] [agent.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/agent.py)
- Revert all internal filesystem configuration loading to keep the graph 100% pure and testable.
- Expect configuration parameters (such as `weekly_automation_enabled`) to be passed strictly from CLI wrappers into the `WeeklyOrganizerInput` model payload.

### CLI Implementation
#### [MODIFY] [cli.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/cli.py)
- Support `cleanslate run` (interactive runner).
- Support `cleanslate search "<query>"` (direct `FileDiscoveryNode` execution).
- Support `cleanslate cleanup` (dry-run and execute pipelines with HITL approval).
- Support `cleanslate weekly-run` (now echoes the `weekly_automation_enabled` state to console).
- Add `cleanslate weekly status` / `--status` command support.
- Add `cleanslate config show` and `cleanslate config reset` subcommands.
- Add Semgrep safety exceptions (`nosemgrep`) for localized configuration reads/writes.

### Setup & Safety Gates
#### [MODIFY] [pyproject.toml](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/pyproject.toml)
- Add standard development libraries under `[project.optional-dependencies]` dev group.

#### [MODIFY] [.semgrep/sdd-safety-rules.yaml](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/.semgrep/sdd-safety-rules.yaml)
- Add `no-direct-config-paths` rule to prevent hardcoded configuration paths.
- Add `no-absolute-paths-in-cli-output` rule to enforce redacted paths.

---

## Verification Plan

### Automated Tests
#### [MODIFY] [test_cli.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_cli.py)
- Test `weekly status`, `config show`, and `config reset` commands.
- Test `cleanslate search`, `cleanslate cleanup --dry-run`, and log limits.
- Run tests via `uv run pytest`.
- Verify Semgrep scan via `uv run semgrep scan --config=.semgrep/sdd-safety-rules.yaml --error`.
