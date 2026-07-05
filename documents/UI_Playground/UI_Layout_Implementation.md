## Implementing Antigravity UI Layout in CleanSlate AI — Your Digital Estate Manager

#### Your Personal PC Cleanup Assistant, Powered by ADK 2.0

-----
## UI Features:
### When the user opens CleanSlate AI agent Playground :

#### 🎉 A centered `welcome message` appears at the top
#### 🎉 The user is told exactly what to say - eg: You can say: `"Organize my computer"`
#### 🎉 When they say “organize my computer” → the guided flow starts
#### 🎉 Allowed vs blocked paths are shown
#### 🎉 User selects folder scope - eg: `C:/Users/divya/OneDrive/Desktop`
#### 🎉 User selects folders clean in the selected path
#### 🎉 User creates a PIN + security question
#### 🎉 Sensitive files are moved to authenticated folder with PIN
#### 🎉 User chooses weekly organizer enable/disable - `Ambient`
#### 🎉 Agent asks the user if it can go ahead with the `Clean up Action` 
#### 🎉 Agent generates beautiful `CLEANUP SUMMARY REPORT` and `ACTION LOG`

### Step 1. Implementation of Welcome Message:
- Prompt in Antigravity:
```

Time to pretty the UI to make it easy for the user to navigate . UI_WELCOME_MESSAGE = """
                Hello! I’m CleanSlate AI — My PC Assistant.
I’m here to help you manage, organize, and optimize your computer safely.
I can search your files, declutter folders, detect duplicates, protect sensitive documents, and/or run your weekly organizer.
        You can say: “Organize my computer” to get started.
"""

# When the user says "organize my computer", guide them through:
# 1. Show allowed vs blocked paths
# 2. Ask which folder is OK to organize
# 3. Explain sensitive file handling (moved to authenticated folder)
# 4. Ask user to create a 4-digit PIN + a security question to remember the PIN
# 5. Ask user to enable or disable ambient weekly organizer

ORGANIZE_FLOW_PROMPT = """
Great! Let’s get your computer organized safely.

Here are the paths I can work with:

Allowed Paths:
- <allowed paths>

Blocked Paths:
- <blocked paths>

Please tell me which folder is OK for me to organize.
Sensitive files will be moved to your authenticated secure folder.
Blocked path will never be touched.
Before we begin, please create a 4-digit PIN.
I’ll also ask one security question so you can recover it later.

Would you like to enable Weekly Organizer?
- Enable weekly cleanup
- Keep weekly cleanup disabled
"""
```
Image- UI_layout1 and UI_layout2

========================================================================================
# Adding check boxes to classify folders 

Prompt: 
```

Update the agent logic and dev-ui logic.

When the user enters a folder path (example: C:/Users/divya/Desktop), enter ORGANIZE_MODE.

In ORGANIZE_MODE:
1. List all subfolders inside the provided folder.
2. Render each subfolder as a checkbox with an icon:

   - icon: 📁
   - label: folder name
   - value: absolute path
   - checked = true means "organize this folder"
   - checked = false means "never touch this folder"

Show the UI like this:
"Select which folders to organize and which to leave untouched:"

Example:
📁 [✔] C:/Users/divya/Desktop/Collection
📁 [✔] C:/Users/divya/Desktop/Photos
📁 [✖] C:/Users/divya/Desktop/School
📁 [✔] C:/Users/divya/Desktop/Work
📁 [✖] C:/Users/divya/Desktop/Random

After the user submits checkbox selections:
- Save checked folders as ORGANIZE_LIST
- Save unchecked folders as NEVER_TOUCH_LIST

Then continue the workflow:
1. Explain sensitive file handling:
   "Sensitive files will be moved to your authenticated secure folder."

2. Ask the user to create a 4-digit PIN.
3. Ask the user to choose one security question for PIN recovery.

4. Render a toggle button for Weekly Organizer:
   - "Enable Weekly Organizer"
   - "Disable Weekly Organizer"

5. After the user chooses weekly organizer settings, proceed with cleanup.

Do NOT reset to the welcome message.
Do NOT use fallback responses while in ORGANIZE_MODE.

```

Image - chat_checkbox

============================================================================================
# Implementing Tabular output 

## Update OptimizationPlannerNode:
**Agent OptimizationPlannerNode (or SummaryNode) is currently emitting plain text:**

### Output:
```
== CleanSlate AI PC Assistant Optimization Action Plan ===
Total Estimated Storage Space Recovered: 8663212 bytes
Suggested Actions:
  [1] DELETE: c:\users\divya\onedrive\desktop\collection\Cheet sheets\pics\Data+Visualizations+-+DataCamp.pdf
      Reasoning: Exact duplicate of another file.
      Safe to delete: True | Confidence: 0.95 | Space: 3955024 bytes
  [2] DELETE: c:\users\divya\onedrive\desktop\collection\Cheet sheets\pics\excel_python.jpg
      Reasoning: Exact duplicate of another file.
      Safe to delete: True | Confidence: 0.95 | Space: 153726 bytes
```

## The fix: Emit a TABLE interrupt

### Prompt: 
```
Update the OptimizationPlannerNode and SummaryNode logic.

Instead of printing raw text for optimization actions, emit a TABLE widget using __TABLE__ JSON.

The table should have columns:
- Action (DELETE, ARCHIVE, MOVE)
- Category (duplicate, sensitive, resume, image, etc.)
- File Path
- Space Saved (bytes)
- Confidence (0–1)

Example JSON structure to emit:

{
  "__TABLE__": {
    "columns": ["Action", "Category", "File Path", "Space Saved", "Confidence"],
    "rows": [
      ["DELETE", "duplicate", "c:/users/.../file.pdf", "3955024", "0.95"],
      ["ARCHIVE", " Unused", "c:/users/.../excel_python.jpg", "153726", "0.95"],
      ["MOVE", "sensitive", "c:/users/.../DL.bmp", "0", "0.95"]
    ]
  }
}

Render this table in the UI instead of plain text.

Do NOT print repeated headers.
Do NOT print repeated summaries.
Do NOT print raw text dumps.

After showing the table, ask:
"Would you like me to execute these actions?"
with two buttons:
- Confirm Cleanup
- Cancel

Use __TOGGLE_SELECT__ for these buttons.

Stop execution after emitting the table interrupt.
Resume only after user selects confirm/cancel.

```
=====================================================================================
# Imnplementing Authentication Folder

## Ensure `Authenticated_Secure folder`  is created in the root path.

### Prompt:
```
Update the ExecutionNode and SensitiveFileHandler logic.

Before moving any sensitive file, ensure the Authenticated_Secure folder exists inside the selected  Parent folder(Eg: C:/Users/divya/Desktop/Collection/) .

Implement:

secure_folder = os.path.join(parent_folder, "Authenticated_Secure")
os.makedirs(secure_folder, exist_ok=True)

Then move sensitive files ONLY into secure_folder.

If the destination is NOT secure_folder:
    → block the move
    → log FAILURE
    → do not attempt to move sensitive files into "Organized" or any other folder.

This ensures:
- Sensitive files always have a valid destination
- Sensitive moves succeed
- Safety checks remain intact
- No more repeated FAILURE rows

```

=================================================================================

# FINAL SUMMARYNODE UPGRADE 

## Prompt:
```
Update the SummaryNode logic to produce a colorful, professional, dashboard-style cleanup summary.

Replace the plain text summary with a structured, emoji-enhanced, visually polished report.

The SummaryNode should generate output in the following format:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧹  CLEANSLATE AI — CLEANUP SUMMARY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 OVERVIEW
──────────────────────────────────────────────
• Total Actions:            {total_actions}
• Successful Actions:       {successful_actions}   🟢
• Failed Actions:           {failed_actions}       🔴
• Skipped Actions:          {skipped_actions}      ⚪

💾 STORAGE RECOVERY
──────────────────────────────────────────────
• Total Space Recovered:    {space_recovered} bytes  📦

🔐 SENSITIVE FILE PROTECTION
──────────────────────────────────────────────
• Sensitive Files Protected: {sensitive_count}
• Status:                   🛡️ All protected safely
• Details:                  Hidden for privacy

♻️ ROLLBACK CAPABILITY
──────────────────────────────────────────────
• Rollback Supported:       {rollback_supported}   🔄
• Rollback Unsupported:     {rollback_unsupported} ✔️

🧪 DRY-RUN MODE
──────────────────────────────────────────────
• Dry-Run Active:           {dry_run_status}  🚫

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📜 ACTION LOG DETAILS
(Scroll above for full table)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Implementation Requirements:

1. SummaryNode must read all cleanup results from ctx.session.state:
   - total_actions
   - successful_actions
   - failed_actions
   - skipped_actions
   - space_recovered
   - sensitive_count
   - rollback_supported
   - rollback_unsupported
   - dry_run_status

2. SummaryNode must NOT emit an interrupt.
   It must return a normal MyPCAssistantOutput with the formatted text.

3. SummaryNode must NOT re-run cleanup or re-trigger ExecutionNode.

4. SummaryNode must NOT print raw JSON or raw logs.
   Only the formatted dashboard-style summary should be shown.

5. SummaryNode must NOT reset ORGANIZE_MODE.
   It should simply conclude the workflow.

6. The formatting must remain stable across sandbox, Windows, and Linux environments.


```

Image -summary_dashboard

=====================================================================================

# Implementing Professional, Color‑Coded Action Log (Text‑UI Safe)

**This prompt updates agents SummaryNode so every entry is grouped, color‑coded, and formatted cleanly.**

### Prompt:
```
Update the SummaryNode (or the node responsible for printing Action Log Details)
to render a polished, color‑coded, professional action log.

Replace the raw action-by-action dump with a structured, grouped,
emoji-enhanced dashboard-style log.

The Action Log section must follow this exact format:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📜  CLEANUP ACTION LOG — DETAILED REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 SUCCESSFUL ACTIONS
──────────────────────────────────────────────
For each successful action:
🟢 {ACTION_TYPE} • {FILE_NAME}
If the action has a success message:
    └─ {details}

Group all successful actions together.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 FAILED ACTIONS
──────────────────────────────────────────────
For each failed action:
🔴 {ACTION_TYPE} • {FILE_NAME}
    └─ ❗ {error_message}

Group all failed actions together.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚪ SKIPPED ACTIONS (only if any exist)
──────────────────────────────────────────────
For each skipped action:
⚪ {ACTION_TYPE} • {FILE_NAME}
    └─ {reason}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 NOTES
──────────────────────────────────────────────
• “File not found” failures indicate the file was moved, renamed,
  or deleted before execution.
• “PathNotAllowed” failures indicate archive destination violated
  safety or traversal policy.
• Sensitive files remain protected and hidden by design.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Implementation Requirements:

1. SummaryNode must read the full action log list from ctx.session.state
   (e.g., ctx.session.state["action_log"]).

2. Each action log entry contains:
   - action_type (MOVE, DELETE, ARCHIVE)
   - category (sensitive, image, document, other)
   - file_name
   - status (SUCCESS, FAILURE, SKIPPED)
   - details (error or success message)

3. SummaryNode must group logs by status:
   - SUCCESS
   - FAILURE
   - SKIPPED

4. SummaryNode must NOT emit an interrupt.
   It must return a normal MyPCAssistantOutput with the formatted text.

5. SummaryNode must NOT print raw JSON or raw logs.
   Only the formatted dashboard-style log should be shown.

6. Formatting must remain stable across sandbox, Windows, and Linux.

7. Sensitive file names must be replaced with:
   “[Protected Sensitive File]”
   unless already anonymized.

This change ensures the Action Log Details section is colorful,
professional, readable, and judge-friendly.
```
