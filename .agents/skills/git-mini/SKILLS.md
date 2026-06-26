---
name: git-mini
description: Safe git workflow with auto-generated meaningful ≤15 character commit messages and sensitive-file protection.
---

# Git Mini Skill

This skill performs a safe git workflow:
1. Checks git status before staging.
2. Blocks sensitive files from being committed.
3. Ensures commit message is meaningful and ≤10 characters.
4. Pulls latest changes from main before pushing.
5. Prevents conflicts and accidental empty commits.

## commit
Runs: status check → sensitive scan → pull → add → commit → push.

```bash
#!/bin/bash
set -e

MSG="$1"

# 1. Validate commit message input and length
if [ -z "$MSG" ]; then
  echo "❌ Error: Antigravity must generate a commit message (≤10 chars)."
  exit 1
fi

if [ ${#MSG} -gt 15 ]; then
  echo "❌ Error: Commit message must be ≤15 characters. Current length: ${#MSG}"
  exit 1
fi

# 2. Check for changes (Exit early if clean)
if git diff --quiet && git diff --cached --quiet; then
  # Check for untracked files too
  if [ -z "$(git status --porcelain)" ]; then
    echo "✨ Nothing to commit, working tree clean."
    exit 0
  fi
fi

# 3. Scan for sensitive files BEFORE doing anything
STATUS=$(git status --porcelain)

SENSITIVE_REGEX="\.env|api|apikey|secret|token|key|credentials|password|pii"

if [ -n "$STATUS" ]; then
  if echo "$STATUS" | grep -E -i "$SENSITIVE_REGEX" > /dev/null; then
    echo "❌ Error: Sensitive file pattern detected in your working tree!"
    echo "$STATUS" | grep -E -i "$SENSITIVE_REGEX"
    echo "🔒 Commit aborted to protect secrets or PII."
    exit 1
  fi
fi

# 4. Pull latest changes safely using rebase
echo "🔄 Pulling latest changes from main..."
git pull origin main --rebase

# 5. Stage and commit
echo "📦 Staging and committing changes..."
git add .
git commit -m "$MSG"

# 6. Push safely
echo "🚀 Pushing changes upstream..."
git push origin main
