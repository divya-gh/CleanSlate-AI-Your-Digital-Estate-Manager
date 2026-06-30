# Implementing Welcome Message for Antigravity UI 

# 🚀 CleanSlate AI — My PC Assistant
**Your Personal PC Cleanup Assistant, Powered by ADK 2.0**

============================================================================================
## When the user opens CleanSlate AI agent:

🎉 A centered welcome message appears at the top
🎉 The user is told exactly what to say
🎉 When they say “organize my computer” → the guided flow starts
🎉 Allowed vs blocked paths are shown
🎉 User selects folder scope
🎉 Sensitive files are moved to authenticated folder
🎉 User creates a PIN + security question
🎉 User chooses weekly organizer enable/disable

Implementation:
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
