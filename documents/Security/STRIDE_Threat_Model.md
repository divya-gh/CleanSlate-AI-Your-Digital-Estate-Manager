# CleanSlate AI - 🛡️ STRIDE Threat Model

This document outlines the threat modeling for **CleanSlate AI: Your Digital Estate Manager** using the industry-standard **STRIDE** methodology. Because the agent operates autonomously on a user's personal filesystem, securing the application against these threat vectors is paramount.

---

## 1. 🔑 Spoofing (Authenticity)
**Threat:** A malicious local script or process spoofs the user's identity to authorize destructive actions (e.g., falsely approving an execution prompt in the `HITLApprovalNode`).
**Mitigation:** 
- CleanSlate AI operates entirely locally under the user's authenticated OS profile context. 
- The local server binds strictly to `localhost` (`127.0.0.1`), preventing network-based spoofing attacks.
- ADK 2.0 `resume_inputs` payloads require precise internal state mapping, making it difficult for an unauthenticated script to blindly spoof a continuation event.

---
## 2. 🪓 Tampering (Integrity)
**Threat:** A malicious application or user tampers with `config.json`, `policy.json`, or the ADK state database to bypass path restrictions or alter the agent's behavior.
**Mitigation:**
- **Defense in Depth:** The `FolderScopePolicy` strictly enforces hardcoded programmatic rules that reject system directories (e.g., `/Windows`, `/usr/bin`) *regardless* of what is injected into the JSON configuration files.
- **Safe Execution:** The `move_to_authenticated_folder` tool isolates highly sensitive files into an `Authenticated/` vault, which can be further secured using OS-level folder permissions.

---
## 3. ↩️ Repudiation (Non-repudiability)
**Threat:** A user or system administrator cannot determine why a critical file was deleted, moved, or archived, leading to a loss of accountability.
**Mitigation:**
- **Immutable Audit Trail:** The `write_log` MCP Tool maintains a continuous, local append-only JSONL log of *every* filesystem action taken by the agent.
- Each log entry captures the timestamp, exact file path, action performed (DELETE, MOVE, COMPRESS), and the explicit LLM reasoning/justification that led to the decision.

---
## 4. 📜 Information Disclosure (Confidentiality)
**Threat:** The agent inadvertently reads sensitive file contents (passwords, PII, tax returns, SSH keys) and leaks them to a remote cloud LLM API (e.g., Gemini) during classification.
**Mitigation:**
- **Metadata-Only Architecture:** CleanSlate AI is fundamentally designed to operate purely on metadata. The `read_file_metadata` tool only reads file names, byte sizes, timestamps, and extensions. 
- **Zero Content Reads:** File contents are *never* read into memory or transmitted over the network, entirely eliminating the risk of LLM data exfiltration.

---
## 5. 🚫 Denial of Service (Availability)
**Threat:** The agent is instructed to scan a massive root directory (e.g., `C:\` or `/`), causing memory exhaustion, token limit overflow, or locking up the OS disk I/O.
**Mitigation:**
- **Scope Enforcement:** The `FolderScopeNode` forces users to specify precise, limited directories (e.g., `Desktop`, `Downloads`) before discovery begins.
- **Pagination & Limits:** The `list_files` MCP tool enforces strict upper limits (e.g., 50 files per call) to prevent payload bloat, and recursive tree traversals are tightly controlled to prevent infinite loops.

---
## 6. 💎 Elevation of Privilege (Authorization)
**Threat:** The agent is tricked via Prompt Injection into attempting to delete `C:\Windows\System32`, modify kernel drivers, or alter other users' files.
**Mitigation:**
- **Hardcoded Blacklists:** The `FolderScopePolicy` contains a hardcoded `_SYSTEM_COMPONENTS` blacklist that cannot be overridden by the LLM.
- **OS IAM Enforcement:** The agent inherits the permissions of the user running it. It inherently lacks administrative (`sudo` / `Run as Administrator`) privileges. If the agent attempts to modify a protected system file, the OS kernel will decisively reject the elevation attempt with a `PermissionError`.
