# MASTER TEST FOLDER STRUCTURE FOR CLEANSLATE AI

```
C/
│
├── user/user_name/allowed(desktop/documents/pictures/media etc)
│   ├── Documents/
│   │   ├── Resume.docx
│   │   ├── Notes.txt
│   │   ├── Meeting.pdf
│   │   ├── Duplicate_Resume.docx
│   │   └── Random.docx
│   │
│   ├── Images/
│   │   ├── photo1.png
│   │   ├── photo1_copy.png
│   │   ├── vacation.jpg
│   │   └── meme.png
|   |
│   │── Safe/
│   ├── tax_2023.pdf
│   ├── passport_scan.png
│   ├── ssn_info.txt
│   ├── medical_report.pdf
│   └── bank_statement.pdf
|   |
│   ├── Videos/
│   │   ├── clip1.mp4
│   │   ├── clip1_copy.mp4
│   │   └── birthday.mov
│   │
│   ├── Projects/
│   │   ├── projectA/
│   │   │   ├── code.py
│   │   │   ├── notes.md
│   │   │   └── data.csv
│   │   └── projectB/
│   │       ├── main.js
│   │       └── readme.md
│   │
│   └── Mixed/
│       ├── random.zip
│       ├── duplicate.zip
│       ├── duplicate_copy.zip
│       ├── image.png
│       └── doc.pdf
│
├
│
├── Blocked/
│   ├── System32/
│   │   └── kernel.dll
│   ├── Windows/
│   │   └── registry.dat
│   └── Private/
│       └── do_not_touch.txt
│
└── Authenticated_Secure/
    └── (empty — sensitive files will be moved here)
```


## WHAT THIS TEST FOLDER ENABLES
### ✔ 1. Duplicate Detection
Duplicate_Resume.docx

photo1_copy.png

clip1_copy.mp4

duplicate_copy.zip

### ✔ 2. Sensitive File Protection
Everything in /Sensitive/ triggers:

SensitiveDetectionNode

Authenticated folder move

PIN requirement

Security question

HITL enforcement

### ✔ 3. Blocked Path Enforcement
Everything in /Blocked/ triggers:

PathNotAllowed

Folder scope rejection

Security rule validation

### ✔ 4. Weekly Organizer Safe Mode
Weekly organizer will:

Skip /Sensitive/

Skip /Blocked/

Only move/organize inside /Allowed/

Never delete

### ✔ 5. Folder Scope Selection
User must choose:

Allowed/Documents

Allowed/Images

Allowed/Projects
etc.

### ✔ 6. Authenticated Folder Logic
Sensitive files move into:

Code
Authenticated_Secure/
after PIN + security question.

### ✔ 7. Compression & Archiving
Mixed folder contains:

random.zip

duplicate.zip

duplicate_copy.zip

Perfect for compression tests.

### ✔ 8. Classification Tests
Documents → docx, pdf
Images → png, jpg
Videos → mp4, mov
Projects → code, csv, js
Mixed → zip, png, pdf

## HOW TO USE THIS IN  DEMO
say:

“For testing CleanSlate AI, create the folder structure shown below.
It includes duplicates, sensitive files, blocked paths, mixed content, and project folders.
This allows testing every node, every MCP tool, and every security rule.”

And yes — you can test in  both ports:

http://127.0.0.1:8000/chat → user-friendly UI

http://127.0.0.1:8000/dev-ui/ → developer graph view



