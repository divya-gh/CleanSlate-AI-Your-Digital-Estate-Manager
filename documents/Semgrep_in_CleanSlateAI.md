
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


## How do we implement Semgrep in this project?

Our project already uses:
•	TDD
•	Pre commit hooks
•	Secure agent lifecycle
•	Antigravity remediation loops
•	Semgrep fits directly into this pipeline.


### We can enforce Semgrep at:

**1. Pre commit (local gate)**
Block insecure code before it ever leaves your machine.

**2. Antigravity remediation loop**

When Semgrep fails, Antigravity can:
•	read the failure
•	fix the code
•	re-run tests
•	re-run Semgrep
•	retry the commit

**3. CI/CD (optional)**
We can run Semgrep in GitHub Actions or Kaggle Notebook CI.


## What rules should you add for this project?

Must have rules for our ADK agent:

**1.Hardcoded secrets**

Detect:  AIzaSy[A-Za-z0-9_-]+

**2. Unsafe file operations**
**Block:**

•	os.remove
•	os.rmdir
•	shutil.rmtree
•	open(..., "w") outside allowed paths

**3. Sensitive file mishandling**
Ensure:
•	sensitive files are only moved to Authenticated folder
•	never deleted
•	never compressed
•	never logged with full path

**4. Path traversal**
**Block:**
•	../
•	absolute paths outside allowed_paths
•	unvalidated user input in path joins

**5. Subprocess execution**
**Block:**

•	subprocess.run
•	os.system
•	Popen

 **6. Weekly organizer safety**
**Ensure:**
•	no deletes in safe_mode
•	no compress in safe_mode
•	only moves/archives allowed


**7. Rollback safety**
**Ensure:**
rollback actions always include backup_path	
rollback never overwrites existing files

`Semgrep` becomes our **static safety gate**, complementing our **runtime ADK safety gates.**
