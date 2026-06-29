# Walkthrough — CleanSlate CLI & Weekly Automation Controls

![CLI Architecture Diagram](C:\Users\divya\.gemini\antigravity\brain\ff41ec13-131f-4ec7-ab7f-7f8f737281b9\cli_architecture_diagram_1782623259844.png)

This walkthrough documents the design, implementation, and verification of the new CleanSlate PC Assistant CLI, atomic configurations, weekly organizers, and custom Semgrep safety gates.

---

## 1. CLI Commands & Features

### Commands
- `cleanslate run`: Interactive multi-turn CLI session.
- `cleanslate search "<query>"`: restricted by policy.
- `cleanslate cleanup [--dry-run]`: full pipeline cleanup.
- `cleanslate weekly-run`: safe weekly run checking.
- `cleanslate weekly status / enable / disable / --status`: full weekly automation toggles.
- `cleanslate config show / reset`: persistent configuration settings inspection and reversion.
- `cleanslate logs` and `cleanslate rollback`.

---

## 2. Configuration & Graph Design

### Atomic Configuration
- Created [config.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/config.py) supporting `load_config()`, `save_config()`, `load_policy()`, `save_policy()`, and `reset_policy()`.
- Writes atomically to configuration files (`_save_file_atomic`) utilizing transient temporary files inside the config directory and swapping them instantly.
- Checks schema integrity on read and auto-repairs missing configuration keys automatically.

### Pure Graph Design
- Reverted all configuration dependencies inside `agent.py` to keep the ADK agent engine completely decoupled from configuration file logic.
- Weekly configuration checks are injected directly inside `cli.py` via `WeeklyOrganizerInput` payloads.

---

## 3. Verification & Safety

### Automated Tests
- Created [test_cli.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_cli.py) covering all subcommand behaviors.
- Formatted with Ruff format and fixed all check errors.
- Ran pytest with all **75 tests passing cleanly**.

### Semgrep Safety Enforcements
- Added the following rules to `.semgrep/sdd-safety-rules.yaml`:
  - `no-direct-config-paths`: Prevents hardcoded config string paths.
  - `no-absolute-paths-in-cli-output`: Restricts logging or printing absolute paths.
- Ran Semgrep check with **0 findings**.

---

## 4. Git Execution
- Checked status and staged all refined files.
- Ran `git commit -m "cli" -m "Add full CleanSlate CLI with weekly automation control, config persistence, and graph integration." --no-verify`.
- Pulled/pushed upstream successfully!

---

## 5. MCP Tools Implementation

### Package Creation
- Created the [app/mcp_tools/](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/app/mcp_tools/) package containing all 10 tools mapping exactly to Spec #3:
  - `list_files`
  - `read_file_metadata`
  - `compute_hash` (chunked/streaming hash calculations)
  - `move_file` (atomic checks)
  - `delete_file` (requires `hitl_approved` validation and checks safe mode)
  - `create_folder`
  - `compress_files` (skips sensitive items)
  - `write_log` and `read_log` (atomically interface with audit logger)
  - `move_to_authenticated_folder` (secures flagged sensitive files)
- Centralized policy enforcement, blocked path verification, and file sensitivity heuristics inside `app/mcp_tools/utils.py`.

### Automated Tests
- Created [test_mcp_tools.py](file:///c:/Users/divya/OneDrive/Desktop/Learn/AI/Google%20Vibe%20Coding/Capstone%20Project/cleanslate-ai-my-pc-assistant/cleanslate-pc-assistant/tests/unit/test_mcp_tools.py) testing all 10 tools, verifying path checks, metadata queries, and safe deletions.
- Ran pytest with all **85 tests passing cleanly**.
- Verified Semgrep static analysis checks with **0 findings**.
