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

