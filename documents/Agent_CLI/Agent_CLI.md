# 💻 Agent CLI in CleanSlate AI — Your Digital Estate Manager 
 **"AI Chief of Staff for Digital Organization and Storage Management."**
 
---
### The CleanSlate CLI is the primary interface for interacting with the agent locally. It provides:  
- 🧭 **User commands** (search, cleanup, weekly automation)
- 🛠️ **Developer commands** (graph visualization, debugging)
- 🔐 **Safety controls** (safe mode, dry run, rollback)
- ⚙️ **Persistent configuration** (atomic config + policy storage)

This CLI is built from scratch using the [**Agent CLI Spec**](../SPECS/Agent_CLI_SPEC_V2.md), with full integration into the **ADK graph** and **WeeklyOrganizerNode** for ambient running.

----------------------------
### 🧭 Available Commands
----------------------------

#### 1. User Commands:

##### ▶️ cleanslate run
•	Starts an interactive multi turn session with the agent.

##### 🔍 cleanslate search `"< query > "`
•	Searches files using metadata only discovery. Options:
o	--json
o	--path <folder>

##### 🧹 cleanslate cleanup
**Runs the full cleanup pipeline with:**
•	FolderScopeNode
•	Classification
•	Sensitive detection
•	HITL approval
•	ExecutionNode

##### SummaryNode
•	Supports:
```
	--dry-run (no actions executed)
```

##### 📅 cleanslate weekly-run
Runs the WeeklyOrganizerNode in safe mode, but only if enabled.
•	If disabled, prints:
```
	“Weekly automation disabled. Enable it with: cleanslate weekly enable”
```

## 2. Weekly Automation Controls
**These commands manage the persistent config flag stored in:**
```
~/.cleanslate/config.json

```

#### 🟢 cleanslate weekly enable
•	Enables weekly automation.

#### 🔴 cleanslate weekly disable
•	Disables weekly automation.

📊 cleanslate weekly status
•	Shows whether weekly automation is enabled or disabled.

## 3. Configuration Commands

#### ⚙️ cleanslate config show
•	Displays current configuration (sanitized).

#### ♻️ cleanslate config reset
•	Resets configuration to defaults.	


## 4. Safety & Control Commands

#### 🧪 cleanslate dry-run
•	Runs the cleanup pipeline without executing actions.


#### 🛡️ cleanslate safe-mode on/off
•	Globally restricts destructive actions.

#### 📜 cleanslate logs
•	Views redacted audit logs. Options:
•	--limit N
•	--json

#### 🔄 cleanslate rollback
•	Reverses the last cleanup batch using RollbackNode.

#### 🗂️ Configuration & Policy System
**CleanSlate uses atomic configuration writes to ensure safety:**
•	config.json → weekly automation, safe-mode defaults
•	policy.json → allowed/blocked folder scope

#### Features:
•	Auto repair missing keys
•	Atomic writes via temp file swap
•	No absolute paths printed (Semgrep enforced)
•	No hardcoded config paths (Semgrep enforced)

#### 🧠 Graph Integration
**The CLI injects configuration into the ADK graph:**
•	weekly_automation_enabled
•	safe_mode
•	allow_deletes
•	allow_compress
•	allow_moves
•	allow_archives
The graph itself remains pure, with no file I/O.

#### 🔐 Safety Guarantees
**The CLI enforces:**
•	Metadata only classification
•	No file-content reads
•	No sensitive file deletion
•	HITL approval for destructive actions
•	Rollback for all reversible actions
•	Redacted audit logs
•	Semgrep static safety gates

#### 🧪 Testing

**All CLI features are covered in:**
```
tests/test_cli.py
```

##### Includes:
•	Weekly enable/disable
•	Weekly-run respecting flag
•	Search
•	Cleanup dry-run
•	Logs
•	Config show/reset
•	All 75 tests pass.

## 🟦 Why This Matters
**This CLI transforms CleanSlate from a codebase into a real, usable product:**
•	Safe
•	Testable
•	Configurable
•	Extensible
•	Capstone ready

**It demonstrates mastery of:**
•	ADK 2.0
•	Antigravity
•	Semgrep
•	Agent lifecycle
•	Safety engineering
•	CLI design
•	Persistent configuration
•	Weekly automation workflows
