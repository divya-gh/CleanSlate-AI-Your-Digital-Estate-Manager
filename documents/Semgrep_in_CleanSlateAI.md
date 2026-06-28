
# What is Semgrep ?
`Semgrep` is a **lightweight static analysis engine** that scans our code for:

•	security vulnerabilities
•	unsafe patterns
•	bad API usage
•	hardcoded secrets
•	insecure file operations
•	dangerous subprocess calls
•	unsafe path handling
•	ANY custom rule you define

**Mental Model:**   `“grep + AST + security brain” ` that we can program with your own rules.

It’s fast, local, and perfect for agentic codebases where safety must be enforced before execution.


## Implimenting Semgrep in CleanSlateAI - My PC Assistant
    Because runtime safety ≠ static safety.
Semgrep guarantee that `unsafe code can never enter our repo` in the first place.

### Analysis:

**Since CleanSlateAI** :
•	moves files
•	deletes files
•	touches user directories
•	handles sensitive data
•	uses Gemini API keys
•	runs automated weekly tasks
•	performs rollback
•	executes actions on the filesystem

##### a simple code  ` os.remove(path)` could bypass:
•	HITL
•	safe_mode
•	rollback
•	sensitive file protection
•	folder scope  And you’d never know until a user loses data.

#### Semgrep prevents that with static safety. Semgrep enforces rules like:

❌ No hardcoded API keys
❌ No direct os.remove() without safety wrapper
❌ No direct shutil.rmtree()
❌ No writing outside allowed_paths
❌ No unvalidated user input passed to file operations
❌ No direct subprocess calls
❌ No unsafe path joins
❌ No absolute paths in logs

### And we can enforce:

✔ All file operations must go through ExecutionNode
✔ All sensitive files must be routed to Authenticated folder
✔ All deletes must be guarded by HITL
✔ All planner actions must include rollback metadata

**Semgrep** is the perfect companion to our **ADK + Antigravity + TDD workflow.**


## Semgrep Rules Used in CleanSlate AI
Below is the complete set of custom Semgrep rules enforced in the project.

**1. Pre commit (local gate)**
Block insecure code before it ever leaves your machine.

•	.pre-commit-config.yaml with Semgrep hook
•	Semgrep runs with --error
•	Pre commit blocks unsafe code
•	ran pre-commit run --all-files
•	committed with "sec rules" after Semgrep passed


**2. Antigravity remediation loop**

When Semgrep fails, Antigravity can:
•	read the failure
•	fix the code
•	re-run tests
•	re-run Semgrep
•	retry the commit
✔ Antigravity is now a automated self healing layer.


**1.Hardcoded secrets**

We have Semgrep rules for:
•	no file content reading
•	no content upload to LLM
•	no sensitive data in logs


**2. Unsafe file operations**

**We have:**
•	Semgrep rule blocking unsafe file ops
•	ExecutionNode is the only allowed boundary
•	# nosemgrep justified only in ExecutionNode
•	FolderScopeNode enforces allowed_paths


### 1. no-file-content-reading
Purpose: Enforce metadata‑only classification and prevent any file‑content access.

Blocks:

open(path, "r")

open(path, "rb")

.read(), .readlines()

PyPDF2.PdfReader(path)

Any attempt to extract previews or text

Why:  
Security Spec Boundary 4 states:

“The agent must never read file contents. Only metadata is allowed.”

This rule guarantees that no code path can ever read file contents, even accidentally.

2. 🚫 no-content-upload-to-llm
Purpose: Prevent accidental leakage of file contents to Gemini or any LLM.

Blocks:

client.generate_content(open(...))

Passing any variable derived from file contents to LLM calls

Why:  
LLMs must receive metadata only, never raw content.
This rule enforces the zero‑content privacy model.

3. 🚫 no-sensitive-data-in-logs
Purpose: Ensure logs never contain sensitive paths, filenames, or raw data.

Blocks:

Any write_log(data) call that isn’t wrapped in redact(data)

Why:  
Security Spec Section 8 requires:

“Logs must never contain sensitive data or full paths.”

This rule prepares the system for structured audit logging.

4. 🚫 file-ops-must-use-folder-scope
Purpose: Prevent unsafe file operations outside ExecutionNode.

Blocks:

os.remove(path)

shutil.rmtree(path)

shutil.move(src, dst)

shutil.copy(src, dst)

Allows only:

Operations routed through ExecutionNode (authorized boundary)

Why:  
This enforces:

FolderScopeNode

HITLApprovalNode

RollbackNode

SensitiveDetectionNode

No file operation can bypass safety gates.

5. 🚫 no-system-folder-access
Purpose: Enforce Security Spec Boundary 5.

Blocks access to:

/usr, /etc, /bin, /var

C:\Windows

C:\Program Files

C:\Users\<user>\AppData

Why:  
The agent must never touch system directories.

6. 🚫 no-unsafe-path-joins
Purpose: Prevent path traversal and unsafe path construction.

Blocks:

os.path.join(a, b) when not using safe_join

Why:  
Ensures all paths are validated against allowed_paths and blocked_paths.

7. 🚫 rollback-required-for-destructive-actions
Purpose: Guarantee reversibility of destructive actions.

Blocks:

Any CleanupAction(action_type="delete") without rollback_supported=True

Why:  
Security Spec Section 7 requires:

“If execution fails → RollbackNode must undo all changes.”

This rule ensures rollback metadata is always present.

🧩 Justified # nosemgrep Exceptions
Only two locations in the entire codebase are allowed to bypass Semgrep:

1. ExecutionNode
os.remove is allowed here because this is the authorized destructive boundary.
All deletes require HITL and rollback metadata.

2. DuplicateDetectionNode
open(path, "rb") is allowed only for hashing files to detect duplicates.
This is wrapped in _is_path_allowed and never sent to LLM.

3. LLM Calls (classification, sensitivity, summary)
client.generate_content(...) is bypassed because only metadata is passed.
No file contents are ever included.

These are the only safe, justified exceptions.

🧪 Verification
Semgrep scan passes with 0 findings

Pre‑commit hook blocks unsafe code

All 62 tests pass

All metadata‑only transitions validated

No content‑reading code remains in the project

🏁 Summary
Semgrep ensures that CleanSlate AI remains:

Predictable

Nondestructive

Privacy‑preserving

Zero‑content

Safe‑by‑default

Impossible to jailbreak via code changes

This static safety layer is a core part of the CleanSlate AI security architecture.

**3. Sensitive file mishandling**

**We have:**
•	SensitiveDetectionNode metadata only
•	ExecutionNode blocks deletes on sensitive files
•	Semgrep rule: no-sensitive-data-in-logs
•	Redaction logic (coming in audit logging)
•	Sensitive files routed to authenticated folder


**4. Path traversal**

**We have:**
•	FolderScopeNode
•	safe_join
•	Semgrep rule: no-unsafe-path-joins


 **6. Weekly organizer safety**

**WeeklyOrganizerNode:**
•	runs in safe_mode
•	blocks deletes
•	blocks compress
•	uses pre-approved folder scope
•	logs actions



**7. Rollback safety**
•	updated CleanupAction schema
•	added rollback_supported=True
•	Semgrep rule enforces rollback metadata
•	RollbackNode restores safely


`Semgrep` becomes our **static safety gate**, complementing our **runtime ADK safety gates.**