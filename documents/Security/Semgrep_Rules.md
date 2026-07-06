# 🛡️ Semgrep Security Rules in CleanSlate AI

CleanSlate AI strictly enforces static code analysis using Semgrep to guarantee that the agent operates safely within the bounds of the host operating system. These rules act as a continuous integration (CI) guardrail against dangerous file operations, privacy leaks, and improper API usage.

Below are the core Semgrep safety rules implemented in our `.semgrep/sdd-safety-rules.yaml` configuration:

---

### 🔑 1. No Hardcoded API Keys (`no-hardcoded-api-keys`)
**Severity**: `ERROR`
- **Rule**: Hardcoded API keys are strictly forbidden anywhere in the source code.
- **Enforcement**: Code must fetch sensitive values dynamically using environment variables (`os.environ.get()`).

### 🗑️ 2. No Direct File Deletes (`no-direct-file-deletes`)
**Severity**: `ERROR`
- **Rule**: Direct calls to `os.remove`, `os.unlink`, or `shutil.rmtree` bypass our safety architecture.
- **Enforcement**: All deletions *must* route through the `ExecutionNode` where Human-in-the-Loop (HITL) approvals and `RollbackNode` metadata are strictly recorded.

### 🛑 3. Never Delete Sensitive Files (`no-delete-sensitive-files`)
**Severity**: `ERROR`
- **Rule**: Any logic branch identifying a file as "sensitive" must never issue a delete command.
- **Enforcement**: Prevents accidental loss of critical user data (e.g., SSNs, Passwords, Tax documents).

### 📁 4. No System Folder Access (`no-system-folder-access`)
**Severity**: `ERROR`
- **Rule**: System-level directories (e.g., `Windows`, `System32`, `Program Files`, `usr/bin`) must never be scanned, modified, or touched.
- **Enforcement**: Ensures the OS remains perfectly intact and the agent operates purely in user-space.

### 🎯 5. Enforce Folder Scope Policy (`file-ops-must-use-folder-scope`)
**Severity**: `WARNING`
- **Rule**: File I/O operations (like `open()`) must first validate the target path against the user's explicit scope.
- **Enforcement**: Requires the `folder_scope_policy.is_path_allowed(path)` check before interacting with the file system.

### ☁️ 6. No File Content Uploads (`no-file-content-upload`)
**Severity**: `ERROR`
- **Rule**: Prevents raw file contents from being transmitted to external APIs (e.g., LLMs).
- **Enforcement**: Flags patterns like `requests.post(..., files=...)`, ensuring our architecture remains metadata-only.

### 🦺 7. Safe Mode Restricts Destructive Actions (`safe-mode-no-deletes-or-compress`)
**Severity**: `ERROR`
- **Rule**: If `safe_mode` is enabled via configuration, all deletes and compress actions are completely blocked at the code level.
- **Enforcement**: Provides an absolute fail-safe fallback for users who want zero destructive operations.

### 🔐 8. Sensitive Files Must Go To Vault (`sensitive-files-to-authenticated`)
**Severity**: `WARNING`
- **Rule**: When a sensitive file is detected, it cannot simply be ignored; it must be protected.
- **Enforcement**: Requires the `move_to_authenticated()` function to relocate the file into the secure, permission-restricted vault.

### ⏪ 9. Destructive Actions Require Rollback Metadata (`destructive-actions-require-rollback`)
**Severity**: `ERROR`
- **Rule**: The agent cannot execute destructive actions without generating a reverse-action payload.
- **Enforcement**: Guarantees that `RollbackNode` always has the cryptographic and path metadata necessary to undo accidental file movements or deletions.
